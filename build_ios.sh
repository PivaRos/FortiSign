#!/bin/bash

# Define log and PID file paths.
LOG_FILE="build_ios.log"
PID_FILE="build_ios.pid"

# Function to print log messages with timestamps.
log() {
  echo "[$(date +"%Y-%m-%d %H:%M:%S")] $1"
}

log "Starting iOS build script..."

# If there's a previous build running, kill it.
if [ -f "$PID_FILE" ]; then
    old_pid=$(cat "$PID_FILE")
    if ps -p "$old_pid" > /dev/null; then
        log "Killing existing build process with PID $old_pid"
        kill "$old_pid"
        sleep 1  # Give it a moment to shut down.
    else
        log "No process found with PID $old_pid. Continuing..."
    fi
fi

# Clean up previous working directory (where the IPA is extracted).
log "Removing ipa_work directory..."
rm -rf ./ipa_work

# Start the new build process and redirect output to the log file.
# Update the paths and parameters below as needed:
#   1. IPA file path (e.g., ./ios_bin/MyApp.ipa)
#   2. DYLIB path (e.g., ./ios_bin/MyPinning.dylib)
#   3. Certificate name (e.g., "iPhone Distribution: Your Company")
#   4. Entitlements plist path (e.g., ./ios_bin/entitlements.plist)
log "Starting new iOS build process..."
python3 ./ios_ssl_pinning.py ./ios_bin/MyApp.ipa ./ios_bin/MyPinning.dylib "iPhone Distribution: Your Company" "./ios_bin/entitlements.plist" >> "$LOG_FILE" 2>&1 &
new_pid=$!
echo $new_pid > "$PID_FILE"
log "Build process started with PID $new_pid, logging to $LOG_FILE"

# Tail the log file for live output.
log "Tailing log file. Press Ctrl+C to exit."
tail -f "$LOG_FILE"
