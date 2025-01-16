import os
import csv
import ast
import requests
from collections import defaultdict
import json
import argparse
 
 
def download_images(base_dir, retries=1, dest_dir="resources/images"):
    """
    Downloads images specified in CSV files located within a directory structure.

    Args:
        base_dir (str): The base directory containing nested folders and CSV files.
        retries (int): Number of retry attempts for downloading an image in case of failure.
        dest_dir (str): Destination directory to save downloaded images.

    Outputs:
        - Downloads images to the specified destination directory.
        - Logs any failed downloads to a file named `failed_links.txt` in the base directory.
        - Saves metadata about successfully downloaded images in `resources/zara.json`.

    Notes:
        - CSV files should have an "image" column with image URLs (in a JSON-like format) and a "name" column for product names.
        - Folder names categorize data into keys like "Men" and "Women" in the JSON output.
    """
    failed_links = []
    data_dict = defaultdict(dict)
    data_dict['Men'] = defaultdict(dict)
    data_dict['Women'] = defaultdict(dict)
    for _, dirs, _ in os.walk(base_dir):
        for dir1 in dirs:
            if dir1 != dest_dir:
                for root, _, files in os.walk(os.path.join(base_dir, dir1)):
                    for file in files:
                        if file.endswith(".csv"):
                            file_path = os.path.join(root, file)
                            folder_name = os.path.basename(root)
                            csv_filename = os.path.splitext(file)[0]
                            
                            with open(file_path, 'r', encoding='utf-8') as f:
                                reader = csv.DictReader(f)
                                for row_number, row in enumerate(reader):
                                    # Normalize and handle different column naming
                                    image_field = next(
                                        (field for field in row if 'image' in field.lower()), None
                                    )
                                    product_field = next(
                                        (field for field in row if 'name' in field.lower()), None
                                    )
                                    if not image_field:
                                        print(f"No valid image column found in {file}. Skipping...")
                                        continue
                                    
                                    try:
                                        image_data = ast.literal_eval(row[image_field])
                                        for image_num, image_url in enumerate(image_data):
                                            image_link = list(image_url.keys())[0]
                                            # Generate the file name
                                            image_name = f"{folder_name}_{csv_filename}_{row_number}_{image_num}.jpg"
                                            # import ipdb; ipdb.set_trace()
                                            download_path = os.path.join(dest_dir, image_name)
 
                                            # Download the image with retry logic
                                            success = download_image_with_retry(image_link, download_path, retries)
                                            if not success:
                                                failed_links.append((image_link, download_path))
                                            else:
                                                if row[product_field] not in data_dict[folder_name].keys():
                                                    data_dict[folder_name][row[product_field]] = []
                                                data_dict[folder_name][row[product_field]].append(image_name)
                                    except (ValueError, KeyError) as e:
                                        print(f"Error processing row {row_number} in {file}: {e}")
 
    # Write all failed links to a file
    failed_links_file = os.path.join(base_dir, "failed_links.txt")
    with open(failed_links_file, 'w') as f:
        for link, path in failed_links:
            f.write(f"{link} -> {path}\n")
    print(f"Failed links logged to {failed_links_file}")
    with open('resources/zara.json', 'w') as file:
        json.dump(data_dict, file, indent=4)
 
 
def download_image_with_retry(url, save_path, retries):
    """
    Downloads an image from a URL with retry logic.
    """
    try:
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        print(f"Downloaded: {save_path}")
        return True
    except requests.RequestException as e:
        print(f"Failed for {url}: {e}")
    return False
 

def parse_arguments():
        """
    Parses command-line arguments for the script.

    Returns:
        argparse.Namespace: Parsed arguments containing:
            - data (str): Path to the base directory containing the dataset.
    """
    parser = argparse.ArgumentParser(description="Data Preparation for Ad Genie")
    parser.add_argument("--data", "-d", type=str, default="resources/zara_dataset", help="Enter the path to the zara dataset")
    return parser.parse_args()
    
# Parse arguments and run the download_images function
args = parse_arguments()
base_directory = args.data
download_images(base_directory)