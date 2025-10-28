import subprocess
import os

# --- Configuration ---
TARGET_URL = "https://wiiedu.iri.columbia.edu/"
OUTPUT_DIRECTORY = "WIIEDU"

# --- Wget Command Breakdown ---
# -r, --recursive: turn on recursive retrieving
# -l inf: set recursion depth to infinite (will try to get everything linked)
# -k, --convert-links: make links in downloaded documents suitable for local viewing
# -p, --page-requisites: download all files (images, CSS, JS) needed to display the page
# -P, --directory-prefix: set the directory where files will be saved
# -e robots=off: instruct wget to ignore robots.txt and fetch all files
# -w 1: wait 1 second between retrievals to be polite to the server
WGET_COMMAND = [
    "wget",
    "-r",
    "-l", "inf",
    "-k",
    "-p",
    "-P", OUTPUT_DIRECTORY,
    "-e", "robots=off",
    "-w", "1",
    TARGET_URL
]

def cache_website():
    """
    Executes the wget command to recursively download the target website
    and store it in the specified output directory.
    """
    print(f"Starting recursive caching of {TARGET_URL}...")
    print(f"Files will be saved into the local directory: ./{OUTPUT_DIRECTORY}")

    # Check if wget is available
    try:
        subprocess.run(["wget", "--version"], check=True, capture_output=True)
    except FileNotFoundError:
        print("\nERROR: 'wget' command not found.")
        print("Please install wget on your system to run this script.")
        return

    # Create the output directory if it doesn't exist
    if not os.path.exists(OUTPUT_DIRECTORY):
        os.makedirs(OUTPUT_DIRECTORY)
        print(f"Created directory: {OUTPUT_DIRECTORY}")

    try:
        # Run the wget command
        process = subprocess.run(
            WGET_COMMAND,
            check=True,
            text=True
        )

        if process.returncode == 0:
            print(f"\nSuccessfully cached the materials to ./{OUTPUT_DIRECTORY}/")
        else:
            print(f"\nwget command finished with return code {process.returncode}")

    except subprocess.CalledProcessError as e:
        print(f"\nAn error occurred during the caching process:")
        print(e)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

if __name__ == "__main__":
    cache_website()

