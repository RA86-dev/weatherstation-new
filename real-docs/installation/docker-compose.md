# Install Weather Station via Docker Compose
To install Weather Station via Docker compose, please follow the following guide:
## Prerequisites:
- Docker Compose + Docker
- Git
## Installation:
Installation can be completed by copying the following code and modifying `docker-compose.yml` once created.
```
git clone https://github.com/RA86-dev/weatherstation-new
cd weatherstation-new 
docker build -t weatherstation:latest .
echo "Please edit the yaml that was just put in the main directory."
```
Please modify the Docker compose settings to your requested settings.
After that, run `docker-compose up -d` or `docker compose up -d` and then wait for atleast 2 minutes for the data to load.
