#!/bin/bash

# Define log and PID file paths.
LOG_FILE="build.log"
PID_FILE="build.pid"

# Function to print log messages with timestamps.
log() {
  echo "[$(date +"%Y-%m-%d %H:%M:%S")] $1"
}

log "Starting build script..."

# If there's a previous build running, kill it.
if [ -f "$PID_FILE" ]; then
    old_pid=$(cat "$PID_FILE")
    if ps -p "$old_pid" > /dev/null; then
        log "Killing existing build process with PID $old_pid"
        kill "$old_pid"
        sleep 1  # give it a moment to shut down
    else
        log "No process found with PID $old_pid. Continuing..."
    fi
fi

# Clean up previous extracted APK.
log "Removing extracted_apk directory..."
rm -rf ./extracted_apk

# Start the new build process and redirect output to the log file.
log "Starting new build process..."
python3 ./android_ssl_pinning.py ./bin/app-release.apk ./bin/Untitled1 key 'asdasdasd' 'asdasdasd' www.chatgpt.com Vekg+x3F9nqs4TpPrlWVhiozepFYg4USuM+nj69ySg4= >> "$LOG_FILE" 2>&1 &
new_pid=$!
echo $new_pid > "$PID_FILE"
log "Build process started with PID $new_pid, logging to $LOG_FILE"

# Tail the log file for live output.
log "Tailing log file. Press Ctrl+C to exit."
tail -f "$LOG_FILE"
