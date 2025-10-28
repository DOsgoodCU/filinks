import csv
import re
from typing import List, Dict, Any
import sys
import os

# NOTE: This script is designed to identify duplicate entries across all data sources
# based on the normalized 'title' field.

def load_image_map(filename: str) -> Dict[str, str]:
    """
    Reads image_data.csv and returns a map of article_url to image_name.
    (This function is included for compatibility with parse_csv_data, even though
    the image data itself is not used for duplicate detection.)
    """
    image_map = {}
    try:
        with open(filename, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Key is article_url, value is image_name
                url_key = row.get('article_url', '').split('?')[0].split('#')[0].strip()
                image_map[url_key] = row.get('image_name', '').strip()
    except FileNotFoundError:
        # Suppress file not found warning for image_data.csv since it's optional for this task
        pass
    except Exception as e:
        print(f"Warning: Error reading image data: {e}", file=sys.stderr)
        
    return image_map


def extract_link_info(link_column_value: str) -> tuple[str, str]:
    """Extracts the title and URL from the complex <a> tag string in publications data."""
    # Regex to capture the URL (group 1) and the Title (group 2)
    match = re.search(r'<a href=[\"|\'](.*?)[\"|\']>(.*?)</a>', link_column_value)
    if match:
        # Returns (Title, URL)
        return match.group(2).strip(), match.group(1).strip()
    return link_column_value.strip(), '#'


def normalize_title(title: str) -> str:
    """
    Normalizes a title string for robust duplicate checking.
    - Converts to lowercase.
    - Removes punctuation and extra whitespace.
    """
    # Convert to lowercase
    normalized = title.lower()
    # Remove all non-alphanumeric characters (except space)
    normalized = re.sub(r'[^\w\s]', '', normalized)
    # Replace multiple spaces with a single space and strip leading/trailing spaces
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized


def parse_csv_data(filename: str, data_type: str, image_map: Dict[str, str] = None) -> List[Dict[str, Any]]:
    """
    Reads CSV data and extracts the necessary entry information.
    Caching is disabled and date parsing is simplified as we only need the title/raw data.
    """
    entries = []
    
    try:
        with open(filename, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                entry = {'type': data_type, 'source_file': filename}

                if data_type == 'media':
                    try:
                        title = row['title']
                        entry.update({
                            'title': title,
                            'raw_data': row # Keep original data for reporting
                        })
                        entries.append(entry)
                    except KeyError as e:
                        print(f"Skipping media entry in {filename}. Missing required column: {e}", file=sys.stderr)

                elif data_type == 'news':
                    try:
                        title = row['title']
                        entry.update({
                            'title': title,
                            'raw_data': row # Keep original data for reporting
                        })
                        entries.append(entry)
                    except KeyError as e:
                        print(f"Skipping news entry in {filename}. Missing required column: {e}", file=sys.stderr)

                elif data_type == 'publications':
                    try:
                        title, _ = extract_link_info(row.get('url', ''))
                        
                        # Publications must have a title to be meaningful
                        if not title:
                            raise ValueError("Title not found in 'url' column.")

                        entry.update({
                            'title': title,
                            'raw_data': row # Keep original data for reporting
                        })
                        entries.append(entry)
                    except (ValueError, KeyError) as e:
                        print(f"Skipping publication entry in {filename} due to critical parsing error: {e}", file=sys.stderr)
                        
    except FileNotFoundError:
        print(f"Warning: CSV file not found at '{filename}'. Skipping this data source.", file=sys.stderr)
    except Exception as e:
        print(f"An unexpected error occurred while processing '{filename}': {e}", file=sys.stderr)
        
    return entries


def find_duplicates(all_entries: List[Dict[str, Any]]):
    """
    Identifies entries with duplicate normalized titles and prints them to stdout.
    """
    
    # Map of normalized title to a list of original entries that share that title
    title_map: Dict[str, List[Dict[str, Any]]] = {}
    
    for entry in all_entries:
        original_title = entry.get('title', '')
        # Only check entries that successfully had a title extracted
        if original_title:
            normalized = normalize_title(original_title)
            
            if normalized not in title_map:
                title_map[normalized] = []
            
            title_map[normalized].append(entry)

    found_duplicates = False
    
    # Iterate through the map to find lists with more than one entry
    for normalized_title, entries in title_map.items():
        if len(entries) > 1:
            found_duplicates = True
            
            print("=" * 70)
            print(f"DUPLICATE FOUND (Normalized Title: '{normalized_title}')")
            print(f"Shared Original Title: '{entries[0]['title']}'")
            print("=" * 70)
            
            for i, entry in enumerate(entries):
                print(f"\n--- Entry {i + 1} ({entry['type'].upper()} from {entry['source_file']}) ---")
                
                # Print all raw data fields for easy comparison
                for key, value in entry['raw_data'].items():
                    # Format as key: value, handling long values gracefully
                    formatted_value = value if len(str(value)) < 120 else f"{str(value)[:120]}..."
                    print(f"  {key.ljust(20)}: {formatted_value}")
                
            print("\n" + "-" * 70 + "\n")


def main():
    # 1. Load image map (even though it's not used, it keeps parse_csv_data signature intact)
    image_map = load_image_map('image_data.csv')
    
    # 2. Read and Parse Data from local CSV files
    # Caching is implicitly disabled as the 'should_cache' argument is not passed/used here.
    media_entries = parse_csv_data('media_data.csv', 'media')
    news_entries = parse_csv_data('news_data.csv', 'news', image_map)
    publication_entries = parse_csv_data('publications_data.csv', 'publications')

    # 3. Combine all entries
    all_entries = media_entries + news_entries + publication_entries

    # 4. Find and report duplicates
    if all_entries:
        find_duplicates(all_entries)
    else:
        print("No entries were loaded from any CSV file. Check file names and structure.")


if __name__ == '__main__':
    main()

