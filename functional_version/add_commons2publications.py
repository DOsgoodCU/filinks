import json
import csv
import re
from io import StringIO
import os # Import the os module for file path operations

# In this environment, file contents are accessed via the '__files__' dictionary.
# NOTE: The execution block below has been modified to use standard Python file I/O 
# for environments where '__files__' is not available.

def update_publications_data(csv_content, json_content):
    """
    Reads publications data from a JSON file, checks for duplicates against an 
    existing CSV file, and returns the updated CSV content as a string.

    The first column ('url') is specifically formatted as an escaped HTML anchor tag: 
    "<a href="[URL]">[Title]</a>"
    
    Args:
        csv_content (str): The content of the existing publications_data.csv file.
        json_content (str): The content of the academic.json file.
        
    Returns:
        str: The complete, updated CSV content.
    """
    
    # 1. Read existing CSV data and prepare for deduplication
    try:
        # Use StringIO to treat the content string as a file object
        csv_file = StringIO(csv_content)
        # Use csv.reader to correctly parse the existing quoted fields
        # Note: 'excel' dialect handles standard quoting, which is necessary
        csv_reader = csv.reader(csv_file, dialect='excel')
        
        # Read the header row
        header = next(csv_reader)
        
        existing_rows = [row for row in csv_reader]
        
        # The key for deduplication is the entire content of the first column
        existing_url_titles = {row[0] for row in existing_rows}
    except Exception as e:
        print(f"Error reading existing CSV: {e}")
        # If header could not be read, return original content
        return csv_content 

    # 2. Load data from the JSON file
    try:
        data = json.loads(json_content)
        # Assuming 'records' holds the list of publications, adjust if needed
        records = data.get('records', []) 
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON file: {e}")
        return csv_content 
        
    new_rows = []
    
    # Define the author separator as seen in the existing CSV file
    AUTHOR_SEPARATOR = "<br />\r\n"
    
    # 3. Process JSON records
    for record in records:
        try:
            # Map JSON fields to required CSV data points
            title = record.get('title', 'Untitled')
            url = record.get('persistent_url')
            # Ensure authors is a list, even if the key is missing or None
            authors = record.get('author', []) or [] 
            date_str = record.get('date', '')
            
            # Skip records missing essential link data
            if not url:
                continue
                
            # Extract 4-digit year from the date string
            year_match = re.search(r'(\d{4})', date_str)
            published_year = year_match.group(1) if year_match else ''

            # MODIFIED LINE: Construct the formatted URL/Title string for the first column.
            # Use single quotes around the URL, relying on CSV writer to quote the whole field.
            url_title_field = f'<a href="{url}">{title}</a>'
            
            # Check for duplication against existing records
            if url_title_field in existing_url_titles:
                continue
            
            # Format authors: join array elements with the custom separator
            formatted_authors = AUTHOR_SEPARATOR.join(authors)
            
            # Construct the full new row (8 columns: url,publisher,published_year,published_month,authors,journal,volume,issue)
            # Columns 1, 3, 5, 6, 7 are left empty to match the original structure.
            new_row = [
                url_title_field, # Col 0: Formatted URL/Title (will be quoted)
                '',              # Col 1: publisher (empty)
                published_year,  # Col 2: published_year
                '',              # Col 3: published_month (empty)
                formatted_authors,# Col 4: authors
                '',              # Col 5: journal (empty)
                '',              # Col 6: volume (empty)
                ''               # Col 7: issue (empty)
            ]
            
            new_rows.append(new_row)
            
        except Exception as e:
            # Print specific error and continue processing other records
            print(f"Skipping record due to processing error: {e}. Record ID: {record.get('id')}")
            continue

    # 4. Combine all rows
    updated_rows = existing_rows + new_rows
    
    # 5. Write all data back to a new CSV content string
    output = StringIO()
    # Use QUOTE_MINIMAL: this quotes only the fields that contain special characters (like the comma in the URL/Title field),
    # and leaves fields without special characters unquoted, matching the requested structure.
    csv_writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL, lineterminator='\r\n')
    
    csv_writer.writerow(header)
    csv_writer.writerows(updated_rows)
    
    print(f"Successfully processed {len(new_rows)} new unique publication records.")
    
    # Return the string content of the updated CSV
    return output.getvalue()


# --- Main Execution Block for local environments ---
if __name__ == "__main__":
    CSV_FILENAME = 'publications_data.csv'
    JSON_FILENAME = 'academic.json'
    
    # Check if we are in the special Canvas environment
    if 'get_file_content' in globals():
        try:
            # This path is for the execution environment where files are provided as global variables/functions
            csv_content = globals()['get_file_content'](CSV_FILENAME)
            json_content = globals()['get_file_content'](JSON_FILENAME)
            
            updated_content = update_publications_data(csv_content, json_content)
            
            print("\n--- BEGIN UPDATED CSV CONTENT ---")
            print(updated_content)
            print("--- END UPDATED CSV CONTENT ---")

        except Exception as e:
            # Fallback for the original environment if file access method changes
            print(f"Error accessing files in the dedicated environment: {e}")
            
    else:
        # This path is for running the script directly on your local machine
        try:
            print(f"Attempting to read files: {CSV_FILENAME} and {JSON_FILENAME} from local directory...")
            
            with open(CSV_FILENAME, 'r', encoding='utf-8') as f:
                csv_content = f.read()
            
            with open(JSON_FILENAME, 'r', encoding='utf-8') as f:
                json_content = f.read()
                
            updated_content = update_publications_data(csv_content, json_content)

            # Write the updated content back to the CSV file
            with open(CSV_FILENAME, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            print(f"\nSUCCESS: File '{CSV_FILENAME}' has been updated with new records.")
            print(f"Total new unique records added: {len(updated_content.splitlines()) - len(csv_content.splitlines())}") # Rough count
            
        except FileNotFoundError:
            print(f"\nERROR: Could not find required files.")
            print(f"Please ensure both '{CSV_FILENAME}' and '{JSON_FILENAME}' are in the same directory as the script.")
        except Exception as e:
            print(f"\nAn unexpected error occurred during local file processing: {e}")

