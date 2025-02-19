#!/bin/bash
# Run watchman in the foreground and set log level to debug.
# This will output Watchman’s logs directly to the terminal.
watchman --foreground &
WATCHMAN_PID=$!

# Set the log level to debug for more detailed output.
watchman log-level debug

# Set up a watch on the current directory.
watchman watch .

# Set up the trigger for changes in android_ssl_pinning.py to run build.sh.
watchman -- trigger . ios_ssl_pinning_trigger 'ios_ssl_pinning.py' -- ./build_ios.sh

# Optional: Tail the Watchman log file if you need extra detail.
# Replace /path/to/watchman.log with the actual path to your Watchman log file.
# tail -f /path/to/watchman.log

# Wait for the foreground process to end (if desired)
wait $WATCHMAN_PID
