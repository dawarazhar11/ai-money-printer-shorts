#!/bin/bash
# Script to download and install fonts needed for captions

echo "Creating fonts directory..."
mkdir -p fonts

# Download common fonts
echo "Downloading Arial and Arial Bold..."
curl -L "https://github.com/matomo-org/travis-scripts/raw/master/fonts/Arial.ttf" -o fonts/Arial.ttf
curl -L "https://github.com/matomo-org/travis-scripts/raw/master/fonts/Arial%20Bold.ttf" -o fonts/Arial-Bold.ttf

echo "Downloading Impact..."
curl -L "https://github.com/matomo-org/travis-scripts/raw/master/fonts/Impact.ttf" -o fonts/Impact.ttf

echo "Downloading Georgia..."
curl -L "https://github.com/matomo-org/travis-scripts/raw/master/fonts/Georgia.ttf" -o fonts/Georgia.ttf

echo "Downloading Courier New..."
curl -L "https://github.com/matomo-org/travis-scripts/raw/master/fonts/Courier%20New.ttf" -o fonts/Courier-New.ttf

# Create system font directories if they don't exist
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    echo "Installing fonts for macOS..."
    mkdir -p ~/Library/Fonts
    cp fonts/* ~/Library/Fonts/
    echo "Fonts installed to ~/Library/Fonts/"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    echo "Installing fonts for Linux..."
    mkdir -p ~/.fonts
    cp fonts/* ~/.fonts/
    fc-cache -f -v
    echo "Fonts installed to ~/.fonts/"
elif [[ "$OSTYPE" == "msys"* || "$OSTYPE" == "win32" ]]; then
    # Windows with Git Bash or similar
    echo "For Windows, please manually copy the fonts to C:\\Windows\\Fonts"
    echo "The fonts are located in the 'fonts' directory"
fi

echo "Font installation completed!" 