# combine_csv.py
import csv
import sys
import re
from typing import Dict, List, Any

# --- Configuration ---

INPUT_FILES = {
    'Media Mention': 'media_data.csv',
    'News/Feature': 'news_data.csv',
    'Publication': 'publications_data.csv'
}
OUTPUT_FILE = 'combined_data.csv'

# The unified header that make_simplefihtml.py expects
FINAL_HEADER = [
    'data_type',
    'title',
    'url',
    'date',
    'author',
    'imagename',
    'excerpt',
    'publisher',
    'published_year',
    'published_month',
    'authors_pub', # Renamed from 'authors'
    'journal',
    'volume',
    'issue',
    'source_media' # Renamed from 'source'
]

# Mapping from source file headers to FINAL_HEADER
COLUMN_MAPS = {
    'Media Mention': {
        'title': 'title',
        'external_link': 'url',      # Renamed
        'date': 'date',
        'source': 'source_media',    # Renamed
    },
    'News/Feature': {
        'title': 'title',
        'url': 'url',
        'author': 'author',
        'date': 'date',
        'imagename': 'imagename',
        'excerpt': 'excerpt',
    },
    'Publication': {
        'url': 'url', 
        'publisher': 'publisher',
        'published_year': 'published_year',
        'published_month': 'published_month',
        'authors': 'authors_pub',    # Renamed
        'journal': 'journal',
        'volume': 'volume',
        'issue': 'issue',
        # 'title' is extracted separately from the 'url' column content
    }
}

def extract_publication_title_from_url(anchor_tag: str) -> str:
    """Extracts the title text from an HTML anchor tag string for publications."""
    # Note: publications_data.csv uses doubled quotes (""") around its fields.
    match = re.search(r'<a\s+[^>]*>([^<]+)</a>', anchor_tag.replace('""', '"'))
    if match:
        return match.group(1).strip()
    return ""

def combine_csv_files(input_files: Dict[str, str], output_file: str, final_header: List[str], column_maps: Dict[str, Dict[str, str]]):
    """Combines and transforms multiple CSV files into a single, unified CSV file."""
    
    all_rows = []
    
    for data_type, filename in input_files.items():
        try:
            # Using 'r' mode because publications_data.csv uses doubled quotes
            with open(filename, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                if not reader.fieldnames:
                    print(f"Warning: File {filename} is empty or has no header. Skipping.")
                    continue
                
                col_map = column_maps[data_type]
                print(f"Processing {filename} as '{data_type}'...")

                for row in reader:
                    # Create a new row initialized with blanks for all final headers
                    new_row = {field: '' for field in final_header}
                    new_row['data_type'] = data_type
                    
                    # Map and populate columns based on the source file
                    for src_col, dest_col in col_map.items():
                        if src_col in row:
                            # Use str(row[src_col] or '') to handle potential None values
                            new_row[dest_col] = str(row[src_col] or '')
                    
                    # Special handling for Publications: Extract the title
                    if data_type == 'Publication':
                        anchor_tag = new_row.get('url', '')
                        extracted_title = extract_publication_title_from_url(anchor_tag)
                        new_row['title'] = extracted_title
                    
                    all_rows.append(new_row)

        except FileNotFoundError:
            print(f"Error: Input file '{filename}' not found. Please ensure all three source files are present.")
            sys.exit(1)
        except Exception as e:
            print(f"An unexpected error occurred while processing {filename}: {e}")
            sys.exit(1)

    # Write the combined data
    try:
        # Using 'csv.QUOTE_MINIMAL' to match standard CSV output for the new file
        with open(output_file, mode='w', newline='', encoding='utf-8') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=final_header)
            
            writer.writeheader()
            writer.writerows(all_rows)
            
        print(f"\n✅ Successfully combined data into '{output_file}'. Total rows: {len(all_rows)}")
        
    except Exception as e:
        print(f"An error occurred while writing the output file: {e}")
        sys.exit(1)

if __name__ == '__main__':
    combine_csv_files(INPUT_FILES, OUTPUT_FILE, FINAL_HEADER, COLUMN_MAPS)
