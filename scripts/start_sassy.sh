#!/bin/bash

# SassyQueenCore Startup Script

# Set the base directory
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BASE_DIR"

# Create necessary directories if they don't exist
mkdir -p logs
mkdir -p learning_data
mkdir -p config

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Check Python version
python3 --version

# Install requirements if needed
if [ ! -f ".requirements_installed" ]; then
    echo "Installing requirements..."
    pip install -r requirements.txt
    touch .requirements_installed
fi

# Check if GUI mode is requested
if [ "$1" == "--gui" ]; then
    echo "Starting SassyQueenCore in GUI mode..."
    python3 scripts/sassy_gui.py
else
    echo "Starting SassyQueenCore in console mode..."
    python3 scripts/system_integration.py
fi

# Handle shutdown
trap 'echo "Shutting down SassyQueenCore..."; exit 0' SIGINT SIGTERM 