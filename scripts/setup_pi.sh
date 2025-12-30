#!/bin/bash
# MoniToni Raspberry Pi Setup Script
# Run this script on the Raspberry Pi to set up the environment

set -e  # Exit on error

echo "======================================"
echo "MoniToni Raspberry Pi Setup"
echo "======================================"
echo ""

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ]; then
    echo "Warning: This doesn't appear to be a Raspberry Pi"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Update system
echo "Step 1: Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install system dependencies
echo ""
echo "Step 2: Installing system dependencies..."
sudo apt-get install -y \
    python3-pip \
    python3-dev \
    python3-venv \
    git \
    libsdl2-dev \
    libsdl2-image-dev \
    libsdl2-mixer-dev \
    libsdl2-ttf-dev \
    libportmidi-dev \
    libswscale-dev \
    libavformat-dev \
    libavcodec-dev \
    zlib1g-dev \
    libgstreamer1.0-dev \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    libmtdev-dev \
    xclip \
    xsel

# Install Python packages
echo ""
echo "Step 3: Installing Python packages..."
cd ~/MoniToniVending
pip3 install -r requirements.txt

# Create config directory if it doesn't exist
echo ""
echo "Step 4: Setting up configuration..."
mkdir -p config

# Create local config from default if it doesn't exist
if [ ! -f config/local.yaml ]; then
    cp config/default.yaml config/local.yaml
    echo "Created config/local.yaml from default"
    echo "Please edit config/local.yaml with your hardware settings"
else
    echo "config/local.yaml already exists, skipping"
fi

# Create data directory for database
echo ""
echo "Step 5: Creating data directories..."
mkdir -p data
mkdir -p logs

# Set up systemd service (optional)
echo ""
read -p "Do you want to set up MoniToni as a systemd service for auto-start? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cat > /tmp/monitoni.service << EOF
[Unit]
Description=MoniToni Vending Machine System
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME/MoniToniVending
ExecStart=/usr/bin/python3 -m monitoni.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    sudo mv /tmp/monitoni.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable monitoni.service

    echo "Systemd service installed. You can control it with:"
    echo "  sudo systemctl start monitoni    # Start the service"
    echo "  sudo systemctl stop monitoni     # Stop the service"
    echo "  sudo systemctl status monitoni   # Check status"
    echo "  sudo systemctl restart monitoni  # Restart the service"
fi

# Configure touchscreen (Waveshare 7.9")
echo ""
read -p "Do you want to configure the Waveshare 7.9\" touchscreen? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Adding touchscreen configuration to /boot/config.txt..."

    # Backup config.txt
    sudo cp /boot/config.txt /boot/config.txt.backup

    # Add HDMI configuration for portrait mode
    sudo tee -a /boot/config.txt > /dev/null << EOF

# Waveshare 7.9" Display Configuration (400x1280)
hdmi_group=2
hdmi_mode=87
hdmi_cvt=400 1280 60 6 0 0 0
display_rotate=1
EOF

    echo "Touchscreen configured. You may need to reboot for changes to take effect."
fi

echo ""
echo "======================================"
echo "Setup Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Edit config/local.yaml with your hardware settings"
echo "2. Test with: python3 -m monitoni.main --mock"
echo "3. Run on hardware: python3 -m monitoni.main"
echo ""
echo "For remote development from your MacBook:"
echo "1. Note this Pi's IP address: $(hostname -I | awk '{print $1}')"
echo "2. Set up SSH key authentication (recommended)"
echo "3. Use VS Code Remote SSH or git pull workflow"
echo ""
