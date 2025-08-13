# Weather Station  - Self-Hosted Live Data Edition

![Weather Station](https://img.shields.io/badge/Weather-Station-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11+-green?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-red?style=for-the-badge&logo=fastapi)
![Docker](https://img.shields.io/badge/Docker-Ready-blue?style=for-the-badge&logo=docker)

A modern, self-hosted weather data visualization platform with real-time data fetching from Open-Meteo API. Designed for schools and organizations to provide unified weather information access.

## 🌟 Features

### ✨ New in v3
- **🔴 Live Data Fetching**: Real-time weather data from self-hosted Open-Meteo API
- **🚀 Instant Startup**: No more 4+ minute initial data downloads
- **🌍 240+ Locations**: All US cities available immediately
- **📊 Multiple Data Sources**: Historical, current, and forecast data
- **🐳 Dockerized**: One-command deployment with Docker Compose
- **⚡ Fast Response**: Sub-second data retrieval
- **🔧 Configurable**: Environment-based configuration

### 🎯 Core Features
- Beautiful, responsive web interface
- Interactive weather maps and charts
- Weather statistics and comparisons
- Multiple visualization modes
- RESTful API for data access
- Health monitoring and status endpoints
- CORS support for web applications

## 🚀 Quick Start
### Docker (recommended):
To install Weather Station on Docker, run the following commands:
```
git clone https://github.com/RA86-dev/v2weatherstation
cd v2weatherstation
docker build -t v2weatherstation:latest .
docker run -p 8110:8110 v2weatherstation:latest

```
# weatherstation-new
# weatherstation-new
