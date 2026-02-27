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

# Create necessary directories
RUN mkdir -p temp_files auth /etc/tor

# Configure Tor
RUN echo "SocksPort 0.0.0.0:9050" > /etc/tor/torrc && \
    echo "ControlPort 0.0.0.0:9051" >> /etc/tor/torrc && \
    echo "CookieAuthentication 0" >> /etc/tor/torrc && \
    echo "HashedControlPassword 16:872860B76453A77D60CA2BB8C1A7042072093276A3D701AD684053EC4C" >> /etc/tor/torrc && \
    echo "DataDirectory /var/lib/tor" >> /etc/tor/torrc && \
    echo "Log notice stdout" >> /etc/tor/torrc

# Expose port
EXPOSE 8080

# Start script that launches both Tor and the app
CMD tor -f /etc/tor/torrc & sleep 5 && hypercorn -b 0.0.0.0:8080 -w 4 main:app
