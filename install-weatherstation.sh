#!/bin/bash

#
# Weather Station v2.0 - Complete Installation Script
# ===================================================
# This script clones the RA86-dev/v2weatherstation repository
# and sets up a fully functional weather station with self-hosted Open-Meteo API
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
echo_header() {
    echo
    echo -e "${PURPLE}============================================${NC}"
    echo -e "${PURPLE} $1 ${NC}"
    echo -e "${PURPLE}============================================${NC}"
    echo
}

echo_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

echo_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

echo_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

echo_error() {
    echo -e "${RED}❌ $1${NC}"
}

echo_step() {
    echo -e "${CYAN}🔧 $1${NC}"
}

# Configuration
REPO_URL="https://github.com/RA86-dev/v2weatherstation.git"
INSTALL_DIR="v2weatherstation"
PROJECT_DIR="$INSTALL_DIR/WeatherStation/weather_station"

# Helper function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check system requirements
check_requirements() {
    echo_header "Checking System Requirements"
    
    local requirements_met=true
    
    # Check for Git
    if command_exists git; then
        echo_success "Git is installed"
    else
        echo_error "Git is not installed. Please install Git first."
        echo_info "Visit: https://git-scm.com/downloads"
        requirements_met=false
    fi
    
    # Check for Docker
    if command_exists docker; then
        echo_success "Docker is installed"
        
        # Check if Docker is running
        if docker info >/dev/null 2>&1; then
            echo_success "Docker is running"
        else
            echo_error "Docker is installed but not running. Please start Docker first."
            requirements_met=false
        fi
    else
        echo_error "Docker is not installed. Please install Docker first."
        echo_info "Visit: https://docs.docker.com/get-docker/"
        requirements_met=false
    fi
    
    # Check for Docker Compose
    if command_exists docker-compose || docker compose version >/dev/null 2>&1; then
        echo_success "Docker Compose is available"
    else
        echo_error "Docker Compose is not installed. Please install Docker Compose first."
        echo_info "Visit: https://docs.docker.com/compose/install/"
        requirements_met=false
    fi
    
    # Check for Python (optional, for manual setup)
    if command_exists python3; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        echo_success "Python $PYTHON_VERSION is installed"
    elif command_exists python; then
        PYTHON_VERSION=$(python --version | cut -d' ' -f2)
        echo_success "Python $PYTHON_VERSION is installed"
    else
        echo_warning "Python is not installed (optional for Docker setup)"
        echo_info "Python is only required if you want to run the application outside Docker"
    fi
    
    if [ "$requirements_met" = false ]; then
        echo
        echo_error "System requirements not met. Please install the missing dependencies and run this script again."
        exit 1
    fi
    
    echo_success "All system requirements are met!"
}

# Function to clone repository
clone_repository() {
    echo_header "Cloning Weather Station Repository"
    
    if [ -d "$INSTALL_DIR" ]; then
        echo_warning "Directory '$INSTALL_DIR' already exists."
        read -p "Remove existing directory and re-clone? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo_step "Removing existing directory..."
            rm -rf "$INSTALL_DIR"
            echo_success "Existing directory removed"
        else
            echo_info "Using existing directory"
            if [ ! -d "$PROJECT_DIR" ]; then
                echo_error "Existing directory is incomplete. Please remove it manually and run this script again."
                exit 1
            fi
            return 0
        fi
    fi
    
    echo_step "Cloning repository from $REPO_URL..."
    
    if git clone "$REPO_URL" "$INSTALL_DIR"; then
        echo_success "Repository cloned successfully"
    else
        echo_error "Failed to clone repository. Please check your internet connection and try again."
        exit 1
    fi
    
    # Verify the expected directory structure exists
    if [ ! -d "$PROJECT_DIR" ]; then
        echo_error "Repository structure is unexpected. Expected path '$PROJECT_DIR' not found."
        exit 1
    fi
    
    echo_success "Repository structure verified"
}

# Function to set up the application
setup_application() {
    echo_header "Setting Up Weather Station"
    
    cd "$PROJECT_DIR"
    
    echo_step "Current directory: $(pwd)"
    echo_step "Verifying project files..."
    
    # Check for essential files
    local essential_files=("docker-compose.yml" "start.sh" "requirements.txt" "index.py")
    for file in "${essential_files[@]}"; do
        if [ -f "$file" ]; then
            echo_success "Found $file"
        else
            echo_error "Missing essential file: $file"
            exit 1
        fi
    done
    
    # Make scripts executable
    echo_step "Making scripts executable..."
    chmod +x start.sh
    chmod +x init-weather-data.sh
    chmod +x setup-auto-update.sh
    chmod +x update-openmeteo-data.sh
    [ -f "item.sh" ] && chmod +x item.sh
    [ -f "update-data.sh" ] && chmod +x update-data.sh
    echo_success "Scripts are now executable"
    
    # Create data directory
    echo_step "Creating data directories..."
    mkdir -p data/open-meteo
    echo_success "Data directories created"
}

# Function to start the application
start_application() {
    echo_header "Starting Weather Station Services"
    
    cd "$PROJECT_DIR"
    
    echo_step "Building and starting Docker containers..."
    echo_info "This may take a few minutes for the first run..."
    
    # Use the existing start.sh script
    if ./start.sh; then
        echo_success "Weather Station started successfully!"
    else
        echo_error "Failed to start Weather Station services."
        echo_info "You can try starting manually with: docker-compose up -d"
        exit 1
    fi
}

# Function to display final information
display_final_info() {
    echo_header "Installation Complete!"
    
    echo_success "Weather Station v2.0 has been installed and started successfully!"
    echo
    echo -e "${CYAN}📍 Installation Location:${NC}"
    echo "   $(pwd)"
    echo
    echo -e "${CYAN}🌐 Access URLs:${NC}"
    echo "   • Weather Station: http://localhost:8110"
    echo "   • Open-Meteo API:  http://localhost:8080"
    echo
    echo -e "${CYAN}🔧 Health Checks:${NC}"
    echo "   • curl http://localhost:8110/health"
    echo "   • curl http://localhost:8110/api/status"
    echo
    echo -e "${CYAN}📊 Available Endpoints:${NC}"
    echo "   • Live weather data: http://localhost:8110/api/data/weather"
    echo "   • All locations:     http://localhost:8110/api/data/locations"
    echo "   • Specific city:     http://localhost:8110/api/data/live/{city}"
    echo
    echo -e "${CYAN}🛠️  Management Commands:${NC}"
    echo "   • View logs:         docker-compose logs -f"
    echo "   • Stop services:     docker-compose down"
    echo "   • Restart services:  docker-compose restart"
    echo "   • Update data:       ./init-weather-data.sh"
    echo "   • Setup auto-update: ./setup-auto-update.sh"
    echo
    echo -e "${CYAN}📁 Directory Structure:${NC}"
    echo "   • Main app:          $(pwd)"
    echo "   • Configuration:     $(pwd)/config.py"
    echo "   • Static files:      $(pwd)/assets/"
    echo "   • Data storage:      $(pwd)/data/"
    echo
    echo -e "${CYAN}🔄 Next Steps:${NC}"
    echo "   1. Visit http://localhost:8110 to access the weather station"
    echo "   2. Optionally run ./setup-auto-update.sh to enable automatic data updates"
    echo "   3. Explore the API endpoints listed above"
    echo
    echo -e "${GREEN}🎉 Enjoy your new Weather Station v2.0!${NC}"
    echo
}

# Function to show usage
show_usage() {
    echo "Weather Station v2.0 - Complete Installation Script"
    echo
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -d, --dir      Specify installation directory (default: v2weatherstation)"
    echo "  --no-start     Clone and setup but don't start services"
    echo
    echo "This script will:"
    echo "  1. Check system requirements (Git, Docker, Docker Compose)"
    echo "  2. Clone the RA86-dev/v2weatherstation repository"
    echo "  3. Set up the weather station application"
    echo "  4. Start Docker services (unless --no-start is specified)"
    echo
    echo "Examples:"
    echo "  $0                    # Standard installation"
    echo "  $0 -d my-weather     # Install to 'my-weather' directory"
    echo "  $0 --no-start        # Setup only, don't start services"
}

# Main function
main() {
    local skip_start=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -d|--dir)
                INSTALL_DIR="$2"
                PROJECT_DIR="$INSTALL_DIR/WeatherStation/weather_station"
                shift 2
                ;;
            --no-start)
                skip_start=true
                shift
                ;;
            *)
                echo_error "Unknown option: $1"
                echo "Use -h or --help for usage information."
                exit 1
                ;;
        esac
    done
    
    echo_header "Weather Station v2.0 - Complete Installation"
    echo_info "This script will install the complete Weather Station v2.0 system"
    echo_info "Repository: $REPO_URL"
    echo_info "Install directory: $INSTALL_DIR"
    echo
    
    # Confirm installation
    read -p "Continue with installation? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo_info "Installation cancelled."
        exit 0
    fi
    
    # Run installation steps
    check_requirements
    clone_repository
    setup_application
    
    if [ "$skip_start" = false ]; then
        start_application
    else
        echo_warning "Skipping service startup (--no-start specified)"
        echo_info "To start services manually, run:"
        echo_info "  cd $PROJECT_DIR && ./start.sh"
    fi
    
    # Change back to the project directory for final info
    cd "$PROJECT_DIR"
    display_final_info
}

# Trap to handle script interruption
trap 'echo; echo_error "Installation interrupted by user"; exit 1' INT

# Run main function with all arguments
main "$@"