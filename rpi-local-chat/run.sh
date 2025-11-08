#!/bin/bash

# RPi Local Chat - Run Script
# Quick script to start the chat server

set -e

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run ./setup.sh first"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Get IP address
IP_ADDR=$(hostname -I | awk '{print $1}')

echo ""
echo "=================================="
echo "🚀 Starting RPi Local Chat..."
echo "=================================="
echo ""
echo "Access the chat at:"
echo "  http://${IP_ADDR}:5000"
echo "  http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=================================="
echo ""

# Run server
python3 server.py
