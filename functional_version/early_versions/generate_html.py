import csv
import io 
from datetime import datetime
import re
from typing import List, Dict, Any

# NOTE: The MOCK DATA SECTION has been removed.
# This script now expects the following files to be present in the same directory:
# 1. media_data.csv
# 2. news_data.csv
# 3. publications_data.csv


def extract_link_info(link_column_value: str) -> tuple[str, str]:
    """Extracts the title and URL from the complex <a> tag string in publications data."""
    # Regex to capture the URL (group 1) and the Title (group 2)
    # The regex needs to handle both single and double-quoted internal links present in the CSV snippets
    match = re.search(r'<a href=[\"|\'](.*?)[\"|\']>(.*?)</a>', link_column_value)
    if match:
        # Returns (Title, URL)
        return match.group(2).strip(), match.group(1).strip()
    return link_column_value.strip(), '#'


def parse_csv_data(filename: str, data_type: str) -> List[Dict[str, Any]]:
    """Reads CSV data from a file and parses it into structured entries."""
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
                        date_obj = datetime.strptime(row['date'], '%Y-%m-%d')
                        entry.update({
                            'date_obj': date_obj,
                            'date_str': date_obj.strftime('%B %d, %Y'),
                            'title': row['title'],
                            'link': row['external_link'],
                            'source': row['source'],
                        })
                        entries.append(entry)
                    except ValueError:
                        print(f"Skipping media entry in {filename} due to invalid date format: {row.get('date')}")
                    except KeyError as e:
                        print(f"Skipping media entry in {filename}. Missing required column: {e}")

                elif data_type == 'news':
                    # News Data: title, url, author, date, excerpt
                    try:
                        date_obj = datetime.strptime(row['date'], '%Y-%m-%d')
                        entry.update({
                            'date_obj': date_obj,
                            'date_str': date_obj.strftime('%B %d, %Y'),
                            'title': row['title'],
                            'link': row['url'],
                            'author': row['author'],
                            'excerpt': row['excerpt'],
                        })
                        entries.append(entry)
                    except ValueError:
                        print(f"Skipping news entry in {filename} due to invalid date format: {row.get('date')}")
                    except KeyError as e:
                        print(f"Skipping news entry in {filename}. Missing required column: {e}")

                elif data_type == 'publications':
                    # Publications Data: url (contains link/title), published_year, published_month, authors, journal, volume, issue, publisher
                    try:
                        title, link = extract_link_info(row['url'])
                        
                        # Construct date from year and month
                        year = int(row.get('published_year'))
                        # Default to 1 (January) if month is missing or empty
                        month = int(row.get('published_month') or 1) 
                        
                        # Attempt to create date object for sorting (using day 1)
                        date_obj = datetime(year, month, 1)

                        # Format date string (e.g., June 2024)
                        date_str = date_obj.strftime('%B %Y')

                        # Clean up authors (replace <br /> with comma-space)
                        authors = row.get('authors', '').replace('<br />\r\n', ', ').replace('<br />', ', ')

                        entry.update({
                            'date_obj': date_obj,
                            'date_str': date_str,
                            'title': title,
                            'link': link,
                            'authors': authors,
                            'journal': row.get('journal', ''),
                            'publisher': row.get('publisher', ''),
                        })
                        entries.append(entry)
                    except (ValueError, KeyError) as e:
                        print(f"Skipping publication entry in {filename} due to error during parsing: {e} in row {row}")
                        
    except FileNotFoundError:
        print(f"Warning: CSV file not found at '{filename}'. Skipping this data source.")
    except Exception as e:
        print(f"An unexpected error occurred while processing '{filename}': {e}")
        
    return entries


def generate_html(sorted_entries: List[Dict[str, Any]]) -> str:
    """Generates the HTML content with custom styling and formatting for each entry type."""

    # Base style updated for blue header, white title, and white background
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
            font-size: 13px; 
            color: #444; 
            margin-top: 5px; 
            background-color: #f9f9f9; 
            padding: 8px; 
            border-left: 3px solid #ccc;
            white-space: normal; /* Ensures text wraps naturally */
            overflow: visible;  /* Ensures content is never hidden */
            word-wrap: break-word; /* Allows long words to break to prevent horizontal scroll */
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
    
    # Removed the line showing the total entry count per user request.
    
    html_content += "<ul class='entry-list'>\n"

    for entry in sorted_entries:
        data_type = entry['type']
        
        # Add a visual label for the type within the mixed list
        type_label = {
            'publications': 'Publication',
            'news': 'News/Feature',
            'media': 'Media Mention',
        }.get(data_type, 'Item')

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
            <li>
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
            # Format: Title (Linked), Date, Author, Excerpt (text/summary).
            html_content += f"""
            <li>
                <div class="entry-title">
                    <a href="{entry['link']}" target="_blank">{entry['title']}</a>
                    <span class="type-label">[{type_label}]</span>
                    <span class="entry-meta">by {entry['author']} on <span class="date">{entry['date_str']}</span></span>
                </div>
                <div class="entry-abstract">{entry['excerpt']}</div>
            </li>
"""

        # --- Media Format ---
        elif data_type == 'media':
            # Format: Title (Linked), Date, Source.
            html_content += f"""
            <li>
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


def main():
    # 1. Read and Parse Data from local CSV files
    media_entries = parse_csv_data('media_data.csv', 'media')
    news_entries = parse_csv_data('news_data.csv', 'news')
    publication_entries = parse_csv_data('publications_data.csv', 'publications')

    # 2. Combine all entries
    all_entries = media_entries + news_entries + publication_entries

    # 3. Sort all entries by date (most recent first)
    # The sort key uses 'date_obj', which is a datetime object created during parsing.
    all_entries.sort(key=lambda x: x['date_obj'], reverse=True)

    # 4. Generate HTML
    html_output = generate_html(all_entries)

    # 5. Write to file
    output_filename = 'financial_instruments.html'
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(html_output)

    print(f"Successfully generated HTML file: {output_filename}")


if __name__ == '__main__':
    main()

