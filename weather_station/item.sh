#!/bin/bash

# Open-Meteo Docker sync script to download weather data
# This script uses the sync command to download specific weather variables

# Weather variables to download
VARIABLES=(
    "temperature_2m_max"
    "temperature_2m_min" 
    "sunrise"
    "sunset"
    "temperature_2m"
    "surface_pressure"
    "cloud_cover"
    "wind_direction_180m"
    "wind_speed_180m"
    "visibility"
    "apparent_temperature"
    "relative_humidity_2m"
    "snowfall"
    "showers"
    "rain"
    "soil_moisture_27_to_81cm"
    "soil_temperature_54cm"
    "uv_index"
)

# Default weather model
MODEL="ecmwf_ifs025"
VOLUME_NAME="open-meteo-data"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --model)
            MODEL="$2"
            shift 2
            ;;
        --volume)
            VOLUME_NAME="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Download weather data using Open-Meteo Docker sync command"
            echo ""
            echo "Options:"
            echo "  --model MODEL       Weather model (default: ecmwf_ifs025)"
            echo "  --volume VOLUME     Docker volume name (default: open-meteo-data)"
            echo "  -h, --help          Show this help message"
            echo ""
            echo "Variables to download:"
            printf '  %s\n' "${VARIABLES[@]}"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "Open-Meteo Data Download Script"
echo "==============================="
echo "Model: $MODEL"
echo "Volume: $VOLUME_NAME"
echo "Variables: ${#VARIABLES[@]} variables"
echo ""

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "Error: Docker is not running or not accessible"
    exit 1
fi

# Check if volume exists, create if not
if ! docker volume inspect "$VOLUME_NAME" >/dev/null 2>&1; then
    echo "Creating Docker volume: $VOLUME_NAME"
    docker volume create --name "$VOLUME_NAME"
fi

# Download each variable
echo "Starting data download..."
echo ""

for variable in "${VARIABLES[@]}"; do
    echo "Downloading: $variable"
    if docker run --rm -v "$VOLUME_NAME:/app/data" ghcr.io/open-meteo/open-meteo sync "$MODEL" "$variable"; then
        echo "✓ Successfully downloaded $variable"
    else
        echo "✗ Failed to download $variable"
    fi
    echo ""
done

echo "Download completed!"
echo ""
echo "To start the API server, run:"
echo "docker run -d --rm -v $VOLUME_NAME:/app/data -p 8080:8080 ghcr.io/open-meteo/open-meteo"
echo ""
echo "Then test with:"
echo "curl \"http://127.0.0.1:8080/v1/forecast?latitude=47.1&longitude=8.4&models=$MODEL&hourly=temperature_2m\""