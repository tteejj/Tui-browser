#!/bin/bash

# RPi Local Chat - Void Linux Setup Script
# This script helps set up the chat application on Void Linux (x86/x86_64/ARM)

set -e

echo "=================================="
echo "RPi Local Chat - Void Linux Setup"
echo "=================================="
echo ""

# Check if we're on Void Linux
if [ ! -f "/etc/os-release" ]; then
    echo "⚠️  Warning: Cannot detect OS. This script is designed for Void Linux."
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
elif ! grep -q "void" /etc/os-release; then
    echo "⚠️  Warning: This doesn't appear to be Void Linux."
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "✓ Detected Void Linux"
echo ""

# Check if script is run as root
if [ "$EUID" -eq 0 ]; then
    echo "⚠️  Please do not run this script as root."
    echo "You will be prompted for sudo password when needed."
    exit 1
fi

# Check for xbps-install
if ! command -v xbps-install &> /dev/null; then
    echo "❌ xbps-install not found! This script requires Void Linux package manager."
    exit 1
fi

echo "Checking system dependencies..."
echo ""

# Check and install Python3
if ! command -v python3 &> /dev/null; then
    echo "Installing Python3..."
    sudo xbps-install -Sy python3
else
    echo "✓ Python3 found: $(python3 --version)"
fi

# Check and install pip
if ! command -v pip3 &> /dev/null; then
    echo "Installing pip..."
    sudo xbps-install -Sy python3-pip
else
    echo "✓ pip3 found"
fi

# Install virtualenv if not present
if ! python3 -m venv --help &> /dev/null 2>&1; then
    echo "Installing python3-venv..."
    sudo xbps-install -Sy python3-virtualenv
else
    echo "✓ python3-venv found"
fi

# Install image processing dependencies
echo ""
echo "Installing image processing libraries..."
PACKAGES_TO_INSTALL=""

# Check for libjpeg
if ! xbps-query libjpeg-turbo-devel &> /dev/null; then
    PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL libjpeg-turbo-devel"
fi

# Check for zlib
if ! xbps-query zlib-devel &> /dev/null; then
    PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL zlib-devel"
fi

if [ -n "$PACKAGES_TO_INSTALL" ]; then
    echo "Installing: $PACKAGES_TO_INSTALL"
    sudo xbps-install -Sy $PACKAGES_TO_INSTALL
else
    echo "✓ Image libraries already installed"
fi

echo ""
echo "=================================="
echo "Setting up Python environment..."
echo "=================================="
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
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
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Initialize database
echo ""
echo "=================================="
echo "Initializing application..."
echo "=================================="
echo ""
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
IP_ADDR=$(hostname -I 2>/dev/null | awk '{print $1}')
if [ -z "$IP_ADDR" ]; then
    # Try alternative method for Void
    IP_ADDR=$(ip addr show | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | cut -d/ -f1 | head -n1)
fi

if [ -z "$IP_ADDR" ]; then
    IP_ADDR="<your-ip-address>"
fi

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
echo "Or simply run:"
echo "  ./run.sh"
echo ""
echo "Then access the chat at:"
echo "  http://${IP_ADDR}:5000"
echo "  http://localhost:5000 (from this machine)"
echo ""
echo "=================================="
echo ""
echo "Optional: Run as system service"
echo "To have the chat start on boot, see README.md"
echo "for runit service configuration (Void Linux uses runit)."
echo "=================================="
