#!/bin/bash

# SassyQueenCore Installation Script
# This script sets up the SassyQueenCore system and its dependencies

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOG_FILE="$SCRIPT_DIR/install_log.txt"

# Function to log messages
log() {
  echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

# Function to log success messages
success() {
  echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

# Function to log error messages
error() {
  echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

# Function to log warning messages
warning() {
  echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

# Check if running as root
check_root() {
  if [ "$EUID" -eq 0 ]; then
    error "Please do not run this script as root or with sudo."
    exit 1
  fi
}

# Check if OS is Linux
check_os() {
  if [ "$(uname)" != "Linux" ]; then
    warning "This script is designed for Linux. Some features may not work on $(uname)."
  else
    success "Detected Linux OS: $(lsb_release -d 2>/dev/null | cut -f2- || cat /etc/os-release | grep PRETTY_NAME | cut -d '=' -f2- | tr -d '\"')"
  fi
}

# Install required system packages
install_system_packages() {
  log "Installing required system packages..."
  
  # Detect package manager
  if command -v apt-get &> /dev/null; then
    # Debian/Ubuntu
    log "Detected apt package manager"
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip python3-venv portaudio19-dev python3-pyaudio git
    success "System packages installed successfully"
  elif command -v dnf &> /dev/null; then
    # Fedora
    log "Detected dnf package manager"
    sudo dnf install -y python3 python3-pip python3-virtualenv portaudio-devel git
    success "System packages installed successfully"
  elif command -v pacman &> /dev/null; then
    # Arch
    log "Detected pacman package manager"
    sudo pacman -Sy --noconfirm python python-pip python-virtualenv portaudio git
    success "System packages installed successfully"
  else
    warning "Could not detect package manager. Please install Python 3, pip, and portaudio manually."
  fi
}

# Create and setup virtual environment
setup_venv() {
  log "Setting up Python virtual environment..."
  
  # Create virtual environment if it doesn't exist
  if [ ! -d "$SCRIPT_DIR/venv" ]; then
    python3 -m venv "$SCRIPT_DIR/venv"
    success "Virtual environment created"
  else
    warning "Virtual environment already exists, skipping creation"
  fi
  
  # Activate virtual environment
  source "$SCRIPT_DIR/venv/bin/activate"
  
  # Upgrade pip
  pip install --upgrade pip
  
  # Install Python dependencies
  log "Installing Python dependencies..."
  pip install -r "$SCRIPT_DIR/requirements.txt"
  
  success "Python dependencies installed successfully"
}

# Make scripts executable
make_executable() {
  log "Making scripts executable..."
  
  chmod +x "$SCRIPT_DIR/sassy_shadow_core.py"
  chmod +x "$SCRIPT_DIR/sassy_listener.sh"
  
  success "Scripts are now executable"
}

# Setup systemd service
setup_service() {
  log "Setting up systemd service..."
  
  # Get current username
  USER=$(whoami)
  
  # Replace placeholder in service file
  sed -i "s/USER_TO_REPLACE/$USER/g" "$SCRIPT_DIR/sassyqueencore.service"
  
  # Ask for permission to install service
  read -p "Do you want to install SassyQueenCore as a system service? (y/n) " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo cp "$SCRIPT_DIR/sassyqueencore.service" /etc/systemd/system/
    sudo systemctl daemon-reload
    
    read -p "Do you want to enable and start the service now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
      sudo systemctl enable sassyqueencore
      sudo systemctl start sassyqueencore
      success "Service installed, enabled and started"
    else
      success "Service installed but not started. You can start it later with: sudo systemctl start sassyqueencore"
    fi
  else
    log "Skipping service installation. You can run the system manually with: ./sassy_listener.sh start"
  fi
}

# Create required directories
create_directories() {
  log "Creating required directories..."
  
  mkdir -p "$SCRIPT_DIR/plugins"
  mkdir -p "$SCRIPT_DIR/backups"
  
  success "Directories created"
}

# Main installation function
install_sassyqueencore() {
  echo -e "${BLUE}=================================================${NC}"
  echo -e "${GREEN}         SassyQueenCore Installation           ${NC}"
  echo -e "${BLUE}=================================================${NC}"
  echo
  
  # Check prerequisites
  check_root
  check_os
  
  # Install components
  install_system_packages
  create_directories
  setup_venv
  make_executable
  setup_service
  
  echo
  echo -e "${BLUE}=================================================${NC}"
  echo -e "${GREEN}     SassyQueenCore Installation Complete      ${NC}"
  echo -e "${BLUE}=================================================${NC}"
  echo
  echo -e "To start SassyQueenCore manually: ${YELLOW}./sassy_listener.sh start${NC}"
  echo -e "To stop SassyQueenCore manually: ${YELLOW}./sassy_listener.sh stop${NC}"
  echo -e "To view logs: ${YELLOW}cat sassy_log.txt${NC}"
  echo
  echo -e "For more information, see the ${YELLOW}README.md${NC} file."
  echo
}

# Run the installation
install_sassyqueencore 