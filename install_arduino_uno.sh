#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

export PLATFORMIO_CORE_DIR="PlatformIO/install"

# --- Clean up any broken symlinks from previous installs ---
if [ -L /dev/ttyACM0 ]; then
  echo "Removing stale /dev/ttyACM0 symlink..."
  sudo rm -f /dev/ttyACM0
  echo "Please unplug and replug the Arduino, then re-run this script."
  exit 0
fi

PIO_DIR="PlatformIO/install/"
if ! [ -d "$PIO_DIR" ]; then
  python3 PlatformIO/platformio-core-installer/get-platformio.py
fi

./PlatformIO/install/penv/bin/platformio run -e uno
./PlatformIO/install/penv/bin/platformio run -e uno -t upload

# --- Analog logging setup ---
echo ""
echo "Setting up analog logging support..."

# Install udev rule (creates /dev/ttyJARVIS symlink for the Arduino)
RULES_SRC="$SCRIPT_DIR/99-jarvis-trigger.rules"
RULES_DST="/etc/udev/rules.d/99-jarvis-trigger.rules"
if [ -f "$RULES_SRC" ]; then
  echo "Installing udev rule..."
  sudo cp "$RULES_SRC" "$RULES_DST"
  sudo udevadm control --reload-rules
  sudo udevadm trigger --subsystem-match=tty
  echo "  Installed $RULES_DST"
fi

# Install serial swap helper
SWAP_SRC="$SCRIPT_DIR/jarvis_serial_swap.sh"
SWAP_DST="/usr/local/bin/jarvis_serial_swap"
if [ -f "$SWAP_SRC" ]; then
  echo "Installing serial swap helper..."
  sudo cp "$SWAP_SRC" "$SWAP_DST"
  sudo chmod 755 "$SWAP_DST"
  echo "  Installed $SWAP_DST"
fi

# Add sudoers entry so the proxy can swap the symlink without a password
SUDOERS_FILE="/etc/sudoers.d/jarvis-trigger"
CURRENT_USER="$(whoami)"
echo "Configuring passwordless sudo for serial swap..."
echo "$CURRENT_USER ALL=(root) NOPASSWD: $SWAP_DST" | sudo tee "$SUDOERS_FILE" > /dev/null
sudo chmod 440 "$SUDOERS_FILE"
echo "  Configured $SUDOERS_FILE"

# Install Python dependencies for the analog logger
echo "Installing Python dependencies for analog logger..."
pip3 install pyserial cobs 2>/dev/null || pip install pyserial cobs 2>/dev/null || true

echo ""
echo "Done! Unplug and replug the Arduino for the udev rule to take effect."
echo "See README.md for analog logging instructions."
