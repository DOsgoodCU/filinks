import requests
import csv
import re
from io import StringIO
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Tuple

# --- Configuration ---
TARGET_URL = 'https://academiccommons.columbia.edu/search?page=2&q=Daniel+Osgood&search_field=all_fields'
CSV_FILENAME = 'publications_data.csv'
# Headers required by the existing CSV file. New data will be mapped to this structure.
CSV_HEADERS = ['url', 'publisher', 'published_year', 'published_month', 'authors', 'journal', 'volume', 'issue']


def get_clean_text(element) -> str:
    """Safely get the text content of a BeautifulSoup element, stripping whitespace."""
    return element.get_text(strip=True) if element else ''


def make_anchor_tag(href: str, title: str) -> str:
    """Formats the URL and Title into the CSV's required HTML anchor tag format."""
    # Note: Uses double-quotes inside the string for CSV compatibility
    return f'"<a href=\\""{href}\\"">{title}</a>"'


def normalize_title(title: str) -> str:
    """Normalizes a publication title for case-insensitive and whitespace-robust comparison."""
    # Removes non-alphanumeric characters, converts to lowercase, and strips space
    return re.sub(r'[\W_]+', '', title).lower().strip()


def scrape_publications(url: str) -> List[Dict[str, str]]:
    """
    Scrapes the target URL for publication data.
    NOTE: You will likely need to adjust the CSS selectors below based on the
    actual structure of the academiccommons.columbia.edu webpage.
    """
    print(f"--- Scraping: {url} ---")
    publications = []

    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {url}: {e}")
        return publications

    soup = BeautifulSoup(response.content, 'html.parser')

    # ASSUMPTION: Each result is in a container with the class 'result-document'
    # YOU MAY NEED TO CHANGE '.result-document'
    results = soup.find_all('div', class_='result-document')

    if not results:
        print("Warning: No results found. Check the CSS selector for the result container.")
        # Attempt a broader search if the specific class fails
        results = soup.find_all('div', class_=re.compile(r'search-result|document-entry'))
        if results:
            print(f"Found {len(results)} results with a broader selector.")

    for result in results:
        # 1. Title and URL
        # ASSUMPTION: Title is an <a> tag with class 'title-link' or similar
        # YOU MAY NEED TO CHANGE '.title-link'
        title_tag = result.find('a', class_='title-link')
        if not title_tag:
            # Fallback for title/link
            title_tag = result.find('h3', class_='record-title').find('a') if result.find('h3', class_='record-title') else None

        if not title_tag or not title_tag.get('href'):
            # Skip entries without a proper title/link
            continue

        raw_title = get_clean_text(title_tag)
        raw_url = title_tag.get('href')

        # 2. Authors (usually a list of <a> tags or a single line of text)
        # ASSUMPTION: Authors are contained in a div/p/span with class 'author-list'
        # YOU MAY NEED TO CHANGE '.author-list'
        author_element = result.find('div', class_='author-list')
        authors_text = get_clean_text(author_element).replace('; ', '<br />') if author_element else ''

        # 3. Date (Year is most important)
        # ASSUMPTION: Date is in a span/div with class 'date-line'
        # YOU MAY NEED TO CHANGE '.date-line'
        date_element = result.find('span', class_='date-line')
        date_text = get_clean_text(date_element)
        year_match = re.search(r'(\d{4})', date_text)
        year = year_match.group(1) if year_match else ''
        month = '' # Cannot reliably scrape month without more detailed structure

        # 4. Journal/Publisher/Volume/Issue (This is highly variable, use placeholders)
        # ASSUMPTION: Other metadata is in a block with class 'metadata-block'
        # YOU MAY NEED TO CHANGE '.metadata-block'
        metadata_block = result.find('div', class_='metadata-block')
        journal = ''
        publisher = ''

        # Construct the final publication dictionary
        pub = {
            'url': make_anchor_tag(raw_url, raw_title),
            'publisher': publisher,
            'published_year': year,
            'published_month': month,
            'authors': authors_text,
            'journal': journal,
            'volume': '',
            'issue': '',
            'raw_url': raw_url, # Stored for easy comparison
            'raw_title': raw_title, # Stored for easy comparison
            'normalized_title': normalize_title(raw_title) # Stored for matching
        }
        publications.append(pub)

    print(f"--- Scraped {len(publications)} entries. ---")
    return publications


def load_existing_data(filename: str) -> Tuple[List[Dict[str, str]], List[str]]:
    """Loads existing data from the CSV file."""
    existing_data = []
    # Use io.StringIO to handle the embedded quotes/HTML within the CSV cells
    # The default dialect is usually sufficient for standard CSVs
    try:
        with open(filename, 'r', newline='', encoding='utf-8') as f:
            # Handle the CSV header row
            reader = csv.DictReader(f)
            headers = reader.fieldnames if reader.fieldnames else CSV_HEADERS

            for row in reader:
                # Extract clean title/URL for comparison purposes
                url_cell = row.get('url', '')
                url_match = re.search(r'href=\\""(.*?)\\""', url_cell)
                title_match = re.search(r'>([^<]*)<', url_cell)

                row['raw_url'] = url_match.group(1) if url_match else ''
                row['raw_title'] = title_match.group(1) if title_match else ''
                row['normalized_title'] = normalize_title(row['raw_title'])
                existing_data.append(row)

    except FileNotFoundError:
        print(f"Warning: {filename} not found. Starting with an empty dataset.")
        headers = CSV_HEADERS
    except Exception as e:
        print(f"Error loading {filename}: {e}. Starting with an empty dataset.")
        headers = CSV_HEADERS

    return existing_data, headers


def save_data(filename: str, headers: List[str], data: List[Dict[str, str]]):
    """Saves the combined data back to the CSV file."""
    # Filter out temporary keys like 'raw_url', 'raw_title', 'normalized_title'
    output_data = [
        {k: v for k, v in row.items() if k in headers}
        for row in data
    ]

    try:
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers, quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()
            writer.writerows(output_data)
        print(f"\n--- Success! Data saved to {filename} ({len(output_data)} entries). ---")
    except Exception as e:
        print(f"Error saving data to {filename}: {e}")


def find_matching_entry(new_pub: Dict[str, str], existing_data: List[Dict[str, str]]) -> Optional[Dict[str, str]]:
    """Finds an existing entry that matches the new publication by title."""
    for existing_pub in existing_data:
        # Check for title match
        if new_pub['normalized_title'] == existing_pub['normalized_title']:
            return existing_pub
    return None


def process_data(scraped_data: List[Dict[str, str]], existing_data: List[Dict[str, str]], headers: List[str]):
    """Core logic for merging and conflict resolution."""
    print("\n--- Processing New Data ---")
    new_entries_added = 0
    total_entries = existing_data[:]

    # Create a set of existing raw URLs for quick exact match check (Point 1)
    existing_raw_urls = {pub['raw_url'] for pub in existing_data}

    for new_pub in scraped_data:
        new_url = new_pub['raw_url']
        new_title = new_pub['raw_title']

        # 1. Direct URL Match Check (Point 1: skip if direct link)
        if new_url in existing_raw_urls:
            print(f"Skipping direct duplicate (URL match): '{new_title}'")
            continue

        # 2. Title Match Check (Point 2: potential conflict/different source)
        matching_existing_pub = find_matching_entry(new_pub, existing_data)

        if matching_existing_pub:
            # Conflict detected: Same title, different URL
            existing_url = matching_existing_pub['raw_url']
            existing_title = matching_existing_pub['raw_title']

            print("\n=======================================================")
            print("!!! CONFLICT DETECTED - Same Title, Different Source !!!")
            print(f"Title: {new_title}")

            # Present options
            print("\nOption 1 (Existing in CSV):")
            print(f"  URL: {existing_url}")
            print(f"  Year: {matching_existing_pub['published_year']}")
            print(f"  Authors: {matching_existing_pub['authors'][:50]}...")

            print("\nOption 2 (New from Scrape):")
            print(f"  URL: {new_url}")
            print(f"  Year: {new_pub['published_year']}")
            print(f"  Authors: {new_pub['authors'][:50]}...")

            # Get user input
            while True:
                choice = input(
                    "\nEnter your choice (1=Keep Existing, 2=Keep New, B=Keep Both, S=Skip/Ignore): "
                ).upper()

                if choice == '1':
                    print("-> Keeping Existing entry (Option 1). Skipping new entry.")
                    break
                elif choice == '2':
                    print("-> Keeping New entry (Option 2). Replacing existing entry.")
                    # Find and remove the old entry, then add the new one
                    total_entries = [p for p in total_entries if p['raw_url'] != existing_url]
                    total_entries.append(new_pub)
                    new_entries_added += 1
                    break
                elif choice == 'B':
                    print("-> Keeping Both entries.")
                    total_entries.append(new_pub)
                    new_entries_added += 1
                    break
                elif choice == 'S':
                    print("-> Skipping/Ignoring the conflict.")
                    break
                else:
                    print("Invalid input. Please enter 1, 2, B, or S.")
        else:
            # 3. No Match Found -> Add New Entry
            total_entries.append(new_pub)
            existing_raw_urls.add(new_url) # Update the set to prevent immediate dupe
            new_entries_added += 1
            # print(f"Adding new entry: {new_title}")


    print("\n--- Processing Complete ---")
    print(f"Total entries in final dataset: {len(total_entries)}")
    print(f"New unique entries added: {new_entries_added}")
    return total_entries


if __name__ == "__main__":
    # 1. Load existing data
    existing_publications, headers = load_existing_data(CSV_FILENAME)
    print(f"Loaded {len(existing_publications)} existing publications from {CSV_FILENAME}.")

    # 2. Scrape new data
    scraped_publications = scrape_publications(TARGET_URL)

    if scraped_publications:
        # 3. Process and merge data with conflict resolution
        final_data = process_data(scraped_publications, existing_publications, headers)

        # 4. Save the final data
        save_data(CSV_FILENAME, headers, final_data)
    else:
        print("No new data was scraped. File remains unchanged.")

