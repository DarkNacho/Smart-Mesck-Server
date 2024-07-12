#!/bin/bash

# Define log file path
LOG_FILE="log.txt"

# Find the process ID (PID) of sensor2.py and kill it
PID=$(pgrep -f sensor2.py)
if [ ! -z "$PID" ]; then
    echo "Killing existing server.py process with PID: $PID"
    kill $PID
fi

# Wait a moment to ensure the process has been terminated
sleep 1

# Activate the virtual environment
source venv/bin/activate

# Run sensor2.py in the background with nohup and redirect stdout and stderr to the log file
nohup python server.py > "$LOG_FILE" 2>&1 &

echo "server.py has been started and is logging to $LOG_FILE"

