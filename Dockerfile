FROM python:3.12-slim

# Install system dependencies including Tor
RUN apt-get update && apt-get install -y \
    tor \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p temp_files auth /tmp/tor && \
    chmod 777 /tmp/tor

# Configure Tor to use /tmp for data directory (no permission issues)
RUN echo "SocksPort 127.0.0.1:9050" > /etc/tor/torrc && \
    echo "ControlPort 127.0.0.1:9051" >> /etc/tor/torrc && \
    echo "CookieAuthentication 0" >> /etc/tor/torrc && \
    echo "DataDirectory /tmp/tor" >> /etc/tor/torrc && \
    echo "Log notice stdout" >> /etc/tor/torrc

# Expose port
EXPOSE 8080

# Start script that launches both Tor and the app
# Run Tor in background, wait for it to bootstrap, then start the app
CMD tor -f /etc/tor/torrc & \
    echo "Waiting for Tor to bootstrap..." && \
    sleep 15 && \
    echo "Starting application..." && \
    hypercorn -b 0.0.0.0:8080 -w 4 main:app
