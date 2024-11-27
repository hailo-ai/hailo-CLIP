#!/bin/bash

# Function to check command status
check_status() {
    if [ $? -ne 0 ]; then
        echo "Error: $1"
        exit 1
    fi
}

# Step 1: Ensure the environment is set up by sourcing setup_env.sh
source setup_env.sh
check_status "Failed to set up environment. Make sure setup_env.sh is correct."

echo "Environment setup completed successfully."

# Step 2: Install required system packages
echo "Installing required system packages..."
sudo apt-get update
sudo apt-get -y install libblas-dev nlohmann-json3-dev
check_status "Failed to install system packages"

# Step 3: Install Python dependencies from requirements.txt
echo "Installing Python dependencies from requirements.txt..."
if [ -f "requirements.txt" ]; then
    python3 -m pip install -r requirements.txt
    check_status "Failed to install Python dependencies"
else
    echo "requirements.txt not found!"
    exit 1
fi

# Step 4: Install test requirements
echo "Installing test requirements..."
if [ -f "tests/test_resources/requirements.txt" ]; then
    python3 -m pip install -r tests/test_resources/requirements.txt
    check_status "Failed to install test requirements"
else
    # Create tests/test_resources directory if it doesn't exist
    mkdir -p tests/test_resources
    # Create requirements.txt file with test dependencies
    cat > tests/test_resources/requirements.txt << EOL
pytest>=7.0.0
pytest-timeout>=2.1.0
pytest-cov>=4.1.0
pytest-xdist>=3.3.1
EOL
    python3 -m pip install -r tests/test_resources/requirements.txt
    check_status "Failed to install test requirements"
fi

# Step 5: Install the package using setup.py in editable mode
echo "Installing the package using setup.py in editable mode..."
python3 -m pip install -v -e .
check_status "Failed to install the package via setup.py"

# Step 6: Download required resources (if applicable)
echo "Downloading required resources..."
if [ -f "./download_resources.sh" ]; then
    ./download_resources.sh
    check_status "Failed to download resources"
else
    echo "download_resources.sh not found!"
    exit 1
fi

# Step 7: Compile the post-process code using compile_postprocess.sh
echo "Compiling the post-process code..."
if [ -f "./compile_postprocess.sh" ]; then
    ./compile_postprocess.sh
    check_status "Post-process compilation failed"
else
    echo "compile_postprocess.sh not found!"
    exit 1
fi

# # Step 8: Run basic tests to verify installation
# echo "Running basic tests to verify installation..."
# if [ -d "tests" ]; then
#     python -m pytest tests/test_clip_app.py -v
#     check_status "Some tests failed during installation verification"
# fi

# echo "Installation completed successfully!"

# # Print verification information
# echo "Verifying installation..."
# echo "Python version: $(python3 --version)"
# echo "Installed packages:"
# pip list

# # Create a simple test script
# echo "Creating test script..."
# cat > test_installation.sh << 'EOL'
# #!/bin/bash
# source setup_env.sh
# echo "Testing CLIP application installation..."
# python -m pytest tests/test_clip_app.py -v
# EOL
# chmod +x test_installation.sh

# echo "You can verify the installation by running: ./test_installation.sh"