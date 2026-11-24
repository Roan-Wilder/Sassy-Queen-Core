#!/bin/bash

# SassyQueenCore Listener Service
# This script runs and maintains the SassyQueenCore system
# It will restart the service if it crashes

# Directory where SassyQueenCore is installed
SASSY_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CORE_SCRIPT="${SASSY_DIR}/sassy_shadow_core.py"
LOG_FILE="${SASSY_DIR}/sassy_startup.log"
HEARTBEAT_FILE="${SASSY_DIR}/heartbeat.log"
PID_FILE="${SASSY_DIR}/.sassy.pid"
MAX_RESTARTS=5
RESTART_DELAY=10

# Function to log messages
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Make sure the Python script is executable
chmod +x "$CORE_SCRIPT"

# Check if dependencies are installed
check_dependencies() {
  log "Checking dependencies..."
  
  # Create a virtual environment if it doesn't exist
  if [ ! -d "${SASSY_DIR}/venv" ]; then
    log "Creating virtual environment..."
    python3 -m venv "${SASSY_DIR}/venv"
    source "${SASSY_DIR}/venv/bin/activate"
    pip install pyttsx3 SpeechRecognition pyaudio RPi.GPIO
  else
    source "${SASSY_DIR}/venv/bin/activate"
  fi
  
  # Check specific dependencies
  if ! python -c "import pyttsx3" &>/dev/null; then
    log "Installing pyttsx3..."
    pip install pyttsx3
  fi
  
  if ! python -c "import speech_recognition" &>/dev/null; then
    log "Installing SpeechRecognition..."
    pip install SpeechRecognition
  fi
  
  log "Dependencies checked."
}

# Function to start the SassyQueenCore
start_sassy() {
  log "Starting SassyQueenCore..."
  
  # Check if already running
  if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null; then
      log "SassyQueenCore is already running with PID: $PID"
      return 0
    else
      log "Stale PID file found, removing..."
      rm -f "$PID_FILE"
    fi
  fi
  
  # Start the Python script
  cd "$SASSY_DIR"
  nohup python "$CORE_SCRIPT" > "${SASSY_DIR}/sassy_output.log" 2>&1 &
  PID=$!
  echo $PID > "$PID_FILE"
  
  log "SassyQueenCore started with PID: $PID"
}

# Function to stop SassyQueenCore
stop_sassy() {
  log "Stopping SassyQueenCore..."
  
  if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null; then
      log "Sending SIGTERM to PID: $PID"
      kill -15 "$PID"
      sleep 5
      
      # Force kill if still running
      if ps -p "$PID" > /dev/null; then
        log "Process did not stop gracefully, sending SIGKILL..."
        kill -9 "$PID"
      fi
    else
      log "No running process found with PID: $PID"
    fi
    
    rm -f "$PID_FILE"
  else
    log "No PID file found, checking for Python process..."
    PIDS=$(pgrep -f "python.*sassy_shadow_core.py")
    if [ -n "$PIDS" ]; then
      log "Found running processes: $PIDS"
      for P in $PIDS; do
        kill -15 "$P"
        log "Killed process with PID: $P"
      done
    else
      log "No running SassyQueenCore processes found."
    fi
  fi
  
  log "SassyQueenCore stopped."
}

# Function to check if SassyQueenCore is running
check_heartbeat() {
  if [ ! -f "$HEARTBEAT_FILE" ]; then
    log "Heartbeat file not found, service may not be running properly."
    return 1
  fi
  
  LAST_HEARTBEAT=$(cat "$HEARTBEAT_FILE" | head -1)
  CURRENT_TIME=$(date +%s)
  
  # Check if the heartbeat is older than 2 minutes
  if (( CURRENT_TIME - LAST_HEARTBEAT > 120 )); then
    log "Heartbeat is stale (last: $LAST_HEARTBEAT, now: $CURRENT_TIME), restarting service."
    return 1
  fi
  
  return 0
}

# Function to restart SassyQueenCore
restart_sassy() {
  log "Restarting SassyQueenCore..."
  stop_sassy
  sleep 2
  start_sassy
}

# Main monitor function
monitor_sassy() {
  log "Starting SassyQueenCore monitor..."
  
  restart_count=0
  
  while true; do
    # Check if the service is running and healthy
    if ! check_heartbeat; then
      if (( restart_count < MAX_RESTARTS )); then
        log "Restarting SassyQueenCore (attempt $((restart_count+1))/$MAX_RESTARTS)..."
        restart_sassy
        restart_count=$((restart_count+1))
      else
        log "Reached maximum restart attempts ($MAX_RESTARTS). Please check the logs."
        exit 1
      fi
    else
      # Reset restart counter if heartbeat is good
      restart_count=0
    fi
    
    # Wait before next check
    sleep 60
  done
}

# Parse command line arguments
case "$1" in
  start)
    check_dependencies
    start_sassy
    ;;
  stop)
    stop_sassy
    ;;
  restart)
    restart_sassy
    ;;
  monitor)
    check_dependencies
    start_sassy
    monitor_sassy
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|monitor}"
    exit 1
    ;;
esac

exit 0 