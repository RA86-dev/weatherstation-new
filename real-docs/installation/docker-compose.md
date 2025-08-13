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
cp real-docs/installation/docker-compose.yml.example docker-compose.yml
echo "Please edit the yaml that was just put in the main directory."
```
Please modify the Docker compose settings to your requested settings.