#!/bin/bash
echo "Starting Drone Controller Application..."
source venv/bin/activate
npm start &
echo "Application started. Check for the Electron window."
