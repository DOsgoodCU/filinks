import csv
import io 
from datetime import datetime
import re
from typing import List, Dict, Any
import requests
import os
import hashlib
import argparse
import sys

# --- Configuration for Caching ---
CACHE_DIR = "cached"
# --- End Configuration ---

# NOTE: This script now expects the following files to be present in the same directory:
# 1. media_data.csv
# 2. news_data.csv
# 3. publications_data.csv
# 4. image_data.csv (NO LONGER USED, but function is kept for script integrity)
# and a directory named 'images'

def safe_filename(title: str, url: str) -> str:
    """Creates a filesystem-safe filename, using a clean version of the title and a URL hash."""
    
    # 1. Clean the title: convert to lowercase, replace non-alphanumeric chars with underscore, and truncate.
    safe_title = re.sub(r'[\W_]+', '_', title.lower()).strip('_')
    if not safe_title:
        safe_title = "document"
        
    safe_title = safe_title[:50] # Truncate for safety

    # 2. Determine extension from URL
    url_path = url.split('?')[0].split('#')[0]
    ext = os.path.splitext(url_path)[1]
    
    # If the extension is missing or too generic, default to .html
    if not ext or len(ext) > 5 or ext.lower() not in ('.html', '.pdf', '.doc', '.docx', '.txt'):
        ext = '.html' 
    
    # 3. Create a unique suffix using a hash of the full URL
    url_hash = hashlib.sha1(url.encode()).hexdigest()[:6]
    
    # Filename structure: safe_title_hash_hash.ext
    return f"{safe_title}_{url_hash}{ext}"


def cache_link(url: str, title: str, should_cache: bool) -> str:
    """
    Downloads content from a URL and caches it locally if caching is enabled.
    Returns the local filepath if successful/cached, otherwise returns the original URL.
    """
    
    if not should_cache:
        # If caching is explicitly disabled via command line argument, return the original URL
        return url

    # Ensure the cache directory exists
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    filename = safe_filename(title, url)
    local_filepath = os.path.join(CACHE_DIR, filename)

    # Check if the file is already cached (This handles the 'don't download if cached' request)
    if os.path.exists(local_filepath):
        print(f"Using cached file for '{title}': {local_filepath}")
        return local_filepath

    print(f"Downloading '{title}' from: {url} to {local_filepath}")
    
    try:
        # Use a timeout and a user-agent to mimic a real browser request
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=15, stream=True)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        # Write content in chunks for robustness, especially with larger files
        with open(local_filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk: # filter out keep-alive new chunks
                    f.write(chunk)

        print(f"Successfully cached: {local_filepath}")
        return local_filepath

    except requests.exceptions.RequestException as e:
        print(f"Error downloading {url}. Falling back to external link: {e}")
        # If caching fails, return the original URL so the link still attempts to work externally.
        return url


def extract_link_info(link_column_value: str) -> tuple[str, str]:
    """
    Extracts the title and URL from the complex <a> tag string in publications data, 
    or treats the entire value as a title and a plain URL if no <a> tag is found.
    """
       
    # Regex to capture the URL (group 1) and the Title (group 2)
    # The regex is permissive of single quotes, double quotes, or no quotes around the URL.
    match = re.search(r'<a href=(?:[\"|\']?)(.*?)(?:[\"|\']?)>(.*?)</a>', link_column_value)
    
    if match:
        # If <a> tag found: Title is link content, URL is href value.
        title = match.group(2).strip()
        url = match.group(1).strip()
        return title, url
    else:
        # If no <a> tag found: Treat the entire value as both the Title and the URL.
        # This handles the case where a plain URL is entered into the publications 'url' column.
        plain_value = link_column_value.strip()
        # Basic check to see if it looks like a URL (starts with http or www)
        if plain_value.lower().startswith('http') or plain_value.lower().startswith('www.'):
            # If it looks like a URL, use it for both title (temporarily) and link
            return plain_value, plain_value
        else:
            # Fallback for truly unstructured data
            return plain_value, '#'


def try_parse_news_date(date_str: str) -> datetime:
    """
    Attempts to parse a date string using multiple common news date formats.
    Returns a fallback date if all attempts fail, ensuring the entry is not skipped.
    """
    # List of formats to try, ordered by likelihood/specificity
    formats_to_try = [
        '%Y-%m-%d', # ISO format (e.g., 2024-05-13)
        '%m/%d/%y', # MM/DD/YY (e.g., 5/13/24)
        '%m/%d/%Y', # MM/DD/YYYY (e.g., 5/13/2024)
        '%b %d, %Y', # Mon Day, Year (e.g., May 13, 2024)
    ]
    
    for fmt in formats_to_try:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
            
    # Fallback date if all attempts fail (very old date ensures it sinks to the bottom)
    return datetime(1900, 1, 1)


def load_image_map(filename: str) -> Dict[str, str]:
    """Reads image_data.csv and returns a map of article_url to image_name. 
    NOTE: This function is now OBSOLETE but kept for script integrity."""
    image_map = {}
    try:
        with open(filename, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # The key is article_url, value is image_name
                # We strip any URL query parameters or anchors for better matching
                url_key = row.get('article_url', '').split('?')[0].split('#')[0].strip()
                image_map[url_key] = row.get('image_name', '').strip()
                
    except FileNotFoundError:
        print(f"Warning: Image data file not found at '{filename}'. News image lookups are now using the 'imagename' column in news_data.csv.")
    except KeyError:
        # This print statement is intentionally suppressed as the map is no longer used
        pass 
    except Exception as e:
        # This print statement is intentionally suppressed as the map is no longer used
        pass
        
    return image_map


def parse_csv_data(filename: str, data_type: str, should_cache: bool, image_map: Dict[str, str] = None) -> List[Dict[str, Any]]:
    """Reads CSV data from a file, parses it into structured entries, and handles caching if enabled."""
    entries = []
    
    try:
        # Open the file for reading with UTF-8 encoding
        with open(filename, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                entry = {'type': data_type}

                if data_type == 'media':
                    # Media Data: title, external_link, date, source
                    try:
                        # --- MODIFICATION: Use robust date parser for media ---
                        raw_date = row.get('date', '').strip()
                        date_obj = try_parse_news_date(raw_date) # Use robust date parser
                        
                        if date_obj == datetime(1900, 1, 1) and raw_date:
                             print(f"Warning: Could not parse media date '{raw_date}'. Using fallback date 1900-01-01.")

                        title = row['title']
                        # --- END MODIFICATION ---

                        link = row['external_link']
                        
                        # Cache the external link (passing the flag)
                        local_link = cache_link(link, title, should_cache)

                        entry.update({
                            'date_obj': date_obj,
                            'date_str': date_obj.strftime('%B %d, %Y'),
                            'title': title,
                            'link': local_link,
                            'source': row['source'],
                        })
                        entries.append(entry)
                    except ValueError:
                        print(f"Skipping media entry in {filename} due to invalid date format: {row.get('date')}")
                    except KeyError as e:
                        print(f"Skipping media entry in {filename}. Missing required column: {e}")

                elif data_type == 'news':
                    # News Data: title, url, author, date, excerpt, imagename
                    try:
                        raw_date = row.get('date', '').strip()
                        
                        # Use the new robust date parser
                        date_obj = try_parse_news_date(raw_date)

                        # Check if it's the fallback date and log a warning
                        if date_obj == datetime(1900, 1, 1) and raw_date:
                             print(f"Warning: Could not parse news date '{raw_date}'. Using fallback date 1900-01-01.")
                        
                        # Use the date string from the object for formatting,
                        # which will correctly format the date regardless of the original input.
                        date_str = date_obj.strftime('%B %d, %Y')
                        
                        title = row['title']
                        
                        # --- MODIFICATION: Use the 'imagename' column from the row ---
                        # The original logic used image_map lookup, we replace it with a direct column read.
                        image_name = row.get('imagename', '').strip()
                        # --- END MODIFICATION ---
                        
                        # Path for the HTML <img> tag
                        image_path = f"images/{image_name}" if image_name else ''
                        
                        # Cache the external link (passing the flag)
                        local_link = cache_link(row['url'], title, should_cache) # Use the full original URL for caching

                        entry.update({
                            'date_obj': date_obj,
                            'date_str': date_str,
                            'title': title,
                            'link': local_link, # Potentially cached link
                            'author': row['author'],
                            'excerpt': row['excerpt'],
                            'image_path': image_path, # The path to the image
                        })
                        entries.append(entry)
                    except KeyError as e:
                        print(f"Skipping news entry in {filename}. Missing required column: {e}")

                elif data_type == 'publications':
                    # Publications Data: url (contains link/title), published_year, published_month, authors, journal, volume, issue, publisher
                    try:
                        # --- FIX: Ensure title is not just the raw URL if a plain URL was provided ---
                        raw_url_value = row.get('url', '')
                        title, link = extract_link_info(raw_url_value)
                        
                        # If extract_link_info returned a raw URL as the title,
                        # try to find a better title if one of the other fields is suitable.
                        if title == link or title == '#':
                            # Prioritize the journal name, then the raw URL, as the title if a title wasn't extracted from an <a> tag
                            # Note: This is an educated guess for a missing title in publication data.
                            better_title = row.get('journal', '') or raw_url_value
                            if better_title:
                                title = better_title.strip()
                            else:
                                title = 'Publication Link' # Final fallback title

                        # Year is required for a meaningful entry; skip if invalid
                        try:
                            # Use 0 as a default for non-existent/invalid year for the check below
                            year = int(row.get('published_year') or 0)
                            if year == 0:
                                # Title is also essential. Skip if year is unusable.
                                raise ValueError("Year is critically missing or invalid.")
                        except (ValueError, TypeError):
                            print(f"Skipping publication entry in {filename}. Year is critically missing or invalid in row: {row}")
                            continue # Skip this entry if year is unusable

                        raw_month = row.get('published_month')
                        
                        # Handle missing, empty, or explicit '0' month by defaulting to 1 (January)
                        # This prevents the "month must be in 1..12" ValueError.
                        if not raw_month or raw_month.strip() == '' or raw_month.strip() == '0':
                            month = 1
                        else:
                            # Safely attempt conversion to integer
                            month = int(raw_month)
                        
                        # Attempt to create date object for sorting (using day 1)
                        # We are now guaranteed a valid month (1-12) and a non-zero year.
                        date_obj = datetime(year, month, 1)

                        # Format date string (e.g., June 2024). We do not show the day.
                        date_str = date_obj.strftime('%B %Y')

                        # Clean up authors (replace <br /> with comma-space)
                        authors = row.get('authors', '').replace('<br />\r\n', ', ').replace('<br />', ', ')
                        
                        # Cache the external link (passing the flag)
                        local_link = cache_link(link, title, should_cache)

                        entry.update({
                            'date_obj': date_obj,
                            'date_str': date_str,
                            'title': title,
                            'link': local_link,
                            'authors': row.get('authors', '').replace('<br />\r\n', ', ').replace('<br />', ', '),
                            'journal': row.get('journal', ''),
                            'publisher': row.get('publisher', ''),
                        })
                        entries.append(entry)
                    except (ValueError, KeyError, TypeError) as e:
                        # Catch other unexpected parsing errors (like invalid month format if it wasn't 0)
                        print(f"Skipping publication entry in {filename} due to critical parsing error: {e} in row: {row}")
                        
    except FileNotFoundError:
        print(f"Warning: CSV file not found at '{filename}'. Skipping this data source.")
    except Exception as e:
        print(f"An unexpected error occurred while processing '{filename}': {e}")
        
    return entries


def generate_html(sorted_entries: List[Dict[str, Any]]) -> str:
    """Generates the HTML content with custom styling and formatting for each entry type."""

    # MODIFICATION: Added .clearfix class to ensure subsequent list items start below the float.
    style = """
        /* Set full browser window background to white */
        body { font-family: 'Helvetica Neue', Arial, sans-serif; margin: 0; padding: 0; background-color: #fff; color: #333; } 
        
        /* Blue header bar across the top of the page */
        .header-bar { background-color: #004c99; padding: 15px 0; margin-bottom: 30px; }
        
        /* White title styling and positioning, centered with content area */
        .header-title { max-width: 960px; margin: 0 auto; padding: 0 20px; font-size: 28px; color: white; font-weight: 500; } 
        
        /* Content container */
        .container { max-width: 960px; margin: 0 auto; padding: 0 20px 20px 20px; background-color: #fff; } 
        
        /* General list styles */
        .entry-list { list-style: none; padding: 0; }
        .entry-list > li { margin-bottom: 25px; border-bottom: 1px dashed #eee; padding-bottom: 15px; }
        .entry-list > li:last-child { border-bottom: none; margin-bottom: 0; padding-bottom: 0; }
        
        /* Entry component styles */
        .entry-title { font-weight: 600; font-size: 16px; margin-right: 5px; display: inline; }
        .entry-title a { color: #1e62a3; text-decoration: none; }
        .entry-title a:hover { text-decoration: underline; color: #004c99; }
        .entry-meta { font-size: 13px; color: #666; margin-top: 3px; display: block; }
        
        /* Ensure abstract text displays fully without truncation or overflow limits */
        .entry-abstract { 
            font-size: 14px; 
            color: #444; 
            margin-top: 5px; 
            padding: 8px 0 0 0; 
            white-space: normal;
            overflow: visible;
            word-wrap: break-word; 
        }

        /* Styling for the image in news/feature entries */
        .entry-image {
            float: left; 
            margin-right: 15px; 
            margin-bottom: 15px; 
            max-width: 150px; 
            height: auto;
            border-radius: 4px;
        }

        /* Wrapper to contain the floated image and the text content */
        .news-content-wrapper {
            /* This property contains the float within this element's boundaries, 
               but the float can still affect elements outside of this wrapper 
               if they are not cleared or in a new block formatting context. */
            display: flow-root; 
        }

        /* NEW: Class to clear the float after the news entry is complete. */
        .clearfix::after {
            content: "";
            display: table;
            clear: both;
        }
        
        /* Specialized styles */
        .date { font-weight: 500; color: #993300; }
        .author-list { font-style: italic; }
        .type-label { color: #004c99; font-size: 11px; font-weight: normal; margin-left: 8px; }
    """

    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Financial Instrument Links</title>
    <style>
        {style}
    </style>
</head>
<body>
    <div class="header-bar">
        <div class="header-title">Financial Instrument Links</div>
    </div>
    <div class="container">
"""
    
    html_content += "<ul class='entry-list'>\n"

    for entry in sorted_entries:
        data_type = entry['type']
        
        # Add a visual label for the type within the mixed list
        type_label = {
            'publications': 'Publication',
            'news': 'News/Feature',
            'media': 'Media Mention',
        }.get(data_type, 'Item')

        # Determine if a clearfix is needed (only for news/feature with an image)
        li_class = ""
        if data_type == 'news' and entry.get('image_path'):
             # Apply clearfix to the list item to ensure the next <li> starts below the float
             li_class = "clearfix"

        # --- Publications Format ---
        if data_type == 'publications':
            # Format: Authors, Year/Month, Title (Linked), Journal, Publisher.
            meta = []
            if entry['journal']:
                meta.append(entry['journal'])
            if entry['publisher'] and entry['publisher'] != 'IRI':
                meta.append(entry['publisher'])
            
            meta_str = ', '.join(meta)

            html_content += f"""
            <li class="{li_class}">
                <div class="entry-meta">
                    <span class="author-list">{entry['authors']}</span>,
                    <span class="date">{entry['date_str']}</span>.
                </div>
                <div class="entry-title">
                    <a href="{entry['link']}" target="_blank">{entry['title']}</a>
                    <span class="type-label">[{type_label}]</span>
                </div>
                {f'<div class="entry-meta">{meta_str}.</div>' if meta_str else ''}
            </li>
"""
        # --- News Format ---
        elif data_type == 'news':
            # Generate image HTML if a path exists
            image_html = f'<img src="{entry["image_path"]}" alt="{entry["title"]}" class="entry-image">' if entry.get('image_path') else ''
            
            # Format: Image (Floated Left), Title (Linked), Date, Author, Excerpt (text/summary).
            html_content += f"""
            <li class="{li_class}">
                {image_html}
                <div class="news-content-wrapper">
                    <div class="entry-title">
                        <a href="{entry['link']}" target="_blank">{entry['title']}</a>
                        <span class="type-label">[{type_label}]</span>
                        <span class="entry-meta">by {entry['author']} on <span class="date">{entry['date_str']}</span></span>
                    </div>
                    <div class="entry-abstract">{entry['excerpt']}</div>
                </div>
            </li>
"""

        # --- Media Format ---
        elif data_type == 'media':
            # Format: Title (Linked), Date, Source.
            html_content += f"""
            <li class="{li_class}">
                <span class="entry-title">
                    <a href="{entry['link']}" target="_blank">{entry['title']}</a>
                    <span class="type-label">[{type_label}]</span>
                </span>
                <span class="entry-meta">
                    (<span class="date">{entry['date_str']}</span>) in {entry['source']}
                </span>
            </li>
"""
        
    html_content += "</ul>\n"

    html_content += """
    </div>
</body>
</html>
"""
    return html_content

def parse_arguments():
    """Parses command-line arguments to check for the caching flag."""
    parser = argparse.ArgumentParser(description="Generate a financial instrument link report with optional caching.")
    parser.add_argument(
        '--cache',
        action='store_true',
        help='Enable caching: external links will be downloaded and stored in the "cached" directory. Links already cached will not be re-downloaded.',
        default=False
    )
    return parser.parse_args()


def main():
    # 0. Parse arguments to determine caching behavior
    args = parse_arguments()
    should_cache = args.cache
    print(f"Caching is {'ENABLED' if should_cache else 'DISABLED'}. Use the '--cache' flag to enable downloading.")

    # 1. Load image mapping data
    # NOTE: This call is kept for compatibility with the original script structure, 
    # but the image map is no longer used for news entries.
    image_map = load_image_map('image_data.csv')
    
    # 2. Read and Parse Data from local CSV files, passing the caching flag and the image map
    # Media entries now use robust date parsing
    media_entries = parse_csv_data('media_data.csv', 'media', should_cache)
    # News entries use robust date parsing and the 'imagename' column
    news_entries = parse_csv_data('news_data.csv', 'news', should_cache, image_map)
    publication_entries = parse_csv_data('publications_data.csv', 'publications', should_cache)

    # 3. Combine all entries
    all_entries = media_entries + news_entries + publication_entries

    # 4. Sort all entries by date (most recent first)
    all_entries.sort(key=lambda x: x['date_obj'], reverse=True)

    # 5. Generate HTML
    html_output = generate_html(all_entries)

    # 6. Write to file
    output_filename = 'financial_instruments.html'
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(html_output)

    print(f"Successfully generated HTML file: {output_filename}")


if __name__ == '__main__':
    # When running the script, the links will be cached in the 'cached' directory if --cache is used.
    # If the download fails, the original external URL will be used in the HTML.
    main()
