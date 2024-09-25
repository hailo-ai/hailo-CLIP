#!/bin/bash

# Step 1: Ensure the environment is set up by sourcing setup_env.sh
source setup_env.sh

# Check if the environment setup was successful
if [ $? -ne 0 ]; then
    echo "Failed to set up environment. Make sure setup_env.sh is correct."
    exit 1
fi

echo "Environment setup completed successfully."

# Step 2: Install required system packages
echo "Installing required system packages..."
sudo apt-get update
sudo apt-get -y install libblas-dev nlohmann-json3-dev

# Step 3: Install Python dependencies from requirements.txt
echo "Installing Python dependencies from requirements.txt..."
if [ -f "requirements.txt" ]; then
    python3 -m pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "Failed to install Python dependencies."
        exit 1
    fi
else
    echo "requirements.txt not found!"
    exit 1
fi

# Step 4: Install the package using setup.py in editable mode
echo "Installing the package using setup.py in editable mode..."
python3 -m pip install -v -e .

if [ $? -ne 0 ]; then
    echo "Failed to install the package via setup.py."
    exit 1
fi

# Step 5: Download required resources (if applicable)
echo "Downloading required resources..."
if [ -f "./download_resources.sh" ]; then
    ./download_resources.sh
    if [ $? -ne 0 ]; then
        echo "Failed to download resources."
        exit 1
    fi
else
    echo "download_resources.sh not found!"
    exit 1
fi

# Step 6: Compile the post-process code using compile_postprocess.sh
echo "Compiling the post-process code..."
if [ -f "./compile_postprocess.sh" ]; then
    ./compile_postprocess.sh
    if [ $? -ne 0 ]; then
        echo "Post-process compilation failed."
        exit 1
    fi
else
    echo "compile_postprocess.sh not found!"
    exit 1
fi

# Step 7: Run the CLIP app with demo input
#echo "Running the CLIP app with demo input..."
#clip_app --input demo

# Optional: If you want to run with a web camera input, uncomment the following line
# clip_app --input /dev/video0
