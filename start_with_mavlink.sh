#!/bin/bash
echo "Starting Drone Controller with MAVLink Parser..."
echo ""

# Activate virtual environment
source venv/bin/activate

# Start MAVLink parser in background
echo "Starting MAVLink parser on port 14550..."
python src/python/mavlink_parser.py 14550 14551 &
PARSER_PID=$!

# Wait a moment for parser to start
sleep 3

# Start Electron app
echo "Starting Electron application..."
npm start

# Cleanup function
cleanup() {
    echo "Stopping MAVLink parser..."
    kill $PARSER_PID 2>/dev/null
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

echo "Application started. Check for windows to open."
