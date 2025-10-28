import requests
from bs4 import BeautifulSoup
import os
import csv
from urllib.parse import urljoin
import re

# --- Configuration ---
BASE_URL = "https://iri.columbia.edu/topics/financial-instruments/"
OUTPUT_DIR = "images"
CSV_FILE = "image_data.csv"
# --- End Configuration ---

def clean_filename(text):
    """Cleans text to be safe for filenames, replacing special characters with underscores."""
    # Replace non-alphanumeric/dot/hyphen/underscore with underscore
    text = re.sub(r'[^\w\-_\.]', '_', text).strip('_')
    # Limit length
    return text[:50] 

def create_output_dir(directory):
    """Creates the output directory if it doesn't exist."""
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Created directory: {directory}")

def download_image(img_url, file_path):
    """Downloads an image from a URL and saves it to a file path."""
    try:
        # Check if the URL is valid
        if not img_url.startswith('http'):
             print(f"  Skipping invalid image URL: {img_url}")
             return False

        response = requests.get(img_url, stream=True, timeout=10)
        response.raise_for_status() # Check for HTTP errors

        with open(file_path, 'wb') as file:
            for chunk in response.iter_content(1024):
                file.write(chunk)
        return True
    except requests.exceptions.RequestException as e:
        print(f"  Error downloading image from {img_url}: {e}")
        return False

def scrape_and_process():
    """Main function to scrape, report, download, and generate CSV."""
    create_output_dir(OUTPUT_DIR)
    image_data = []
    download_count = 0

    try:
        # 1. Fetch the webpage content
        print(f"Fetching content from: {BASE_URL}")
        response = requests.get(BASE_URL, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # 2. WordPress-Optimized Search: Find common article/post containers.
        # This targets a comprehensive list of common WordPress article/post wrappers.
        article_selectors = 'article.topic, article[class*="post-"], div.post-item, div.article-item'
        articles = soup.select(article_selectors)

        if not articles:
            print("Warning: Could not find any standard article/post blocks using common WordPress selectors.")
        
        for i, article in enumerate(articles):
            img_tag = None
            link_tag = None
            
            # 2a. Find the Image: Look for the <img> inside common WordPress thumbnail wrappers.
            # Using 'select_one' for more specific CSS targeting.
            img_container_selectors = '.entry-thumbnail img, .post-thumb img, .featured-image img, figure.wp-block-image img'
            img_tag = article.select_one(img_container_selectors)
            
            # Fallback: Find any image directly within the article, excluding tiny icons (e.g., logo)
            if not img_tag:
                 img_tag = article.find('img', src=re.compile(r'\.(jpe?g|png|gif)', re.I), width=lambda x: x is None or int(x) > 50)


            # 2b. Find the Link/Title: Look for the main article title link.
            # Titles are typically h2 with a class like .entry-title or .post-title.
            title_link_selectors = 'h2.entry-title a, h3.post-title a, a[rel="bookmark"]'
            link_tag = article.select_one(title_link_selectors)

            if img_tag and link_tag:
                # Extract image and link data
                img_src = img_tag.get('src')
                # Use 'data-src' if 'src' is missing (common with lazy loading)
                if not img_src:
                    img_src = img_tag.get('data-src') 
                
                if not img_src:
                     print(f"Content Block {i + 1}: Found tags but no valid 'src' or 'data-src' on image.")
                     continue
                     
                full_img_url = urljoin(BASE_URL, img_src)
                
                link_title = link_tag.get_text(strip=True)
                link_url = urljoin(BASE_URL, link_tag.get('href'))
                
                # Report finding to standard output
                print("-" * 50)
                print(f"Found Content Block {i + 1}:")
                print(f"  Image URL: {full_img_url}")
                print(f"  Link Text/Title: {link_title}")
                print(f"  Link URL: {link_url}")
                
                # Create a clean file name
                file_base_name = clean_filename(link_title)
                # Try to extract the extension from the image URL
                img_ext = os.path.splitext(full_img_url.split('?')[0])[-1] or '.jpg'
                
                img_filename = f"{file_base_name}{img_ext}" if file_base_name else f"image_{i}{img_ext}"
                
                local_file_path = os.path.join(OUTPUT_DIR, img_filename)

                # 3. Download the image
                print(f"  Attempting download to: {local_file_path}")
                if download_image(full_img_url, local_file_path):
                    download_count += 1
                    print("  Download successful.")
                    # 4. Store data for CSV
                    image_data.append({
                        'image_name': img_filename,
                        'article_title': link_title,
                        'article_url': link_url
                    })
                else:
                    print("  Download failed.")
            
            elif article:
                # Only report on blocks that look like articles but failed to yield a pair
                # We skip reporting on the general outer wrappers (if they were included in the search)
                if len(article.attrs.get('class', [])) > 1:
                    print("-" * 50)
                    print(f"Content Block {i + 1}: Found article element but could not find a valid image and/or link pair.")


        # 5. Generate CSV file
        print("-" * 50)
        print(f"Generating CSV file: {CSV_FILE}")
        
        if image_data:
            with open(CSV_FILE, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['image_name', 'article_title', 'article_url']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                writer.writerows(image_data)
            
            print("Script completed successfully.")
            print(f"Total images downloaded: {download_count}")
            print(f"Images are in the '{OUTPUT_DIR}' directory.")
            print(f"Data is in the '{CSV_FILE}' file.")
        else:
             print("No image data was collected to generate the CSV.")


    except requests.exceptions.RequestException as e:
        print("-" * 50)
        print(f"FATAL ERROR: Failed to access the webpage. Please check the URL and your internet connection. Error: {e}")
    except Exception as e:
        print("-" * 50)
        print(f"FATAL ERROR: An unexpected error occurred: {e}")

if __name__ == "__main__":
    scrape_and_process()
