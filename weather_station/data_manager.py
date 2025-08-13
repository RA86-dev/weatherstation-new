"""
Weather Data Manager
====================
Handles automatic data updates, validation, and retention policies.
"""

import json
import os
import time
import asyncio
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple, List
import logging
import subprocess

from .config import get_config

logger = logging.getLogger(__name__)


class WeatherDataManager:
    """Manages weather data updates, validation, and retention"""
    
    def __init__(self):
        self.config = get_config()
        self.update_thread: Optional[threading.Thread] = None
        self.should_stop = threading.Event()
        self._last_update_check = 0
        self._data_cache = None
        self._cache_timestamp = 0
        
    def start_background_updates(self):
        """Start background thread for automatic data updates"""
        if not self.config.AUTO_UPDATE_ENABLED:
            logger.info("Automatic data updates disabled")
            return
            
        if self.update_thread and self.update_thread.is_alive():
            logger.warning("Background update thread already running")
            return
            
        logger.info(f"Starting automatic data file updates (every {self.config.DATA_UPDATE_INTERVAL} seconds)")
        self.should_stop.clear()
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
    
    def stop_background_updates(self):
        """Stop background data updates"""
        if self.update_thread:
            logger.info("Stopping background data updates")
            self.should_stop.set()
            self.update_thread.join(timeout=10)
    
    def _update_loop(self):
        """Background update loop for periodic data file updates"""        
        logger.info("Background update loop started")
        
        # Wait 30 seconds after startup before first check
        self.should_stop.wait(30)
        
        # Check immediately on startup if data needs updating
        if not self.should_stop.is_set() and self.should_update_data():
            logger.info("Data file needs updating on startup")
            success = self._perform_update()
            if success:
                logger.info("✅ Startup data update completed successfully")
            else:
                logger.warning("⚠️ Startup data update failed, will retry in next cycle")
        
        while not self.should_stop.is_set():
            try:
                # Check every 6 hours if data needs updating
                check_interval = 21600  # 6 hours
                self.should_stop.wait(check_interval)
                
                if not self.should_stop.is_set() and self.should_update_data():
                    logger.info("Performing scheduled background data update")
                    success = self._perform_update()
                    
                    if success:
                        logger.info("✅ Background data update completed successfully")
                    else:
                        logger.warning("⚠️ Background data update failed, will retry in next cycle")
                
            except Exception as e:
                logger.error(f"Error in background update loop: {e}")
                # Wait 10 minutes on error before retrying
                self.should_stop.wait(600)
    
    def should_update_data(self) -> bool:
        """Check if data file needs updating (every 7 days)"""
        try:
            output_file = Path(self.config.OUTPUT_DATA_FILE)
            
            if not output_file.exists():
                logger.info("Data file does not exist, update needed")
                return True
            
            # Check file age
            file_mtime = output_file.stat().st_mtime
            current_time = time.time()
            file_age_seconds = current_time - file_mtime
            
            # Update every 7 days (604800 seconds)
            needs_update = file_age_seconds >= self.config.DATA_UPDATE_INTERVAL
            
            if needs_update:
                logger.info(f"Data file update needed - {file_age_seconds/3600:.1f}h since last update")
            
            return needs_update
            
        except Exception as e:
            logger.error(f"Error checking if update needed: {e}")
            return True  # Update on error to be safe
    
    def get_data_info(self) -> Dict:
        """Get information about data file system"""
        try:
            output_file = Path(self.config.OUTPUT_DATA_FILE)
            
            # Check if data file exists
            file_exists = output_file.exists()
            file_size_mb = 0.0
            data_age = "Unknown"
            location_count = 0
            
            if file_exists:
                # Get file size in MB
                file_size_bytes = output_file.stat().st_size
                file_size_mb = file_size_bytes / (1024 * 1024)
                
                # Calculate file age
                file_mtime = output_file.stat().st_mtime
                age_seconds = time.time() - file_mtime
                if age_seconds < 60:
                    data_age = f"{int(age_seconds)}s ago"
                elif age_seconds < 3600:
                    data_age = f"{int(age_seconds/60)}m ago"
                elif age_seconds < 86400:
                    data_age = f"{int(age_seconds/3600)}h ago"
                else:
                    data_age = f"{int(age_seconds/86400)}d ago"
                
                # Count locations in file
                try:
                    with open(output_file, 'r') as f:
                        data = json.load(f)
                        location_count = len(data)
                except:
                    location_count = 0
            
            # Check API accessibility for updates
            is_api_accessible = True
            try:
                import requests
                response = requests.get(f"{self.config.effective_open_meteo_url}/v1/forecast?latitude=0&longitude=0", timeout=5)
                is_api_accessible = response.status_code == 200
            except:
                is_api_accessible = False
            
            return {
                'exists': file_exists,
                'live_fetch': False,
                'api_accessible': is_api_accessible,
                'api_url': self.config.effective_open_meteo_url,
                'location_count': location_count,
                'last_update_check': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()) if file_exists else 'Never',
                'is_valid': file_exists and location_count > 0,
                'record_count': location_count,
                'file_size_mb': file_size_mb,
                'data_age': data_age,
                'retention_days': self.config.DATA_RETENTION_DAYS,
                'update_interval_hours': self.config.DATA_UPDATE_INTERVAL / 3600
            }
            
        except Exception as e:
            logger.error(f"Error getting data info: {e}")
            return {
                'exists': False,
                'live_fetch': False,
                'api_accessible': False,
                'api_url': self.config.effective_open_meteo_url,
                'location_count': 0,
                'last_update_check': 'Never',
                'is_valid': False,
                'record_count': 0,
                'file_size_mb': 0.0,
                'data_age': 'Unknown',
                'retention_days': self.config.DATA_RETENTION_DAYS,
                'update_interval_hours': self.config.DATA_UPDATE_INTERVAL / 3600
            }
    
    
    def _perform_update(self):
        """Update the data file by fetching fresh data from API"""
        try:
            logger.info("Starting data file update...")
            
            # Load locations
            locations = self._load_locations()
            if not locations:
                logger.error("No locations to fetch data for")
                return False
            
            # Fetch fresh data with rate limiting
            logger.info(f"Fetching data for {len(locations)} locations...")
            fresh_data = self._fetch_data_with_rate_limiting(locations)
            
            if not fresh_data:
                logger.error("Failed to fetch any data")
                return False
            
            # Save to output_data.json
            output_file = Path(self.config.OUTPUT_DATA_FILE)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w') as f:
                json.dump(fresh_data, f, indent=2)
            
            logger.info(f"✅ Data file updated successfully with {len(fresh_data)} locations ({output_file.stat().st_size / 1024 / 1024:.1f} MB)")
            return True
            
        except Exception as e:
            logger.error(f"Error updating data file: {e}")
            return False
    
    def force_update(self) -> bool:
        """Force an immediate data file update"""
        logger.info("Forcing immediate data file update")
        return self._perform_update()
    
    def refresh_cache(self) -> bool:
        """Alias for force_update to maintain compatibility"""
        return self.force_update()
    
    def load_weather_data(self) -> Optional[Dict]:
        """Load weather data from output_data.json file"""
        try:
            output_file = Path(self.config.OUTPUT_DATA_FILE)
            
            if not output_file.exists():
                logger.warning(f"Data file not found: {output_file}")
                return None
            
            with open(output_file, 'r') as f:
                data = json.load(f)
            
            logger.info(f"✓ Loaded weather data from file ({len(data)} locations)")
            return data
            
        except Exception as e:
            logger.error(f"Error loading weather data from file: {e}")
            return None
    
    def _fetch_data_with_rate_limiting(self, locations: Dict) -> Dict:
        """Fetch data with proper rate limiting and ensure minimum 100 valid locations"""
        live_data = {}
        total_locations = len(locations)
        completed = 0
        failed = 0
        min_locations_target = 100
        
        logger.info(f"Starting data fetch for {total_locations} locations (target: min {min_locations_target} valid)")
        
        for city, coordinates in locations.items():
            try:
                # Add delay to respect rate limits (1 request per second)
                if completed > 0:
                    time.sleep(1.1)  # Slightly over 1 second to be safe
                
                data = self._fetch_live_weather_data(city, coordinates)
                if data and self._has_valid_weather_data(data):
                    live_data[city] = data
                    completed += 1
                    
                    # Log progress every 20 locations
                    if completed % 20 == 0:
                        logger.info(f"Progress: {completed}/{total_locations} locations fetched ({completed/total_locations*100:.1f}%)")
                    
                    # Stop early if we have enough valid data (optional optimization)
                    # if completed >= 150:  # Allow up to 150 for better coverage
                    #     logger.info(f"Reached sufficient coverage with {completed} locations")
                    #     break
                        
                else:
                    failed += 1
                    if data:
                        logger.debug(f"No valid weather data for {city} (API returned nulls)")
                    else:
                        logger.warning(f"No data received for {city}")
                    
            except Exception as e:
                failed += 1
                logger.warning(f"Failed to fetch data for {city}: {e}")
                continue
        
        success_rate = (completed / total_locations) * 100
        logger.info(f"Data fetch completed: {completed} valid locations, {failed} failed ({success_rate:.1f}% success rate)")
        
        if completed < min_locations_target:
            logger.warning(f"⚠️ Only {completed} locations have valid data (target: {min_locations_target})")
            logger.warning("This might be due to API issues or missing weather data")
        else:
            logger.info(f"✅ Successfully fetched {completed} locations with valid weather data")
        
        return live_data
    
    def _has_valid_weather_data(self, data: Dict) -> bool:
        """Check if weather data contains valid (non-null) values"""
        if not data or 'hourly' not in data:
            return False
        
        hourly = data['hourly']
        
        # Check key weather parameters for any non-null values
        key_params = ['temperature_2m', 'pressure_msl', 'relative_humidity_2m', 'wind_speed_10m']
        
        for param in key_params:
            if param in hourly and isinstance(hourly[param], list):
                # Check if at least 25% of values are non-null
                values = hourly[param]
                non_null_count = sum(1 for v in values if v is not None)
                if non_null_count > len(values) * 0.25:  # At least 25% non-null
                    return True
        
        return False
    
    def _load_locations(self) -> Dict:
        """Load locations from geolocations.json"""
        try:
            with open(self.config.LOCATIONS_FILE, 'r') as f:
                locations = json.load(f)
            logger.info(f"Loaded {len(locations)} locations")
            return locations
        except Exception as e:
            logger.error(f"Error loading locations: {e}")
            return {}
    
    def _fetch_live_weather_data(self, city: str, coordinates: List[float]) -> Optional[Dict]:
        """Fetch live weather data for a specific city"""
        try:
            import requests
            
            latitude, longitude = coordinates
            
            # Weather parameters for official Open-Meteo API
            weather_params = [
                'temperature_2m', 'relative_humidity_2m', 'dew_point_2m', 
                'apparent_temperature', 'precipitation_probability', 'precipitation',
                'rain', 'showers', 'snowfall', 'snow_depth', 'pressure_msl',
                'surface_pressure', 'cloud_cover', 'visibility', 'uv_index',
                'wind_speed_10m', 'wind_direction_10m', 'wind_gusts_10m',
                'soil_temperature_0cm', 'soil_moisture_0_to_1cm'
            ]
            
            # Build API URL for configured Open-Meteo API
            params = {
                'latitude': latitude,
                'longitude': longitude,
                'hourly': ','.join(weather_params),
                'past_days': self.config.PAST_DAYS,
                'forecast_days': 7,  # Get 7 days of forecast
                'timezone': 'auto'
            }
            
            # Add models parameter if using self-hosted API
            if 'localhost' in self.config.effective_open_meteo_url:
                params['models'] = 'ecmwf_ifs025,ncep_gfs025,meteofrance_arpege_world025'
            
            # Use configured backend API for data updates
            api_url = f"{self.config.effective_open_meteo_url}/v1/forecast"
            
            response = requests.get(api_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Normalize field names from model-specific to generic
            data = self._normalize_field_names(data)
            
            # Clean null values from the data
            if 'hourly' in data:
                cleaned_hourly = {}
                for param, values in data['hourly'].items():
                    if isinstance(values, list):
                        # Replace None/null with a reasonable default or remove
                        cleaned_values = []
                        for value in values:
                            if value is None:
                                cleaned_values.append(None)  # Keep None for proper array indexing
                            else:
                                cleaned_values.append(value)
                        cleaned_hourly[param] = cleaned_values
                    else:
                        cleaned_hourly[param] = values
                data['hourly'] = cleaned_hourly
            
            # Add metadata for mapping interface
            data['city'] = city
            data['coordinates'] = coordinates
            data['latitude'] = latitude
            data['longitude'] = longitude
            
            return data
            
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
    
    def get_status(self) -> Dict:
        """Get current status of data manager"""
        data_info = self.get_data_info()
        
        return {
            'live_fetch_enabled': False,
            'auto_update_enabled': self.config.AUTO_UPDATE_ENABLED,
            'update_interval_hours': self.config.DATA_UPDATE_INTERVAL / 3600,
            'background_thread_running': self.update_thread and self.update_thread.is_alive(),
            'data_info': data_info,
            'needs_update': self.should_update_data(),
            'api_accessible': data_info.get('api_accessible', False),
            'location_count': data_info.get('location_count', 0),
            'file_based': True,
            'file_status': {
                'exists': data_info.get('exists', False),
                'size_mb': data_info.get('file_size_mb', 0),
                'age': data_info.get('data_age', 'Unknown'),
                'valid': data_info.get('is_valid', False)
            }
        }


# Global instance
_data_manager: Optional[WeatherDataManager] = None


def get_data_manager() -> WeatherDataManager:
    """Get global data manager instance"""
    global _data_manager
    if _data_manager is None:
        _data_manager = WeatherDataManager()
    return _data_manager


def start_data_manager():
    """Start the global data manager"""
    manager = get_data_manager()
    manager.start_background_updates()
    return manager


def stop_data_manager():
    """Stop the global data manager"""
    global _data_manager
    if _data_manager:
        _data_manager.stop_background_updates()
        _data_manager = None