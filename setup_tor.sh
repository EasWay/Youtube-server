#!/bin/bash
# Tor setup script for Render deployment

echo "Setting up Tor..."

# Install Tor
apt-get update
apt-get install -y tor

# Create Tor configuration
mkdir -p /etc/tor
cat > /etc/tor/torrc << EOF
# Tor configuration for YouTube server
SocksPort 9050
ControlPort 9051
CookieAuthentication 1
DataDirectory /tmp/tor
Log notice stdout
EOF

# Start Tor in the background
echo "Starting Tor service..."
tor -f /etc/tor/torrc &

# Wait for Tor to establish connection
echo "Waiting for Tor to connect..."
sleep 10

# Check if Tor is running
if pgrep -x "tor" > /dev/null; then
    echo "Tor is running successfully on port 9050"
else
    echo "Warning: Tor may not have started properly"
fi

echo "Tor setup complete!"
