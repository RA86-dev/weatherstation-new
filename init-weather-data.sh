#!/bin/bash

echo "🌤️  Initializing Open-Meteo with weather data..."
echo "==============================================="

# Wait for Open-Meteo container to be ready
echo "⏳ Waiting for Open-Meteo container to start..."
sleep 10

# Check if Open-Meteo is running
if ! docker ps | grep -q openmeteo-api; then
    echo "❌ Open-Meteo container is not running!"
    exit 1
fi

echo "✅ Open-Meteo container is running"

# Download essential weather models with core variables for US weather
echo "📡 Downloading weather data models..."

# Download global weather models for worldwide coverage (5-7 days of data)
echo "🌍 Downloading global weather model data for worldwide coverage..."

# 1. ECMWF IFS 0.25° Global (best global coverage, 10 days forecast)
echo "⬇️  Downloading ECMWF IFS Global model (worldwide coverage)..."
docker run --rm \
    -v openmeteo-api:/app/data \
    ghcr.io/open-meteo/open-meteo \
    sync ecmwf_ifs025 \
    temperature_2m,relative_humidity_2m,pressure_msl,wind_speed_10m,wind_direction_10m,precipitation \
    --past-days 3

if [ $? -eq 0 ]; then
    echo "✅ ECMWF IFS Global model downloaded successfully"
else
    echo "⚠️  ECMWF download failed, continuing with other models..."
fi

# 2. NOAA GFS 0.25° (Global Forecast System - worldwide, 16 days)
echo "⬇️  Downloading NOAA GFS 0.25° model (worldwide coverage)..."
docker run --rm \
    -v openmeteo-api:/app/data \
    ghcr.io/open-meteo/open-meteo \
    sync ncep_gfs025 \
    temperature_2m,relative_humidity_2m,pressure_msl,wind_speed_10m,wind_direction_10m,precipitation \
    --past-days 3

if [ $? -eq 0 ]; then
    echo "✅ NOAA GFS 0.25° model downloaded successfully"
else
    echo "⚠️  NOAA GFS 0.25° download failed"
fi

# 3. MeteoFrance ARPEGE World 0.25° (global coverage)
echo "⬇️  Downloading MeteoFrance ARPEGE World model..."
docker run --rm \
    -v openmeteo-api:/app/data \
    ghcr.io/open-meteo/open-meteo \
    sync meteofrance_arpege_world025 \
    temperature_2m,relative_humidity_2m,pressure_msl,wind_speed_10m,wind_direction_10m,precipitation \
    --past-days 3

if [ $? -eq 0 ]; then
    echo "✅ MeteoFrance ARPEGE World model downloaded successfully"
else
    echo "⚠️  MeteoFrance ARPEGE World download failed"
fi

# 4. JMA GSM (Japan Meteorological Agency Global Spectral Model - Asia/Pacific coverage)
echo "⬇️  Downloading JMA GSM model (Asia/Pacific coverage)..."
docker run --rm \
    -v openmeteo-api:/app/data \
    ghcr.io/open-meteo/open-meteo \
    sync jma_gsm \
    temperature_2m,relative_humidity_2m,pressure_msl,wind_speed_10m,wind_direction_10m,precipitation \
    --past-days 3

if [ $? -eq 0 ]; then
    echo "✅ JMA GSM model downloaded successfully"
else
    echo "⚠️  JMA GSM download failed"
fi

# 5. CMA GRAPES Global (China Meteorological Administration - global coverage)
echo "⬇️  Downloading CMA GRAPES Global model..."
docker run --rm \
    -v openmeteo-api:/app/data \
    ghcr.io/open-meteo/open-meteo \
    sync cma_grapes_global \
    temperature_2m,relative_humidity_2m,pressure_msl,wind_speed_10m,wind_direction_10m,precipitation \
    --past-days 3

if [ $? -eq 0 ]; then
    echo "✅ CMA GRAPES Global model downloaded successfully"
else
    echo "⚠️  CMA GRAPES Global download failed"
fi

# 6. BOM ACCESS Global (Australian Bureau of Meteorology - global coverage)
echo "⬇️  Downloading BOM ACCESS Global model..."
docker run --rm \
    -v openmeteo-api:/app/data \
    ghcr.io/open-meteo/open-meteo \
    sync bom_access_global \
    temperature_2m,relative_humidity_2m,pressure_msl,wind_speed_10m,wind_direction_10m,precipitation \
    --past-days 3

if [ $? -eq 0 ]; then
    echo "✅ BOM ACCESS Global model downloaded successfully"
else
    echo "⚠️  BOM ACCESS Global download failed"
fi

echo ""
echo "🎉 Weather data initialization complete!"
echo "🌐 Open-Meteo API is ready at: http://localhost:8080"
echo ""
echo "Test with:"
echo "curl 'http://localhost:8080/v1/forecast?latitude=40.7&longitude=-74.0&hourly=temperature_2m'"