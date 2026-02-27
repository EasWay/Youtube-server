#!/bin/bash
# Test Docker build and Tor setup locally before deploying to Render

echo "=========================================="
echo "Local Docker + Tor Test"
echo "=========================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    echo "Install Docker from: https://www.docker.com/get-started"
    exit 1
fi

echo "✓ Docker is installed"

# Build the Docker image
echo ""
echo "Building Docker image..."
docker build -t youtube-server-test .

if [ $? -ne 0 ]; then
    echo "❌ Docker build failed"
    exit 1
fi

echo "✓ Docker image built successfully"

# Run the container
echo ""
echo "Starting container..."
docker run -d -p 8080:8080 --name youtube-server-test youtube-server-test

if [ $? -ne 0 ]; then
    echo "❌ Failed to start container"
    exit 1
fi

echo "✓ Container started"

# Wait for services to start
echo ""
echo "Waiting for Tor and server to start (30 seconds)..."
sleep 30

# Test the server
echo ""
echo "Testing server endpoints..."

# Test 1: Ping
echo "1. Testing /ping..."
curl -s http://localhost:8080/ping | grep -q "pong"
if [ $? -eq 0 ]; then
    echo "   ✓ Server is responding"
else
    echo "   ❌ Server not responding"
fi

# Test 2: Tor status
echo "2. Testing /tor_status..."
TOR_RESPONSE=$(curl -s http://localhost:8080/tor_status)
echo "$TOR_RESPONSE" | grep -q '"tor_enabled": true'
if [ $? -eq 0 ]; then
    echo "   ✓ Tor is enabled"
else
    echo "   ❌ Tor is not enabled"
fi

echo "$TOR_RESPONSE" | grep -q '"is_tor_exit": true'
if [ $? -eq 0 ]; then
    echo "   ✓ Tor is working!"
    EXIT_IP=$(echo "$TOR_RESPONSE" | grep -o '"exit_ip": "[^"]*"' | cut -d'"' -f4)
    echo "   → Exit IP: $EXIT_IP"
else
    echo "   ❌ Tor is not working"
fi

# Show logs
echo ""
echo "=========================================="
echo "Container Logs (last 20 lines):"
echo "=========================================="
docker logs --tail 20 youtube-server-test

# Cleanup prompt
echo ""
echo "=========================================="
echo "Test complete!"
echo "=========================================="
echo ""
echo "To view full logs:"
echo "  docker logs youtube-server-test"
echo ""
echo "To stop and remove container:"
echo "  docker stop youtube-server-test"
echo "  docker rm youtube-server-test"
echo ""
echo "To remove image:"
echo "  docker rmi youtube-server-test"
echo ""
read -p "Stop and remove container now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker stop youtube-server-test
    docker rm youtube-server-test
    echo "✓ Container stopped and removed"
fi
