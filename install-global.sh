#!/bin/bash

#
# Weather Station v2.0 - Enhanced Global Installation Script
# ===========================================================
# This script provides comprehensive installation and management
# for the Weather Station v2.0 system with improved features:
# - Multi-platform support (Linux, macOS, Windows/WSL)
# - Advanced dependency management
# - Service management integration
# - Configuration validation
# - Health monitoring
# - Automatic updates
# - Backup and restore functionality
#

set -e

# Script version and information
SCRIPT_VERSION="2.1.0"
REPO_URL="https://github.com/RA86-dev/v2weatherstation.git"
DEFAULT_INSTALL_DIR="/opt/weatherstation"
CONFIG_FILE="/etc/weatherstation/config.env"
SERVICE_NAME="weatherstation"
LOG_FILE="/var/log/weatherstation-install.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Enhanced logging functions
log_to_file() {
    local level="$1"
    shift
    echo "$(date '+%Y-%m-%d %H:%M:%S') [$level] $*" >> "$LOG_FILE" 2>/dev/null || true
}

echo_header() {
    echo
    echo -e "${PURPLE}============================================${NC}"
    echo -e "${WHITE} $1 ${NC}"
    echo -e "${PURPLE}============================================${NC}"
    echo
    log_to_file "INFO" "HEADER: $1"
}

echo_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
    log_to_file "INFO" "$1"
}

echo_success() {
    echo -e "${GREEN}✅ $1${NC}"
    log_to_file "SUCCESS" "$1"
}

echo_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    log_to_file "WARNING" "$1"
}

echo_error() {
    echo -e "${RED}❌ $1${NC}"
    log_to_file "ERROR" "$1"
}

echo_step() {
    echo -e "${CYAN}🔧 $1${NC}"
    log_to_file "STEP" "$1"
}

echo_debug() {
    if [ "$DEBUG" = "true" ]; then
        echo -e "${WHITE}🐛 $1${NC}"
        log_to_file "DEBUG" "$1"
    fi
}

# Platform detection
detect_platform() {
    case "$(uname -s)" in
        Linux*)     PLATFORM=Linux;;
        Darwin*)    PLATFORM=Mac;;
        CYGWIN*)    PLATFORM=Cygwin;;
        MINGW*)     PLATFORM=MinGw;;
        MSYS*)      PLATFORM=Msys;;
        *)          PLATFORM="UNKNOWN";;
    esac
    
    # Detect distribution for Linux
    if [ "$PLATFORM" = "Linux" ]; then
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            DISTRO="$ID"
            DISTRO_VERSION="$VERSION_ID"
        elif command -v lsb_release >/dev/null 2>&1; then
            DISTRO=$(lsb_release -si | tr '[:upper:]' '[:lower:]')
            DISTRO_VERSION=$(lsb_release -sr)
        else
            DISTRO="unknown"
            DISTRO_VERSION="unknown"
        fi
    fi
    
    echo_info "Platform detected: $PLATFORM"
    [ "$PLATFORM" = "Linux" ] && echo_info "Distribution: $DISTRO $DISTRO_VERSION"
}

# Enhanced dependency checking
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

check_version() {
    local cmd="$1"
    local min_version="$2"
    local current_version
    
    case "$cmd" in
        docker)
            current_version=$(docker --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
            ;;
        python*)
            current_version=$($cmd --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
            ;;
        git)
            current_version=$(git --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
            ;;
        *)
            return 0
            ;;
    esac
    
    if [ -n "$current_version" ] && [ -n "$min_version" ]; then
        if printf '%s\n%s\n' "$min_version" "$current_version" | sort -V -C; then
            return 0
        else
            return 1
        fi
    fi
    return 0
}

install_docker() {
    case "$PLATFORM" in
        Linux)
            case "$DISTRO" in
                ubuntu|debian)
                    echo_step "Installing Docker on Ubuntu/Debian..."
                    curl -fsSL https://get.docker.com -o get-docker.sh
                    sudo sh get-docker.sh
                    sudo usermod -aG docker "$USER"
                    rm get-docker.sh
                    ;;
                centos|rhel|fedora)
                    echo_step "Installing Docker on CentOS/RHEL/Fedora..."
                    curl -fsSL https://get.docker.com -o get-docker.sh
                    sudo sh get-docker.sh
                    sudo systemctl enable docker
                    sudo systemctl start docker
                    sudo usermod -aG docker "$USER"
                    rm get-docker.sh
                    ;;
                *)
                    echo_warning "Unsupported Linux distribution for automatic Docker installation"
                    echo_info "Please install Docker manually: https://docs.docker.com/engine/install/"
                    return 1
                    ;;
            esac
            ;;
        Mac)
            echo_info "Please install Docker Desktop for Mac: https://docs.docker.com/desktop/install/mac-install/"
            return 1
            ;;
        *)
            echo_warning "Unsupported platform for automatic Docker installation"
            return 1
            ;;
    esac
}

check_requirements() {
    echo_header "Checking System Requirements"
    
    local requirements_met=true
    local auto_install="${AUTO_INSTALL:-false}"
    
    # Check for required tools
    local required_tools=("curl" "wget" "unzip")
    for tool in "${required_tools[@]}"; do
        if command_exists "$tool"; then
            echo_success "$tool is installed"
        else
            echo_error "$tool is not installed"
            if [ "$auto_install" = "true" ] && [ "$PLATFORM" = "Linux" ]; then
                echo_step "Installing $tool..."
                case "$DISTRO" in
                    ubuntu|debian)
                        sudo apt-get update && sudo apt-get install -y "$tool"
                        ;;
                    centos|rhel|fedora)
                        sudo yum install -y "$tool" || sudo dnf install -y "$tool"
                        ;;
                esac
            else
                requirements_met=false
            fi
        fi
    done
    
    # Check Git
    if command_exists git; then
        if check_version git "2.20.0"; then
            echo_success "Git $(git --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+') is installed"
        else
            echo_warning "Git version is old, consider upgrading"
        fi
    else
        echo_error "Git is not installed"
        if [ "$auto_install" = "true" ] && [ "$PLATFORM" = "Linux" ]; then
            echo_step "Installing Git..."
            case "$DISTRO" in
                ubuntu|debian)
                    sudo apt-get update && sudo apt-get install -y git
                    ;;
                centos|rhel|fedora)
                    sudo yum install -y git || sudo dnf install -y git
                    ;;
            esac
        else
            requirements_met=false
        fi
    fi
    
    # Check Docker
    if command_exists docker; then
        if check_version docker "20.10.0"; then
            echo_success "Docker $(docker --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+') is installed"
            
            # Check if Docker is running
            if docker info >/dev/null 2>&1; then
                echo_success "Docker daemon is running"
            else
                echo_error "Docker is installed but daemon is not running"
                echo_step "Attempting to start Docker..."
                case "$PLATFORM" in
                    Linux)
                        sudo systemctl start docker || sudo service docker start
                        ;;
                    Mac)
                        echo_info "Please start Docker Desktop manually"
                        ;;
                esac
            fi
        else
            echo_warning "Docker version is old, consider upgrading"
        fi
    else
        echo_error "Docker is not installed"
        if [ "$auto_install" = "true" ]; then
            install_docker || requirements_met=false
        else
            requirements_met=false
        fi
    fi
    
    # Check Docker Compose
    if command_exists docker-compose || docker compose version >/dev/null 2>&1; then
        echo_success "Docker Compose is available"
    else
        echo_error "Docker Compose is not available"
        if [ "$auto_install" = "true" ]; then
            echo_step "Installing Docker Compose..."
            if [ "$PLATFORM" = "Linux" ]; then
                sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
                sudo chmod +x /usr/local/bin/docker-compose
            fi
        else
            requirements_met=false
        fi
    fi
    
    # Check Python (optional)
    local python_cmd=""
    if command_exists python3; then
        python_cmd="python3"
    elif command_exists python; then
        python_cmd="python"
    fi
    
    if [ -n "$python_cmd" ]; then
        local python_version=$($python_cmd --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
        if [ "$(echo "$python_version" | cut -d. -f1)" -ge 3 ] && [ "$(echo "$python_version" | cut -d. -f2)" -ge 8 ]; then
            echo_success "Python $python_version is installed"
        else
            echo_warning "Python version is too old (need 3.8+), current: $python_version"
        fi
    else
        echo_warning "Python is not installed (optional for Docker setup)"
    fi
    
    # Check disk space
    local available_space=$(df -BG . | tail -1 | awk '{print $4}' | sed 's/G//')
    if [ "$available_space" -gt 5 ]; then
        echo_success "Sufficient disk space available (${available_space}GB)"
    else
        echo_warning "Low disk space (${available_space}GB). At least 5GB recommended."
    fi
    
    # Check memory
    if [ "$PLATFORM" = "Linux" ]; then
        local total_mem=$(free -g | grep '^Mem:' | awk '{print $2}')
        if [ "$total_mem" -gt 1 ]; then
            echo_success "Sufficient memory available (${total_mem}GB)"
        else
            echo_warning "Low memory (${total_mem}GB). At least 2GB recommended."
        fi
    fi
    
    if [ "$requirements_met" = false ]; then
        echo
        echo_error "System requirements not met. Please install missing dependencies."
        echo_info "Tip: Run with --auto-install to automatically install dependencies (Linux only)"
        exit 1
    fi
    
    echo_success "All system requirements are met!"
}

# Enhanced repository management
clone_repository() {
    echo_header "Setting Up Weather Station Repository"
    
    local install_dir="${INSTALL_DIR:-$DEFAULT_INSTALL_DIR}"
    
    # Create installation directory
    if [ ! -d "$(dirname "$install_dir")" ]; then
        echo_step "Creating parent directory..."
        sudo mkdir -p "$(dirname "$install_dir")"
        sudo chown "$USER:$(id -gn)" "$(dirname "$install_dir")"
    fi
    
    if [ -d "$install_dir" ]; then
        echo_warning "Installation directory already exists: $install_dir"
        if [ "$FORCE_REINSTALL" = "true" ]; then
            echo_step "Removing existing installation (--force specified)..."
            sudo rm -rf "$install_dir"
        else
            read -p "Remove existing installation and continue? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                echo_step "Backing up existing installation..."
                sudo mv "$install_dir" "${install_dir}.backup.$(date +%Y%m%d-%H%M%S)"
                echo_success "Backup created"
            else
                echo_info "Installation cancelled"
                exit 0
            fi
        fi
    fi
    
    echo_step "Cloning repository..."
    
    # Clone with specific branch if specified
    local git_cmd="git clone"
    if [ -n "$BRANCH" ]; then
        git_cmd="$git_cmd -b $BRANCH"
    fi
    
    if sudo -u "$USER" $git_cmd "$REPO_URL" "$install_dir"; then
        echo_success "Repository cloned successfully"
    else
        echo_error "Failed to clone repository"
        exit 1
    fi
    
    # Set proper ownership
    sudo chown -R "$USER:$(id -gn)" "$install_dir"
    
    INSTALL_DIR="$install_dir"
}

# Configuration management
create_config() {
    echo_header "Creating Configuration"
    
    local config_dir="/etc/weatherstation"
    sudo mkdir -p "$config_dir"
    
    # Create default configuration
    cat > /tmp/weatherstation.env << EOF
# Weather Station v2.0 Configuration
# Generated on $(date)

# Application Settings
WS_HOST=${WS_HOST:-0.0.0.0}
WS_PORT=${WS_PORT:-8110}
WS_DEBUG=${WS_DEBUG:-false}

# Data Source Settings
WS_LIVE_DATA_ENABLED=${WS_LIVE_DATA_ENABLED:-true}
WS_USE_SELF_HOSTED=${WS_USE_SELF_HOSTED:-true}
WS_OPEN_METEO_URL=${WS_OPEN_METEO_URL:-http://localhost:8080/v1}

# Security Settings
WS_API_KEY=${WS_API_KEY:-$(openssl rand -hex 32 2>/dev/null || dd if=/dev/urandom bs=32 count=1 2>/dev/null | base64 | tr -d '\\n=')}

# Logging
WS_LOG_LEVEL=${WS_LOG_LEVEL:-INFO}

# CORS Settings
WS_CORS_ORIGINS=${WS_CORS_ORIGINS:-["*"]}

# Installation Metadata
INSTALL_DATE=$(date -Iseconds)
INSTALL_VERSION=$SCRIPT_VERSION
INSTALL_DIR=$INSTALL_DIR
EOF
    
    sudo mv /tmp/weatherstation.env "$CONFIG_FILE"
    sudo chmod 644 "$CONFIG_FILE"
    
    echo_success "Configuration created at $CONFIG_FILE"
}

# Service management
create_systemd_service() {
    echo_header "Creating System Service"
    
    if [ "$PLATFORM" != "Linux" ]; then
        echo_warning "System service creation is only supported on Linux"
        return 0
    fi
    
    cat > /tmp/weatherstation.service << EOF
[Unit]
Description=Weather Station v2.0
Documentation=https://github.com/RA86-dev/v2weatherstation
After=docker.service
Wants=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$CONFIG_FILE
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
ExecReload=/usr/bin/docker-compose restart
User=$USER
Group=$(id -gn)

[Install]
WantedBy=multi-user.target
EOF
    
    sudo mv /tmp/weatherstation.service "/etc/systemd/system/${SERVICE_NAME}.service"
    sudo systemctl daemon-reload
    sudo systemctl enable "$SERVICE_NAME"
    
    echo_success "System service created and enabled"
}

# Application setup
setup_application() {
    echo_header "Setting Up Weather Station Application"
    
    cd "$INSTALL_DIR"
    
    # Make scripts executable
    echo_step "Setting up permissions..."
    find . -name "*.sh" -type f -exec chmod +x {} \;
    
    # Create necessary directories
    echo_step "Creating data directories..."
    mkdir -p data/weather data/backups data/logs
    
    # Install Python dependencies if Python is available
    if command_exists python3 && [ -f requirements.txt ]; then
        echo_step "Installing Python dependencies..."
        python3 -m pip install --user -r requirements.txt 2>/dev/null || echo_warning "Failed to install Python dependencies (Docker installation will work)"
    fi
    
    # Build Docker images
    echo_step "Building Docker containers..."
    if [ -f docker-compose.yml ]; then
        docker-compose build --no-cache
        echo_success "Docker containers built successfully"
    else
        echo_warning "docker-compose.yml not found, skipping container build"
    fi
    
    echo_success "Application setup completed"
}

# Health monitoring
health_check() {
    echo_step "Performing health checks..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -o /dev/null -w "%{http_code}" http://localhost:8110/health | grep -q "200"; then
            echo_success "Weather Station is responding (attempt $attempt/$max_attempts)"
            return 0
        fi
        
        echo_debug "Health check attempt $attempt/$max_attempts failed, waiting..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo_warning "Health check failed after $max_attempts attempts"
    echo_info "Service may still be starting up. Check logs: docker-compose logs"
    return 1
}

# Start services
start_services() {
    echo_header "Starting Weather Station Services"
    
    cd "$INSTALL_DIR"
    
    if [ "$USE_SYSTEMD" = "true" ] && [ "$PLATFORM" = "Linux" ]; then
        echo_step "Starting via systemd service..."
        sudo systemctl start "$SERVICE_NAME"
        sleep 5
        if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
            echo_success "Service started successfully"
        else
            echo_error "Failed to start service via systemd"
            echo_info "Falling back to direct docker-compose..."
            docker-compose up -d
        fi
    else
        echo_step "Starting via docker-compose..."
        docker-compose up -d
    fi
    
    # Wait for services to be ready
    sleep 10
    health_check
}

# Backup functionality
create_backup() {
    echo_step "Creating backup..."
    
    local backup_dir="/var/backups/weatherstation"
    local backup_file="weatherstation-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
    
    sudo mkdir -p "$backup_dir"
    
    tar -czf "/tmp/$backup_file" \
        -C "$(dirname "$INSTALL_DIR")" "$(basename "$INSTALL_DIR")" \
        -C /etc weatherstation/ \
        2>/dev/null || true
    
    sudo mv "/tmp/$backup_file" "$backup_dir/"
    echo_success "Backup created: $backup_dir/$backup_file"
}

# Monitoring setup
setup_monitoring() {
    echo_step "Setting up monitoring..."
    
    # Create monitoring script
    cat > "$INSTALL_DIR/monitor.sh" << 'EOF'
#!/bin/bash

check_services() {
    echo "=== Weather Station Health Check ===" 
    echo "Time: $(date)"
    echo
    
    # Check Docker containers
    echo "Docker containers:"
    docker-compose ps
    echo
    
    # Check API health
    echo "API Health:"
    curl -s http://localhost:8110/health | jq . 2>/dev/null || echo "Health endpoint not responding"
    echo
    
    # Check disk usage
    echo "Disk usage:"
    df -h "$PWD"
    echo
    
    # Check logs for errors
    echo "Recent errors:"
    docker-compose logs --tail=10 2>&1 | grep -i error || echo "No recent errors"
}

check_services
EOF
    
    chmod +x "$INSTALL_DIR/monitor.sh"
    
    # Setup log rotation
    if [ "$PLATFORM" = "Linux" ]; then
        cat > /tmp/weatherstation.logrotate << EOF
/var/log/weatherstation/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    copytruncate
}
EOF
        sudo mv /tmp/weatherstation.logrotate /etc/logrotate.d/weatherstation
    fi
    
    echo_success "Monitoring setup completed"
}

# Final information display
display_final_info() {
    echo_header "Installation Complete!"
    
    echo_success "Weather Station v2.0 has been successfully installed!"
    echo
    echo -e "${CYAN}📍 Installation Details:${NC}"
    echo "   • Location: $INSTALL_DIR"
    echo "   • Configuration: $CONFIG_FILE"
    echo "   • Platform: $PLATFORM"
    echo "   • Installation Date: $(date)"
    echo
    echo -e "${CYAN}🌐 Access Information:${NC}"
    echo "   • Weather Station: http://localhost:8110"
    echo "   • Open-Meteo API: http://localhost:8080"
    echo "   • Health Check: http://localhost:8110/health"
    echo "   • API Status: http://localhost:8110/api/status"
    echo
    echo -e "${CYAN}🛠️  Management Commands:${NC}"
    if [ "$USE_SYSTEMD" = "true" ] && [ "$PLATFORM" = "Linux" ]; then
        echo "   • Start service:      sudo systemctl start $SERVICE_NAME"
        echo "   • Stop service:       sudo systemctl stop $SERVICE_NAME"
        echo "   • Restart service:    sudo systemctl restart $SERVICE_NAME"
        echo "   • Service status:     sudo systemctl status $SERVICE_NAME"
        echo "   • View logs:          sudo journalctl -u $SERVICE_NAME -f"
    fi
    echo "   • Direct start:       cd $INSTALL_DIR && docker-compose up -d"
    echo "   • Direct stop:        cd $INSTALL_DIR && docker-compose down"
    echo "   • View logs:          cd $INSTALL_DIR && docker-compose logs -f"
    echo "   • Health monitor:     cd $INSTALL_DIR && ./monitor.sh"
    echo
    echo -e "${CYAN}📊 API Endpoints:${NC}"
    echo "   • All weather data:   GET http://localhost:8110/api/data/weather"
    echo "   • Locations list:     GET http://localhost:8110/api/data/locations"
    echo "   • City weather:       GET http://localhost:8110/api/data/live/{city}"
    echo "   • Current conditions: GET http://localhost:8110/api/data/current/{city}"
    echo
    echo -e "${CYAN}🔧 Configuration:${NC}"
    echo "   • Config file:        $CONFIG_FILE"
    echo "   • Edit config:        sudo nano $CONFIG_FILE"
    echo "   • Restart after config changes"
    echo
    echo -e "${CYAN}🔄 Updates & Maintenance:${NC}"
    echo "   • Update software:    cd $INSTALL_DIR && git pull && docker-compose build --no-cache"
    echo "   • Create backup:      $0 --backup"
    echo "   • Reinstall:          $0 --force"
    echo
    echo -e "${CYAN}📋 Next Steps:${NC}"
    echo "   1. Visit http://localhost:8110 to access the weather dashboard"
    echo "   2. Test API endpoints listed above"
    echo "   3. Review configuration in $CONFIG_FILE"
    echo "   4. Set up monitoring and backups as needed"
    echo
    echo -e "${GREEN}🎉 Weather Station v2.0 is ready to use!${NC}"
    echo
}

# Usage information
show_usage() {
    cat << EOF
Weather Station v2.0 - Enhanced Global Installation Script v$SCRIPT_VERSION

USAGE:
    $0 [OPTIONS]

OPTIONS:
    -h, --help              Show this help message
    -d, --dir DIR           Installation directory (default: $DEFAULT_INSTALL_DIR)
    -b, --branch BRANCH     Git branch to install (default: main)
    --auto-install          Automatically install dependencies (Linux only)
    --force                 Force reinstallation (remove existing)
    --no-start             Setup only, don't start services
    --no-systemd           Skip systemd service creation
    --backup               Create backup of existing installation
    --debug                Enable debug output
    --config-only          Only create/update configuration
    --uninstall            Remove Weather Station installation

ENVIRONMENT VARIABLES:
    WS_HOST                 Server host (default: 0.0.0.0)
    WS_PORT                 Server port (default: 8110)
    WS_DEBUG                Debug mode (default: false)
    WS_LIVE_DATA_ENABLED    Enable live data (default: true)
    WS_API_KEY              API key (auto-generated if not set)

EXAMPLES:
    # Standard installation
    $0

    # Custom directory with auto-install
    $0 --dir /home/user/weather --auto-install

    # Development installation
    $0 --branch develop --debug --no-systemd

    # Create backup
    $0 --backup

    # Force reinstall
    $0 --force

    # Update configuration only
    $0 --config-only

FEATURES:
    • Multi-platform support (Linux, macOS, Windows/WSL)
    • Automatic dependency installation
    • System service integration
    • Health monitoring
    • Backup and restore
    • Configuration management
    • Comprehensive logging

For more information, visit: https://github.com/RA86-dev/v2weatherstation
EOF
}

# Backup function
backup_installation() {
    echo_header "Creating Backup"
    
    if [ ! -d "$INSTALL_DIR" ]; then
        echo_error "Installation directory not found: $INSTALL_DIR"
        exit 1
    fi
    
    create_backup
    echo_success "Backup completed successfully"
}

# Uninstall function
uninstall_weatherstation() {
    echo_header "Uninstalling Weather Station"
    
    echo_warning "This will completely remove Weather Station from your system"
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo_info "Uninstall cancelled"
        exit 0
    fi
    
    # Create backup before uninstall
    if [ -d "$INSTALL_DIR" ]; then
        echo_step "Creating backup before uninstall..."
        create_backup
    fi
    
    # Stop and remove systemd service
    if [ "$PLATFORM" = "Linux" ] && systemctl is-enabled "$SERVICE_NAME" >/dev/null 2>&1; then
        echo_step "Stopping and removing systemd service..."
        sudo systemctl stop "$SERVICE_NAME" || true
        sudo systemctl disable "$SERVICE_NAME" || true
        sudo rm -f "/etc/systemd/system/${SERVICE_NAME}.service"
        sudo systemctl daemon-reload
    fi
    
    # Stop Docker containers
    if [ -d "$INSTALL_DIR" ]; then
        echo_step "Stopping Docker containers..."
        cd "$INSTALL_DIR"
        docker-compose down --volumes --remove-orphans || true
    fi
    
    # Remove installation directory
    if [ -d "$INSTALL_DIR" ]; then
        echo_step "Removing installation directory..."
        sudo rm -rf "$INSTALL_DIR"
    fi
    
    # Remove configuration
    if [ -f "$CONFIG_FILE" ]; then
        echo_step "Removing configuration..."
        sudo rm -f "$CONFIG_FILE"
        sudo rmdir /etc/weatherstation 2>/dev/null || true
    fi
    
    # Remove log rotation
    if [ -f /etc/logrotate.d/weatherstation ]; then
        sudo rm -f /etc/logrotate.d/weatherstation
    fi
    
    echo_success "Weather Station has been uninstalled successfully"
}

# Main installation function
main() {
    local skip_start=false
    local config_only=false
    
    # Initialize log file
    sudo mkdir -p "$(dirname "$LOG_FILE")"
    sudo touch "$LOG_FILE"
    sudo chmod 666 "$LOG_FILE"
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -d|--dir)
                INSTALL_DIR="$2"
                shift 2
                ;;
            -b|--branch)
                BRANCH="$2"
                shift 2
                ;;
            --auto-install)
                AUTO_INSTALL=true
                shift
                ;;
            --force)
                FORCE_REINSTALL=true
                shift
                ;;
            --no-start)
                skip_start=true
                shift
                ;;
            --no-systemd)
                USE_SYSTEMD=false
                shift
                ;;
            --backup)
                backup_installation
                exit 0
                ;;
            --debug)
                DEBUG=true
                shift
                ;;
            --config-only)
                config_only=true
                shift
                ;;
            --uninstall)
                uninstall_weatherstation
                exit 0
                ;;
            *)
                echo_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
    
    # Set defaults
    INSTALL_DIR="${INSTALL_DIR:-$DEFAULT_INSTALL_DIR}"
    USE_SYSTEMD="${USE_SYSTEMD:-true}"
    
    echo_header "Weather Station v2.0 - Enhanced Global Installation v$SCRIPT_VERSION"
    echo_info "Repository: $REPO_URL"
    echo_info "Install directory: $INSTALL_DIR"
    echo_info "Platform: $(detect_platform)"
    
    if [ "$config_only" = "true" ]; then
        create_config
        echo_success "Configuration updated successfully"
        exit 0
    fi
    
    # Confirm installation
    if [ "$FORCE_REINSTALL" != "true" ]; then
        echo
        read -p "Continue with installation? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo_info "Installation cancelled"
            exit 0
        fi
    fi
    
    # Run installation steps
    detect_platform
    check_requirements
    clone_repository
    create_config
    setup_application
    
    if [ "$USE_SYSTEMD" = "true" ] && [ "$PLATFORM" = "Linux" ]; then
        create_systemd_service
    fi
    
    setup_monitoring
    
    if [ "$skip_start" = false ]; then
        start_services
    else
        echo_warning "Skipping service startup (--no-start specified)"
        echo_info "To start services manually:"
        echo_info "  cd $INSTALL_DIR && docker-compose up -d"
        if [ "$USE_SYSTEMD" = "true" ] && [ "$PLATFORM" = "Linux" ]; then
            echo_info "  sudo systemctl start $SERVICE_NAME"
        fi
    fi
    
    display_final_info
}

# Error handling
trap 'echo; echo_error "Installation interrupted"; exit 1' INT TERM

# Ensure running as user (not root)
if [ "$EUID" -eq 0 ] && [ "$ALLOW_ROOT" != "true" ]; then
    echo_error "Please run this script as a regular user, not as root"
    echo_info "The script will use sudo when necessary"
    echo_info "To override: ALLOW_ROOT=true $0"
    exit 1
fi

# Run main function
main "$@"