import pandas as pd
import os
import re

def update_news_data_with_images(csv_filename="news_data.csv", images_dir="images"):
    """
    Reads a CSV file, looks for images in a specified directory, and matches 
    them to rows in the DataFrame based on a similarity check between 
    the image filename and the title/URL columns. It then updates 
    the 'imagename' column and saves the result back to the CSV.
    """
    
    # 1. Read the CSV file
    try:
        df = pd.read_csv(csv_filename)
    except FileNotFoundError:
        print(f"Error: The file {csv_filename} was not found.")
        return

    # Initialize or reset the 'imagename' column
    df['imagename'] = None

    # 2. Get a list of image files from the 'images' directory
    try:
        all_files = os.listdir(images_dir)
        image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg')
        # Filter for files that have a common image extension
        image_files = [f for f in all_files if f.lower().endswith(image_extensions)]
    except FileNotFoundError:
        print(f"Warning: The images directory '{images_dir}' was not found. Please create it and add images.")
        image_files = []
    
    print(f"Found {len(image_files)} potential images in '{images_dir}'.")
    matched_count = 0

    # Function to clean and normalize strings for matching
    def normalize_string(s):
        s = str(s).lower()
        # Replace non-alphanumeric/non-space characters with a space
        s = re.sub(r'[^a-z0-9 ]', ' ', s) 
        # Replace multiple spaces with a single space
        s = re.sub(r'\s+', ' ', s).strip()
        return s

    # 3. Iterate and match
    for img_filename in image_files:
        # Get the filename without extension
        base_name, ext = os.path.splitext(img_filename)

        # Normalize the image filename base (replace common separators with space, then normalize)
        base_name_norm = normalize_string(base_name.replace('-', ' ').replace('_', ' '))

        # Iterate through the DataFrame rows to find a match
        for index, row in df.iterrows():
            # Clean and normalize title and url for comparison
            title_norm = normalize_string(row.get('title', ''))
            url_norm = normalize_string(row.get('url', ''))

            # --- Matching Logic ---
            is_match = False
            
            # 1. Match against Title: Check if the normalized filename is a substring of the title
            if base_name_norm and (base_name_norm in title_norm):
                 is_match = True
            
            # 2. Match against URL: Check the last part of the URL (the slug)
            # Find the last part of the URL, which is usually the 'slug'
            url_slug = url_norm.split('/')[-1]
            if not is_match and base_name_norm and (base_name_norm in url_slug):
                is_match = True
                
            if is_match:
                # Found a match, add the full filename
                df.at[index, 'imagename'] = img_filename
                matched_count += 1
                # Stop after the first match is found for this image
                break

    # 4. Save the updated DataFrame back to the CSV file
    df.to_csv(csv_filename, index=False)
    print(f"Successfully matched {matched_count} images to rows in {csv_filename} and saved the updated file.")
    print("Check the 'imagename' column in your updated news_data.csv.")

if __name__ == "__main__":
    # Assuming news_data.csv is in the same directory and images are in a subdirectory named 'images'
    update_news_data_with_images()

