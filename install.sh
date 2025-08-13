#!/bin/bash

#
# Weather Station v2.0 - Super Simple Installation
# ==============================================
#

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}"
echo "🌤️  Weather Station v2.0 - SELF-HOSTED Install"
echo "==============================================="
echo "This installs a completely self-hosted weather station"
echo "with local Open-Meteo API - NO external dependencies!"
echo -e "${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found. Please install Docker first.${NC}"
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker is ready${NC}"

# Clone repository
REPO_DIR="weather-station"
if [ -d "$REPO_DIR" ]; then
    echo "⚠️  Directory exists. Removing old installation..."
    rm -rf "$REPO_DIR"
fi

echo "📥 Downloading Weather Station..."
git clone https://github.com/RA86-dev/v2weatherstation.git "$REPO_DIR"
cd "$REPO_DIR/WeatherStation/weather_station"

# Start the application
echo "🚀 Starting Weather Station..."
docker compose up --build -d

echo ""
echo -e "${GREEN}✅ SELF-HOSTED Installation Complete!${NC}"
echo ""
echo "⏳ IMPORTANT: Wait 2-3 minutes for Open-Meteo to initialize"
echo ""
echo "🌐 Access URLs:"
echo "   • Weather Station: http://localhost:8110"
echo "   • Self-hosted Open-Meteo API: http://localhost:8080"
echo ""
echo "📊 API endpoints:"
echo "   • Health: http://localhost:8110/health"
echo "   • Weather data: http://localhost:8110/api/data/weather"
echo "   • Locations: http://localhost:8110/api/data/locations"
echo ""
echo "🛠️  Management commands:"
echo "   • View logs: docker compose logs -f"
echo "   • Stop: docker compose down"
echo "   • Check Open-Meteo: curl http://localhost:8080/v1/forecast?latitude=40.7&longitude=-74.0"
echo ""
echo -e "${GREEN}🎉 Enjoy your SELF-HOSTED Weather Station!${NC}"