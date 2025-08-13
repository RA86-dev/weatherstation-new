#!/usr/bin/env python3
"""
Weather Data Updater v2.0
Enhanced weather data fetcher with self-hosted Open-Meteo support
"""

import requests
import json
import time
import os
import argparse
from urllib.parse import quote
from typing import Dict, List, Tuple, Optional
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WeatherDataUpdater:
    """Enhanced weather data updater with multiple API source support"""
    
    def __init__(self, api_base_url: str = "https://api.open-meteo.com", 
                 retry_delay: int = 5, max_retries: int = 3):
        self.api_base_url = api_base_url.rstrip('/')
        self.retry_delay = retry_delay
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'WeatherStation/2.0 (Enhanced Data Fetcher)'
        })
        
        # Weather parameters to fetch
        self.weather_params = [
            'temperature_2m', 'relative_humidity_2m', 'dew_point_2m', 
            'apparent_temperature', 'precipitation_probability', 'precipitation',
            'rain', 'showers', 'snowfall', 'snow_depth', 'pressure_msl',
            'surface_pressure', 'cloud_cover', 'vapour_pressure_deficit',
            'wind_speed_10m', 'wind_direction_10m', 'soil_temperature_0cm',
            'soil_moisture_0_to_1cm'
        ]
        
    def load_locations(self, filepath: str = 'geolocations.json') -> Dict[str, List[float]]:
        """Load city locations from JSON file"""
        try:
            with open(filepath, 'r') as file:
                locations = json.load(file)
                logger.info(f"Loaded {len(locations)} locations from {filepath}")
                return locations
        except FileNotFoundError:
            logger.error(f"Location file {filepath} not found")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {filepath}: {e}")
            return {}
    
    def fetch_weather_data(self, city: str, coordinates: List[float], 
                          past_days: int = 92) -> Dict:
        """Fetch weather data for a specific city with retry logic"""
        latitude, longitude = coordinates
        
        # Build API URL
        params = {
            'latitude': latitude,
            'longitude': longitude,
            'hourly': ','.join(self.weather_params),
            'past_days': past_days,
            'timezone': 'auto'
        }
        
        url = f"{self.api_base_url}/v1/forecast"
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.info(f"Fetching data for {city} (attempt {attempt + 1}/{self.max_retries + 1})")
                
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                logger.info(f"✓ Successfully fetched data for {city}")
                return data
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Failed to fetch data for {city}: {e}")
                
                if attempt < self.max_retries:
                    logger.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"✗ Failed to fetch data for {city} after {self.max_retries + 1} attempts")
                    return {}
            
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON response for {city}: {e}")
                return {}
        
        return {}
    
    def validate_data(self, data: Dict, city: str) -> bool:
        """Validate fetched weather data"""
        if not data:
            return False
            
        required_keys = ['hourly', 'latitude', 'longitude']
        if not all(key in data for key in required_keys):
            logger.warning(f"Missing required keys in data for {city}")
            return False
            
        hourly_data = data.get('hourly', {})
        if not hourly_data or 'time' not in hourly_data:
            logger.warning(f"No hourly time data for {city}")
            return False
            
        # Check if we have at least some weather parameters
        param_count = sum(1 for param in self.weather_params if param in hourly_data)
        if param_count < len(self.weather_params) * 0.5:  # At least 50% of parameters
            logger.warning(f"Insufficient weather parameters for {city} ({param_count}/{len(self.weather_params)})")
        
        logger.info(f"Data validation passed for {city}")
        return True
    
    def update_all_locations(self, locations_file: str = 'geolocations.json', 
                           output_file: str = 'output_data.json',
                           past_days: int = 92) -> Dict:
        """Update weather data for all locations"""
        logger.info("Starting weather data update process...")
        
        # Load locations
        locations = self.load_locations(locations_file)
        if not locations:
            logger.error("No locations to process")
            return {}
        
        output = {}
        successful_updates = 0
        
        # Process each location
        for i, (city, coordinates) in enumerate(locations.items(), 1):
            logger.info(f"Processing {city} ({i}/{len(locations)})")
            
            try:
                data = self.fetch_weather_data(city, coordinates, past_days)
                
                if self.validate_data(data, city):
                    output[city] = data
                    successful_updates += 1
                else:
                    logger.warning(f"Skipping {city} due to invalid data")
                    
            except Exception as e:
                logger.error(f"Unexpected error processing {city}: {e}")
            
            # Add small delay between requests to be respectful
            if i < len(locations):
                time.sleep(1)
        
        # Save results
        if output:
            try:
                with open(output_file, 'w') as file:
                    json.dump(output, file, indent=2)
                logger.info(f"✓ Saved weather data for {successful_updates}/{len(locations)} locations to {output_file}")
            except Exception as e:
                logger.error(f"Failed to save output file: {e}")
        else:
            logger.error("No data to save")
        
        return output
    
    def check_api_status(self) -> bool:
        """Check if the API endpoint is accessible"""
        try:
            logger.info(f"Checking API status at {self.api_base_url}")
            response = self.session.get(f"{self.api_base_url}/v1/forecast?latitude=0&longitude=0", timeout=10)
            if response.status_code == 200:
                logger.info("✓ API is accessible")
                return True
            else:
                logger.warning(f"API returned status code: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"API not accessible: {e}")
            return False

def main():
    """Main function with command-line interface"""
    parser = argparse.ArgumentParser(description='Weather Station Data Updater v2.0')
    parser.add_argument('--api-url', default='https://api.open-meteo.com',
                       help='Open-Meteo API base URL (default: https://api.open-meteo.com)')
    parser.add_argument('--self-hosted', action='store_true',
                       help='Use self-hosted Open-Meteo instance at localhost:8080')
    parser.add_argument('--locations', default='geolocations.json',
                       help='Path to locations JSON file (default: geolocations.json)')
    parser.add_argument('--output', default='output_data.json',
                       help='Output JSON file (default: output_data.json)')
    parser.add_argument('--past-days', type=int, default=92,
                       help='Number of past days to fetch (default: 92)')
    parser.add_argument('--retries', type=int, default=3,
                       help='Maximum number of retry attempts (default: 3)')
    parser.add_argument('--retry-delay', type=int, default=5,
                       help='Delay between retries in seconds (default: 5)')
    
    args = parser.parse_args()
    
    # Determine API URL
    if args.self_hosted:
        api_url = 'https://backend.weatherbox.org'
        logger.info("Using self-hosted Open-Meteo instance")
    else:
        api_url = args.api_url
        logger.info(f"Using external API: {api_url}")
    
    # Create updater instance
    updater = WeatherDataUpdater(
        api_base_url=api_url,
        retry_delay=args.retry_delay,
        max_retries=args.retries
    )
    
    # Check API status first
    if not updater.check_api_status():
        logger.error("API is not accessible. Please check your connection or API URL.")
        if args.self_hosted:
            logger.error("Make sure your self-hosted Open-Meteo instance is running.")
        return 1
    
    # Update data
    result = updater.update_all_locations(
        locations_file=args.locations,
        output_file=args.output,
        past_days=args.past_days
    )
    
    if result:
        logger.info("Weather data update completed successfully!")
        return 0
    else:
        logger.error("Weather data update failed!")
        return 1

if __name__ == "__main__":
    exit(main())