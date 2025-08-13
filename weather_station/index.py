"""
Weather Station FastAPI Server v2.0
A modern weather data visualization platform with enhanced features
"""

import time
import os
import logging
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_config
from .data_manager import get_data_manager, start_data_manager, stop_data_manager
from .live_data_manager import get_live_data_manager

# Setup logging
config = get_config()
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT
)
logger = logging.getLogger(__name__)


class WeatherStationApp:
    """Enhanced Weather Station application with configuration support"""
    
    def __init__(self):
        self.config = get_config()
        self.logs = []
        self.data_manager = get_data_manager()
        self.live_data_manager = get_live_data_manager()
        
        # Initialize FastAPI app with configuration
        self.app = FastAPI(
            title=self.config.APP_NAME,
            description=self.config.APP_DESCRIPTION,
            version=self.config.APP_VERSION,
            debug=self.config.DEBUG
        )
        
        # Setup lifecycle events
        self._setup_events()
        
        # Setup middleware
        self._setup_middleware()
        
        # Setup routes
        self._setup_routes()
        
        logger.info(f"{self.config.APP_NAME} v{self.config.APP_VERSION} initialized successfully")
        if self.config.DEBUG:
            logger.debug(f"Configuration: {self.config.to_dict()}")
            logger.info(f"🔑 Admin API Key: {self.config.API_KEY}")
        else:
            logger.info(f"🔑 Admin API Key generated (32 chars): {self.config.API_KEY[:8]}...")
    
    def _setup_events(self):
        """Setup FastAPI lifecycle events"""
        
        @self.app.on_event("startup")
        async def startup_event():
            """Application startup"""
            logger.info("Starting Weather Station application")
            
            if self.config.LIVE_DATA_ENABLED:
                logger.info("Live data mode enabled - using self-hosted Open-Meteo API")
                # Check API accessibility
                api_status = self.live_data_manager.get_api_status()
                if api_status['accessible']:
                    logger.info(f"✓ Self-hosted API accessible ({api_status['response_time_ms']}ms)")
                else:
                    logger.warning(f"⚠ Self-hosted API not accessible: {api_status.get('error', 'Unknown error')}")
            else:
                logger.info("File-based data mode enabled")
                # Start data manager for automatic updates
                start_data_manager()
                logger.info("Data manager started")
                
                # Check if initial data update is needed
                if self.data_manager.should_update_data():
                    logger.info("Scheduling initial data update")
                    # Don't block startup, let background thread handle it
        
        @self.app.on_event("shutdown")
        async def shutdown_event():
            """Application shutdown"""
            logger.info("Shutting down Weather Station application")
            stop_data_manager()
            logger.info("Data manager stopped")
    
    def _setup_middleware(self):
        """Setup FastAPI middleware"""
        # CORS middleware
        if self.config.CORS_ORIGINS:
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=self.config.CORS_ORIGINS,
                allow_credentials=True,
                allow_methods=["GET", "POST"],
                allow_headers=["*"],
            )
        
        # Static files
        assets_path = Path(self.config.ASSETS_DIR)
        if assets_path.exists():
            self.app.mount("/assets", StaticFiles(directory=str(assets_path)), name="assets")
    
    def generate_log(self, request: Request, page: str) -> dict:
        """Generate access log entry with enhanced information"""
        log_entry = {
            'timestamp': time.asctime(),
            'iso_timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'client_host': request.client.host if request.client else 'unknown',
            'client_port': request.client.port if request.client else 0,
            'page': page,
            'method': request.method,
            'user_agent': request.headers.get('user-agent', 'Unknown'),
            'referer': request.headers.get('referer', ''),
            'query_params': dict(request.query_params) if request.query_params else {}
        }
        
        # Log to file if debug mode
        if self.config.DEBUG:
            logger.debug(f"Access log: {log_entry}")
        
        return log_entry
    
    def _get_file_path(self, filename: str) -> Path:
        """Get safe file path within assets directory"""
        assets_path = Path(self.config.ASSETS_DIR)
        file_path = assets_path / filename
        
        # Security check: ensure file is within assets directory
        try:
            file_path.resolve().relative_to(assets_path.resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return file_path
    
    def _setup_routes(self):
        """Setup all application routes"""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            data_status = self.data_manager.get_status()
            return JSONResponse({
                "status": "healthy",
                "version": self.config.APP_VERSION,
                "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                "data_status": data_status
            })
        
        @self.app.get("/api/data/status")
        async def data_status():
            """Get data manager status"""
            status = self.data_manager.get_status()
            # Add additional debug information
            status['debug_info'] = {
                'cache_exists': self.data_manager._data_cache is not None,
                'cache_size': len(self.data_manager._data_cache) if self.data_manager._data_cache else 0,
                'cache_timestamp': self.data_manager._cache_timestamp,
                'last_update_check': self.data_manager._last_update_check
            }
            return JSONResponse(status)
        
        @self.app.post("/api/data/force-update")
        async def force_data_update(request: Request):
            """Manually trigger a data update (requires API key)"""
            try:
                # Check API key
                api_key = request.headers.get('X-API-Key') or request.headers.get('Authorization', '').replace('Bearer ', '')
                
                if not api_key or api_key != self.config.API_KEY:
                    return JSONResponse({
                        "success": False,
                        "error": "Unauthorized",
                        "message": "Valid API key required for manual updates",
                        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                    }, status_code=401)
                
                logger.info("Manual data update requested with valid API key")
                success = self.data_manager.force_update()
                
                if success:
                    return JSONResponse({
                        "success": True,
                        "message": "Data update completed successfully",
                        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                    })
                else:
                    return JSONResponse({
                        "success": False,
                        "message": "Data update failed - check logs for details",
                        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                    }, status_code=500)
                    
            except Exception as e:
                logger.error(f"Error in manual update: {e}")
                return JSONResponse({
                    "success": False,
                    "message": f"Update failed: {str(e)}",
                    "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                }, status_code=500)
        
        
        @self.app.get("/api/data/weather")
        async def get_weather_data(limit: int = 300):
            """Get live weather data for multiple locations"""
            start_time = time.time()
            
            # Validate and sanitize limit
            limit = max(1, min(limit, 300))  # Between 1 and 300
            
            try:
                if self.config.LIVE_DATA_ENABLED:
                    # Get live data for limited number of cities
                    locations = self.live_data_manager.load_locations()
                    if not locations:
                        return JSONResponse({
                            "error": "No locations available",
                            "message": "Location data could not be loaded. Check geolocations.json file.",
                            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                            "request_id": f"req_{int(start_time)}"
                        }, status_code=404)
                    
                    # Limit to prevent timeout issues
                    limited_locations = dict(list(locations.items())[:limit])
                    
                    logger.info(f"Fetching live data for {len(limited_locations)} cities (limit: {limit})")
                    data = self.live_data_manager._fetch_multiple_cities_data(limited_locations, limit)
                    
                    if not data:
                        api_status = self.live_data_manager.get_api_status()
                        error_msg = "Failed to fetch live weather data"
                        if not api_status.get('accessible', False):
                            error_msg += f" - API not accessible: {api_status.get('error', 'Unknown error')}"
                        
                        return JSONResponse({
                            "error": "Weather data not available",
                            "message": error_msg,
                            "api_status": api_status,
                            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                            "request_id": f"req_{int(start_time)}"
                        }, status_code=503)
                    
                    fetch_time = time.time() - start_time
                    logger.info(f"Successfully fetched {len(data)}/{len(limited_locations)} cities in {fetch_time:.2f}s")
                    
                    return JSONResponse({
                        "data": data,
                        "locations": list(data.keys()),
                        "total_available": len(locations),
                        "requested": len(limited_locations),
                        "fetched": len(data),
                        "live_data": True,
                        "fetch_time_seconds": round(fetch_time, 2),
                        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                        "request_id": f"req_{int(start_time)}"
                    })
                else:
                    # Fallback to file-based data
                    data = self.data_manager.load_weather_data()
                    if data is None:
                        file_status = self.data_manager.get_data_info()
                        return JSONResponse({
                            "error": "Weather data not available",
                            "message": "Data file may be outdated, missing, or failed to load",
                            "file_status": file_status,
                            "suggestion": "Try updating data file or enabling live data mode",
                            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                            "request_id": f"req_{int(start_time)}"
                        }, status_code=404)
                    
                    # Limit file data as well
                    if limit < len(data):
                        data = dict(list(data.items())[:limit])
                    
                    return JSONResponse({
                        "data": data,
                        "locations": list(data.keys()),
                        "total": len(data),
                        "live_data": False,
                        "source": "file_cache",
                        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                        "request_id": f"req_{int(start_time)}"
                    })
                    
            except Exception as e:
                fetch_time = time.time() - start_time
                logger.error(f"Error getting weather data after {fetch_time:.2f}s: {e}")
                return JSONResponse({
                    "error": "Internal server error",
                    "message": f"Failed to process weather data request: {str(e)[:100]}",
                    "fetch_time_seconds": round(fetch_time, 2),
                    "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                    "request_id": f"req_{int(start_time)}"
                }, status_code=500)
        
        @self.app.get("/api/data/live/{city}")
        async def get_live_city_weather(city: str):
            """Get live weather data for a specific city"""
            try:
                if not self.config.LIVE_DATA_ENABLED:
                    return JSONResponse({
                        "error": "Live data not enabled",
                        "message": "Live data fetching is disabled in configuration",
                        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                    }, status_code=503)
                
                data = self.live_data_manager.get_weather_data(city)
                if data is None:
                    return JSONResponse({
                        "error": "City not found or data unavailable",
                        "message": f"Could not fetch weather data for {city}",
                        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                    }, status_code=404)
                
                return JSONResponse({
                    "city": city,
                    "data": data,
                    "live_data": True,
                    "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                })
                
            except Exception as e:
                logger.error(f"Error getting live weather data for {city}: {e}")
                return JSONResponse({
                    "error": "Internal server error",
                    "message": str(e),
                    "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                }, status_code=500)
        
        @self.app.get("/api/data/current/{city}")
        async def get_current_conditions(city: str):
            """Get current weather conditions for a specific city"""
            try:
                if not self.config.LIVE_DATA_ENABLED:
                    return JSONResponse({
                        "error": "Live data not enabled",
                        "message": "Live data fetching is disabled in configuration",
                        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                    }, status_code=503)
                
                data = self.live_data_manager.get_current_conditions(city)
                if data is None:
                    return JSONResponse({
                        "error": "City not found or data unavailable",
                        "message": f"Could not fetch current conditions for {city}",
                        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                    }, status_code=404)
                
                return JSONResponse({
                    "city": city,
                    "current_conditions": data,
                    "live_data": True,
                    "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                })
                
            except Exception as e:
                logger.error(f"Error getting current conditions for {city}: {e}")
                return JSONResponse({
                    "error": "Internal server error",
                    "message": str(e),
                    "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                }, status_code=500)
        
        @self.app.get("/api/data/locations")
        async def get_available_locations():
            """Get list of available locations"""
            try:
                locations = self.live_data_manager.load_locations()
                return JSONResponse({
                    "locations": list(locations.keys()),
                    "coordinates": locations,
                    "total": len(locations),
                    "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                })
            except Exception as e:
                logger.error(f"Error getting locations: {e}")
                return JSONResponse({
                    "error": "Internal server error",
                    "message": str(e),
                    "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                }, status_code=500)
        
        @self.app.get("/api/status")
        async def get_api_status():
            """Get API and self-hosted Open-Meteo status"""
            try:
                api_status = self.live_data_manager.get_api_status()
                data_status = self.data_manager.get_status()
                
                return JSONResponse({
                    "api_status": api_status,
                    "data_manager_status": data_status,
                    "live_data_enabled": self.config.LIVE_DATA_ENABLED,
                    "self_hosted": self.config.USE_SELF_HOSTED,
                    "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                })
            except Exception as e:
                logger.error(f"Error getting API status: {e}")
                return JSONResponse({
                    "error": "Internal server error",
                    "message": str(e),
                    "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                }, status_code=500)
        
        @self.app.get("/config")
        async def get_app_config():
            """Get application configuration (public settings only)"""
            public_config = {
                "app_name": self.config.APP_NAME,
                "app_version": self.config.APP_VERSION,
                "api_url": self.config.effective_open_meteo_url,
                "self_hosted": self.config.USE_SELF_HOSTED
            }
            return JSONResponse(public_config)
        
        @self.app.get("/admin/api-key")
        async def get_api_key():
            """Get the API key for administrative operations (local access only)"""
            if not self.config.DEBUG:
                raise HTTPException(status_code=404, detail="Not found")
            
            return JSONResponse({
                "api_key": self.config.API_KEY,
                "usage": "Use with X-API-Key header or Authorization: Bearer <key>",
                "example": f"curl -X POST http://localhost:8110/api/data/force-update -H 'X-API-Key: {self.config.API_KEY}'"
            })
        
        @self.app.get("/logs")
        async def get_logs(limit: int = 100):
            """Get recent access logs (debug mode only)"""
            if not self.config.DEBUG:
                raise HTTPException(status_code=404, detail="Not found")
            
            return JSONResponse({
                "logs": self.logs[-limit:],
                "total": len(self.logs)
            })
        
        @self.app.get("/assets/{filename:path}")
        async def serve_assets(filename: str):
            """Serve static assets with enhanced security"""
            try:
                file_path = self._get_file_path(filename)
                
                if file_path.exists() and file_path.is_file():
                    return FileResponse(file_path)
                else:
                    raise HTTPException(status_code=404, detail="File not found")
                    
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error serving asset {filename}: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        @self.app.get("/")
        async def home(request: Request):
            """Main dashboard page"""
            self.logs.append(self.generate_log(request, "home"))
            file_path = self._get_file_path("index.html")
            
            if not file_path.exists():
                raise HTTPException(status_code=404, detail="Dashboard not found")
            
            return FileResponse(file_path)
        
        @self.app.get("/comparison")
        async def comparison_page(request: Request):
            """Weather data comparison page"""
            self.logs.append(self.generate_log(request, "comparison"))
            file_path = self._get_file_path("comparison_quick.html")
            
            if not file_path.exists():
                raise HTTPException(status_code=404, detail="Comparison page not found")
            
            return FileResponse(file_path)
        
        @self.app.get("/intmap")
        async def interactive_map_page(request: Request):
            """Interactive pressure map page"""
            self.logs.append(self.generate_log(request, "interactive_map"))
            file_path = self._get_file_path("interactive_pressure_map.html")
            
            if not file_path.exists():
                raise HTTPException(status_code=404, detail="Interactive map not found")
            
            return FileResponse(file_path)
        
        @self.app.get("/weatherstat")
        async def weather_statistics_page(request: Request):
            """Weather statistics page"""
            self.logs.append(self.generate_log(request, "weather_statistics"))
            file_path = self._get_file_path("weather_statistics.html")
            
            if not file_path.exists():
                raise HTTPException(status_code=404, detail="Statistics page not found")
            
            return FileResponse(file_path)
        
        @self.app.get("/license")
        async def license_page(request: Request):
            """License information page"""
            self.logs.append(self.generate_log(request, "license"))
            file_path = self._get_file_path("LICENSE.txt")
            
            if not file_path.exists():
                raise HTTPException(status_code=404, detail="License file not found")
            
            return FileResponse(file_path)
        
        @self.app.get("/favicon.ico")
        async def favicon():
            """Serve favicon"""
            file_path = self._get_file_path("favicon.ico")
            
            if not file_path.exists():
                raise HTTPException(status_code=404, detail="Favicon not found")
            
            return FileResponse(file_path)


def create_app() -> FastAPI:
    """Factory function to create the FastAPI app"""
    weather_app = WeatherStationApp()
    return weather_app.app


# Initialize the application
app = create_app()
def main():
    import uvicorn
    
    # Validate configuration before starting
    if not config.validate():
        logger.error("Invalid configuration. Exiting.")
        exit(1)
    
    logger.info(f"Starting {config.APP_NAME} v{config.APP_VERSION}")
    logger.info(f"Server will run on {config.HOST}:{config.PORT}")
    logger.info(f"Debug mode: {config.DEBUG}")
    logger.info(f"Open-Meteo API: {config.effective_open_meteo_url}")
    
    # Run the server
    uvicorn.run(
        "WeatherStation.weather_station.index:app",
        host=config.HOST,
        port=config.PORT,
        log_level=config.LOG_LEVEL.lower(),
        reload=config.DEBUG,
        access_log=True
    )

if __name__ == "__main__":
    main()