#!/bin/bash

# RPi Local Chat - Setup Script
# This script helps set up the chat application on your Raspberry Pi

set -e

echo "=================================="
echo "RPi Local Chat - Setup Script"
echo "=================================="
echo ""

# Check if Python3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed!"
    echo "Please run: sudo apt install python3 python3-pip python3-venv"
    exit 1
fi

echo "✓ Python3 found: $(python3 --version)"

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed!"
    echo "Please run: sudo apt install python3-pip"
    exit 1
fi

echo "✓ pip3 found"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

# Initialize database
echo ""
echo "Initializing database..."
python3 database.py

# Initialize PIN (only if .chat_pin doesn't exist)
if [ ! -f ".chat_pin" ]; then
    echo ""
    echo "Generating access PIN..."
    python3 -c "import auth; pin = auth.set_pin(); print(f'\n🔐 Your PIN is: {pin}\n\nSave this PIN - you will need it to access the chat!\n')"
else
    echo ""
    echo "✓ PIN already exists (stored in .chat_pin)"
fi

# Get IP address
IP_ADDR=$(hostname -I | awk '{print $1}')

echo ""
echo "=================================="
echo "✓ Setup Complete!"
echo "=================================="
echo ""
echo "To start the chat server, run:"
echo ""
echo "  source venv/bin/activate"
echo "  python3 server.py"
echo ""
echo "Then access the chat at:"
echo "  http://${IP_ADDR}:5000"
echo "  http://localhost:5000 (from the Pi)"
echo ""
echo "=================================="
