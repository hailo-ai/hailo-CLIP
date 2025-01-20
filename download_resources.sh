#!/bin/bash

set -e  # Exit immediately if a command exits with a non-zero status

# Set the resource directory
RESOURCE_DIR="./resources"
mkdir -p "$RESOURCE_DIR"

# Define download function with file existence check and retries
download_model() {
  file_name=$(basename "$1")
  if [ ! -f "$RESOURCE_DIR/$file_name" ]; then
    echo "Downloading $file_name..."
    wget --tries=3 --retry-connrefused --quiet --show-progress "$1" -P "$RESOURCE_DIR" || {
      echo "Failed to download $file_name after multiple attempts."
      exit 1
    }
  else
    echo "File $file_name already exists. Skipping download."
  fi
}

# Define all URLs in arrays
H8_HEFS=(
  "https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.9.0/clip_resnet_50x4.hef"
  "https://hailo-tappas.s3.eu-west-2.amazonaws.com/v3.26/general/hefs/yolov5s_personface.hef"
)

H8L_HEFS=(
  "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hefs/h8l_rpi/clip_resnet_50x4_h8l.hef"
  "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hefs/h8l_rpi/yolov5s_personface_h8l_pi.hef"
)

VIDEOS=(
  "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/video/clip_example.mp4"
)

# If --all flag is provided, download everything in parallel
if [ "$1" == "--all" ]; then
  echo "Downloading all models and video resources..."
  for url in "${H8_HEFS[@]}" "${H8L_HEFS[@]}" "${VIDEOS[@]}"; do
    download_model "$url" &
  done
else
  if [ "$DEVICE_ARCHITECTURE" == "HAILO8L" ]; then
    echo "Downloading HAILO8L models..."
    for url in "${H8L_HEFS[@]}"; do
      download_model "$url" &
    done
  elif [ "$DEVICE_ARCHITECTURE" == "HAILO8" ]; then
    echo "Downloading HAILO8 models..."
    for url in "${H8_HEFS[@]}"; do
      download_model "$url" &
    done
  fi
fi

# Download additional videos
for url in "${VIDEOS[@]}"; do
  download_model "$url" &
done

# Wait for all background downloads to complete
wait

echo "All downloads completed successfully!"