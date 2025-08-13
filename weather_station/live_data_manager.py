"""
Live Weather Data Manager
=========================
Handles live data fetching from self-hosted Open-Meteo API.
"""

import json
import time
import logging
from typing import Dict, Optional, List
import requests
from datetime import datetime

from .config import get_config

logger = logging.getLogger(__name__)


class LiveWeatherDataManager:
    """Manages live weather data fetching from self-hosted Open-Meteo API"""
    
    def __init__(self):
        self.config = get_config()
        self._locations_cache = None
        self._locations_cache_time = 0
        
    def load_locations(self) -> Dict:
        """Load locations from geolocations.json with caching"""
        current_time = time.time()
        
        # Cache locations for 5 minutes
        if (self._locations_cache is None or 
            current_time - self._locations_cache_time > 300):
            
            try:
                with open(self.config.LOCATIONS_FILE, 'r') as f:
                    self._locations_cache = json.load(f)
                self._locations_cache_time = current_time
                logger.info(f"Loaded {len(self._locations_cache)} locations")
            except Exception as e:
                logger.error(f"Error loading locations: {e}")
                self._locations_cache = {}
                
        return self._locations_cache or {}
    
    def get_weather_data(self, city: str = None) -> Optional[Dict]:
        """Get live weather data for a specific city or all cities"""
        locations = self.load_locations()
        
        if not locations:
            logger.error("No locations available")
            return None
        
        if city:
            # Get data for specific city
            if city not in locations:
                logger.error(f"City '{city}' not found in locations")
                return None
            
            coordinates = locations[city]
            return self._fetch_live_weather_data(city, coordinates)
        
        # Get data for all cities (this could be expensive, so limit concurrent requests)
        return self._fetch_multiple_cities_data(locations)
    
    def _fetch_multiple_cities_data(self, locations: Dict, limit: int = 300) -> Dict:
        """Fetch data for multiple cities with rate limiting and improved error handling"""
        result = {}
        count = 0
        errors = 0
        start_time = time.time()
        
        logger.info(f"Starting batch fetch for up to {min(limit, len(locations))} cities")
        
        for city, coordinates in locations.items():
            if limit and count >= limit:
                logger.info(f"Reached limit of {limit} cities for batch request")
                break
            
            try:
                data = self._fetch_live_weather_data(city, coordinates)
                if data:
                    result[city] = data
                    count += 1
                else:
                    errors += 1
                    logger.warning(f"No data returned for {city}")
            except Exception as e:
                errors += 1
                logger.error(f"Error fetching data for {city}: {e}")
                # Continue with other cities
                continue
            
            # Rate limiting - reduced for self-hosted API
            if count < len(locations) - 1 and count % 10 != 9:  # No delay every 10th request
                time.sleep(0.001)  # Much faster for self-hosted API
            
            # Progress logging every 10 cities
            if count > 0 and count % 10 == 0:
                elapsed = time.time() - start_time
                rate = count / elapsed
                logger.info(f"Progress: {count} cities fetched in {elapsed:.1f}s ({rate:.1f} cities/s)")
        
        elapsed = time.time() - start_time
        logger.info(f"Batch fetch completed: {len(result)} cities in {elapsed:.1f}s, {errors} errors")
        return result
    
    def _fetch_live_weather_data(self, city: str, coordinates: List[float]) -> Optional[Dict]:
        """Fetch live weather data for a specific city from self-hosted API"""
        try:
            latitude, longitude = coordinates
            
            # Weather parameters for self-hosted Open-Meteo API
            weather_params = [
                'temperature_2m', 'relative_humidity_2m', 'dew_point_2m', 
                'apparent_temperature', 'precipitation_probability', 'precipitation',
                'rain', 'showers', 'snowfall', 'snow_depth', 'pressure_msl',
                'surface_pressure', 'cloud_cover', 'visibility', 'uv_index',
                'wind_speed_10m', 'wind_direction_10m', 'wind_gusts_10m',
                'soil_temperature_0cm', 'soil_moisture_0_to_1cm'
            ]
            
            # Build API URL for self-hosted Open-Meteo API
            params = {
                'latitude': latitude,
                'longitude': longitude,
                'hourly': ','.join(weather_params),
                'past_days': 1,  # Only get recent data for live fetching
                'forecast_days': 7,  # Get 7 days of forecast
                'timezone': 'auto',
                'models': 'ecmwf_ifs025,ncep_gfs025,meteofrance_arpege_world025'  # Specify available models
            }
            
            api_url = f"{self.config.effective_open_meteo_url}/v1/forecast"
            
            # Shorter timeout for live data
            response = requests.get(api_url, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            
            # Normalize field names from model-specific to generic
            data = self._normalize_field_names(data)
            
            # Add metadata
            data['city'] = city
            data['coordinates'] = coordinates
            data['latitude'] = latitude
            data['longitude'] = longitude
            data['fetch_time'] = datetime.now().isoformat()
            
            return data
            
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout fetching live data for {city}")
            return None
        except requests.exceptions.ConnectionError:
            logger.warning(f"Connection error fetching live data for {city}")
            return None
        except Exception as e:
            logger.warning(f"Failed to fetch live data for {city}: {e}")
            return None
    
    def _normalize_field_names(self, data):
        """Normalize model-specific field names to generic field names"""
        if not data or 'hourly' not in data:
            return data
        
        hourly = data['hourly']
        normalized_hourly = {}
        
        # Field name mapping patterns - from model-specific to generic
        field_mappings = {
            'temperature_2m': ['temperature_2m_ecmwf_ifs025', 'temperature_2m_ncep_gfs025', 'temperature_2m_meteofrance_arpege_world025'],
            'relative_humidity_2m': ['relative_humidity_2m_ecmwf_ifs025', 'relative_humidity_2m_ncep_gfs025', 'relative_humidity_2m_meteofrance_arpege_world025'],
            'pressure_msl': ['pressure_msl_ecmwf_ifs025', 'pressure_msl_ncep_gfs025', 'pressure_msl_meteofrance_arpege_world025'],
            'wind_speed_10m': ['wind_speed_10m_ecmwf_ifs025', 'wind_speed_10m_ncep_gfs025', 'wind_speed_10m_meteofrance_arpege_world025'],
            'wind_direction_10m': ['wind_direction_10m_ecmwf_ifs025', 'wind_direction_10m_ncep_gfs025', 'wind_direction_10m_meteofrance_arpege_world025'],
            'precipitation': ['precipitation_ecmwf_ifs025', 'precipitation_ncep_gfs025', 'precipitation_meteofrance_arpege_world025'],
            'dew_point_2m': ['dew_point_2m_ecmwf_ifs025', 'dew_point_2m_ncep_gfs025', 'dew_point_2m_meteofrance_arpege_world025'],
            'apparent_temperature': ['apparent_temperature_ecmwf_ifs025', 'apparent_temperature_ncep_gfs025', 'apparent_temperature_meteofrance_arpege_world025']
        }
        
        # Copy time field
        if 'time' in hourly:
            normalized_hourly['time'] = hourly['time']
        
        # Normalize field names
        for generic_name, model_specific_names in field_mappings.items():
            for model_specific_name in model_specific_names:
                if model_specific_name in hourly:
                    normalized_hourly[generic_name] = hourly[model_specific_name]
                    break  # Use first available model
        
        # Copy any fields that don't need normalization
        for field_name, field_data in hourly.items():
            if field_name not in normalized_hourly and not any(field_name in models for models in field_mappings.values()):
                normalized_hourly[field_name] = field_data
        
        data['hourly'] = normalized_hourly
        return data
    
    def get_current_conditions(self, city: str) -> Optional[Dict]:
        """Get current weather conditions for a specific city"""
        data = self.get_weather_data(city)
        if not data or 'hourly' not in data:
            return None
        
        try:
            hourly = data['hourly']
            current_hour_index = -1  # Get the latest available data
            
            current_conditions = {
                'city': city,
                'coordinates': data.get('coordinates', []),
                'timezone': data.get('timezone', 'UTC'),
                'fetch_time': data.get('fetch_time'),
                'current': {}
            }
            
            # Extract current conditions
            for param, values in hourly.items():
                if isinstance(values, list) and len(values) > abs(current_hour_index):
                    current_conditions['current'][param] = values[current_hour_index]
            
            return current_conditions
            
        except Exception as e:
            logger.error(f"Error extracting current conditions for {city}: {e}")
            return None
    
    def get_api_status(self) -> Dict:
        """Check if the self-hosted Open-Meteo API is accessible"""
        try:
            # Test API with a simple request
            test_url = f"{self.config.effective_open_meteo_url}/v1/forecast"
            params = {
                'latitude': 40.7,
                'longitude': -74.0,
                'hourly': 'temperature_2m,relative_humidity_2m,pressure_msl,wind_speed_10m',
                'forecast_days': 1,
                'models': 'ecmwf_ifs025,ncep_gfs025,meteofrance_arpege_world025'
            }
            
            start_time = time.time()
            response = requests.get(test_url, params=params, timeout=10)
            response_time = time.time() - start_time
            
            return {
                'accessible': response.status_code == 200,
                'response_time_ms': int(response_time * 1000),
                'api_url': self.config.effective_open_meteo_url,
                'status_code': response.status_code,
                'self_hosted': self.config.USE_SELF_HOSTED,
                'live_data_enabled': self.config.LIVE_DATA_ENABLED
            }
            
        except Exception as e:
            return {
                'accessible': False,
                'response_time_ms': -1,
                'api_url': self.config.effective_open_meteo_url,
                'status_code': -1,
                'error': str(e),
                'self_hosted': self.config.USE_SELF_HOSTED,
                'live_data_enabled': self.config.LIVE_DATA_ENABLED
            }


# Global instance
_live_data_manager: Optional[LiveWeatherDataManager] = None


def get_live_data_manager() -> LiveWeatherDataManager:
    """Get global live data manager instance"""
    global _live_data_manager
    if _live_data_manager is None:
        _live_data_manager = LiveWeatherDataManager()
    return _live_data_manager