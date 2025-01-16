import json
import os
import argparse

def parse_arguments():
        """
        Parse command-line arguments for the script.

        Returns:
        argparse.Namespace: Parsed arguments containing:
                - json_path (str): Path to the input JSON file.
                - output (str): Path to the output JSON file.
        """
        parser = argparse.ArgumentParser(description="Lables Preparation for Ad Genie")
        parser.add_argument("--json-path", "-p", type=str, default="resources/zara.json", help="Enter the path to the zara json file")
        parser.add_argument("--output", "-o", type=str, default="resources/lables.json", help="Enter the path for the output labels json")
        return parser.parse_args()
    
args = parse_arguments()

# Open the input JSON file and load its content into the `data` variable
with open(args.json_path, 'r') as file:
        data = json.load(file)

# Initialize the labels dictionary
labels = {}
labels['negative'] = []
labels['positive'] = []

# Process the input data to generate positive labels
for gender in data:
    for label in data[gender]:
        labels['positive'].append(f'a {os.path.basename(gender)} wearing a {label}')

# Write the generated labels to the specified output JSON file
with open(args.output, 'w') as file:
        json.dump(labels, file, indent=4)  