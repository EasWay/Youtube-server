# Proxy Setup Guide for YouTube Server

## Overview

This guide explains how to configure proxies to avoid YouTube's rate limiting (HTTP 429 errors). The server now includes automatic proxy rotation with retry logic.

## Why Use Proxies?

YouTube rate limits requests from the same IP address. Proxies route your requests through different IP addresses, helping you:
- Avoid 429 "Too Many Requests" errors
- Handle higher request volumes
- Distribute load across multiple IPs

## Proxy Types

### 1. Tor Network (FREE - Recommended for Development)
- **Best for**: Development, testing, personal use
- **Pros**: 
  - Completely free and open-source
  - Secure and anonymous
  - Community-run network
  - Automatic IP rotation
  - No registration required
- **Cons**: 
  - Slower than paid proxies
  - Not suitable for high-volume production
- **Setup**: See [Tor Setup Guide](#tor-network-setup-free) below

### 2. Residential Proxies (Recommended for Production)
- **Best for**: Production use, high volume
- **Pros**: Look like real users, rarely blocked
- **Cons**: More expensive
- **Providers**: Bright Data, Smartproxy, Oxylabs

### 3. Datacenter Proxies
- **Best for**: Testing, medium-volume use
- **Pros**: Fast and affordable
- **Cons**: More easily detected and blocked
- **Providers**: Webshare, ProxyRack, IPRoyal

### 4. Free Public Proxies
- **Not recommended**: Unreliable, slow, potentially unsafe

## Configuration

### Tor Network Setup (FREE)

#### Step 1: Install Tor

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install tor
```

**macOS:**
```bash
brew install tor
```

**Windows:**
1. Download Tor Expert Bundle from https://www.torproject.org/download/tor/
2. Extract and run `tor.exe`

Or install Tor Browser and use its built-in Tor service.

#### Step 2: Start Tor Service

**Linux/macOS:**
```bash
# Start Tor service
sudo systemctl start tor

# Or run Tor directly
tor
```

**Windows:**
```bash
# Run tor.exe from the extracted folder
tor.exe
```

Tor will start a SOCKS5 proxy on `localhost:9050` by default.

#### Step 3: Configure Server

**Option A: Using SOCKS5 (Requires PySocks)**

Install PySocks for SOCKS5 support:
```bash
pip install PySocks
```

Then set environment variables:
```bash
export AUTH=True
export PROXIES=socks5://127.0.0.1:9050
```

**Option B: Using Privoxy (HTTP Proxy Wrapper)**

Privoxy converts Tor's SOCKS5 to HTTP proxy:

1. Install Privoxy:
   ```bash
   # Linux
   sudo apt install privoxy
   
   # macOS
   brew install privoxy
   ```

2. Configure Privoxy to use Tor:
   ```bash
   # Edit /etc/privoxy/config
   echo "forward-socks5 / 127.0.0.1:9050 ." | sudo tee -a /etc/privoxy/config
   ```

3. Start Privoxy:
   ```bash
   sudo systemctl start privoxy
   ```

4. Configure server:
   ```bash
   export AUTH=True
   export PROXIES=http://127.0.0.1:8118
   ```

#### Step 4: Test Tor Connection

```bash
# Check your IP through Tor
curl --socks5 127.0.0.1:9050 https://api.ipify.org

# Or with Privoxy
curl -x http://127.0.0.1:8118 https://api.ipify.org
```

#### Step 5: Run Your Server

```bash
python main.py
```

#### Tor Configuration Tips

1. **IP Rotation**: Tor automatically rotates IPs every 10 minutes
2. **Manual Rotation**: Force new circuit:
   ```bash
   # Send NEWNYM signal to Tor
   echo -e 'AUTHENTICATE ""\r\nSIGNAL NEWNYM\r\nQUIT' | nc 127.0.0.1 9051
   ```

3. **Multiple Tor Instances**: Run multiple Tor instances on different ports:
   ```bash
   # Instance 1 on port 9050
   tor --SocksPort 9050
   
   # Instance 2 on port 9051
   tor --SocksPort 9051 --DataDirectory /tmp/tor2
   
   # Instance 3 on port 9052
   tor --SocksPort 9052 --DataDirectory /tmp/tor3
   ```
   
   Then configure:
   ```bash
   export PROXIES=socks5://127.0.0.1:9050,socks5://127.0.0.1:9051,socks5://127.0.0.1:9052
   ```

4. **Performance**: Tor is slower than paid proxies but sufficient for moderate use

### Environment Variables

Set the `PROXIES` environment variable with comma-separated proxy URLs:

```bash
# Tor (via Privoxy)
PROXIES=http://127.0.0.1:8118

# Tor SOCKS5 (requires PySocks)
PROXIES=socks5://127.0.0.1:9050

# Multiple Tor instances
PROXIES=socks5://127.0.0.1:9050,socks5://127.0.0.1:9051,socks5://127.0.0.1:9052

# Regular HTTP proxies without authentication
PROXIES=http://proxy1.example.com:8080,http://proxy2.example.com:8080

# With authentication
PROXIES=http://user1:pass1@proxy1.example.com:8080,http://user2:pass2@proxy2.example.com:8080

# Mixed (Tor + paid proxies)
PROXIES=http://127.0.0.1:8118,http://user:pass@premium.proxy.com:8080
```

### Proxy URL Format

```
protocol://[username:password@]host:port
```

Supported protocols:
- `http://` - Standard HTTP proxy
- `https://` - HTTPS proxy
- `socks5://` - SOCKS5 proxy (requires PySocks: `pip install PySocks`)

Examples:
- `http://123.456.789.0:8080`
- `https://123.456.789.0:8080`
- `socks5://127.0.0.1:9050` (Tor)
- `http://myuser:mypass@proxy.example.com:8080`
- `https://user123:secret@10.0.0.1:3128`

### Enable Authentication

Proxies only work when `AUTH=True`:

```bash
AUTH=True
PROXIES=http://user:pass@proxy.example.com:8080
```

## How It Works

### Automatic Proxy Rotation

The server automatically:
1. Rotates through available proxies in round-robin fashion
2. Retries failed requests with exponential backoff (2s, 4s, 8s)
3. Switches proxies when rate limited
4. Tracks and skips failed proxies
5. Resets failed proxy list when all proxies fail

### Retry Logic

```
Attempt 1: Use Proxy A → 429 Error → Wait 2s
Attempt 2: Use Proxy B → 429 Error → Wait 4s
Attempt 3: Use Proxy C → Success!
```

## Testing Your Proxies

### 1. Test Tor Connection

```bash
# Test Tor SOCKS5
curl --socks5 127.0.0.1:9050 https://check.torproject.org/api/ip

# Test Tor via Privoxy
curl -x http://127.0.0.1:8118 https://check.torproject.org/api/ip

# Should return: {"IsTor":true,"IP":"xxx.xxx.xxx.xxx"}
```

### 2. Test Regular Proxy

```bash
curl -x http://user:pass@proxy.example.com:8080 https://www.youtube.com
```

### 3. Test in Python

```python
import requests

# Test Tor
proxies = {
    'http': 'socks5://127.0.0.1:9050',
    'https': 'socks5://127.0.0.1:9050'
}

response = requests.get('https://check.torproject.org/api/ip', proxies=proxies)
print(response.json())  # Should show IsTor: true
```

### 4. Test Your Server

```bash
# Set environment variables
export AUTH=True
export PROXIES=http://127.0.0.1:8118  # or socks5://127.0.0.1:9050

# Start server
python main.py

# Test endpoint
curl -X POST http://localhost:5000/info?url=https://youtu.be/dQw4w9WgXcQ
```

### 5. Use Test Script

```bash
# Run the included test script
python test_proxy.py

# Run full test suite
python test_proxy.py --full
```

## Recommended Proxy Providers

### For Production

1. **Bright Data** (formerly Luminati)
   - Most reliable
   - Residential & datacenter options
   - ~$500/month for 40GB

2. **Smartproxy**
   - Good balance of price/quality
   - Residential proxies
   - ~$75/month for 5GB

3. **Oxylabs**
   - Enterprise-grade
   - Excellent for YouTube
   - ~$300/month

### For Development/Testing

1. **Webshare**
   - 10 free proxies
   - Good for testing
   - Datacenter proxies

2. **ProxyRack**
   - Affordable plans
   - ~$50/month
   - Mixed quality

## Best Practices

### 1. Use Multiple Proxies
Configure at least 3-5 proxies for reliable rotation:

```bash
PROXIES=http://proxy1:8080,http://proxy2:8080,http://proxy3:8080,http://proxy4:8080,http://proxy5:8080
```

### 2. Monitor Logs
Watch for proxy failures:

```bash
tail -f app.log | grep -i proxy
```

### 3. Rotate Credentials
Change proxy credentials regularly to maintain access.

### 4. Use Residential Proxies for High Volume
If downloading >100 videos/day, use residential proxies.

### 5. Implement Rate Limiting
Even with proxies, don't hammer YouTube:

```python
# Add delays between requests
import time
time.sleep(1)  # 1 second between requests
```

## Troubleshooting

### Still Getting 429 Errors

1. **Check proxy is working**:
   ```bash
   curl -x http://your-proxy:8080 https://api.ipify.org
   ```

2. **Verify AUTH is enabled**:
   ```bash
   echo $AUTH  # Should output: True
   ```

3. **Check proxy format**:
   - Ensure no spaces in PROXIES string
   - Verify username/password don't contain special characters
   - Use URL encoding for special characters

4. **Add more proxies**:
   - Single proxy can still get rate limited
   - Use 5+ proxies for best results

### Proxy Connection Errors

1. **Timeout errors**: Proxy might be slow or down
2. **Authentication failed**: Check username/password
3. **Connection refused**: Verify proxy host and port

### All Proxies Failing

The server will reset the failed proxy list and retry. Check logs:

```
WARNING - All proxies failed, resetting failed proxy list
```

## Example Configurations

### Free Setup (Tor Only)

```bash
# Install Tor and Privoxy
sudo apt install tor privoxy

# Configure Privoxy for Tor
echo "forward-socks5 / 127.0.0.1:9050 ." | sudo tee -a /etc/privoxy/config

# Start services
sudo systemctl start tor
sudo systemctl start privoxy

# Configure server
export AUTH=True
export PROXIES=http://127.0.0.1:8118
export DEBUG=True

# Run server
python main.py
```

### Free Setup (Multiple Tor Instances)

```bash
# Start 3 Tor instances
tor --SocksPort 9050 &
tor --SocksPort 9051 --DataDirectory /tmp/tor2 &
tor --SocksPort 9052 --DataDirectory /tmp/tor3 &

# Install PySocks
pip install PySocks

# Configure server
export AUTH=True
export PROXIES=socks5://127.0.0.1:9050,socks5://127.0.0.1:9051,socks5://127.0.0.1:9052
export DEBUG=True

# Run server
python main.py
```

### Development (Free Proxies)

```bash
AUTH=True
PROXIES=http://free-proxy1.com:8080,http://free-proxy2.com:8080
DEBUG=True
```

### Production (Paid Proxies)

```bash
AUTH=True
PROXIES=http://user1:pass1@premium1.proxy.com:8080,http://user2:pass2@premium2.proxy.com:8080,http://user3:pass3@premium3.proxy.com:8080
DEBUG=False
MAX_SIZE=5368709120
EXPIRATION=3600
```

### Hybrid Setup (Tor + Paid Proxies)

```bash
# Best of both worlds: Free Tor + reliable paid proxies
AUTH=True
PROXIES=http://127.0.0.1:8118,http://user:pass@premium.proxy.com:8080,http://user:pass@premium2.proxy.com:8080
DEBUG=False
```

### Render.com Deployment with Tor

**NEW: Tor is now fully supported on Render!**

The server includes automatic Tor installation and configuration for Render deployments.

#### Quick Setup

1. **Deploy to Render** - Tor is pre-configured in `render.yaml`
2. **Verify in logs**:
   ```
   Setting up Tor...
   Tor is running successfully on port 9050
   Using Tor network (SOCKS5 proxy)
   ```

3. **Environment variables** (already set in render.yaml):
   ```yaml
   USE_TOR: True
   TOR_PROXY_HOST: 127.0.0.1
   TOR_PROXY_PORT: 9050
   TOR_CONTROL_PORT: 9051
   ```

#### Features on Render

- **Automatic Installation**: Tor installs during build
- **Auto-start**: Tor starts with your server
- **IP Rotation**: New IP every 10 requests
- **Rate Limit Handling**: Automatic circuit renewal on 429 errors
- **No Extra Cost**: Completely free

#### Testing on Render

After deployment, check your server logs or add this endpoint to test:

```python
@app.route('/tor_status')
async def tor_status():
    from settings import USE_TOR, TOR_PROXY_HOST, TOR_PROXY_PORT
    if not USE_TOR:
        return jsonify({"tor_enabled": False})
    
    try:
        import requests
        proxies = {
            'http': f'socks5://{TOR_PROXY_HOST}:{TOR_PROXY_PORT}',
            'https': f'socks5://{TOR_PROXY_HOST}:{TOR_PROXY_PORT}'
        }
        response = requests.get('https://check.torproject.org/api/ip', 
                              proxies=proxies, timeout=10)
        return jsonify({
            "tor_enabled": True,
            "is_tor": response.json().get('IsTor', False),
            "exit_ip": response.json().get('IP')
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

#### Disable Tor on Render

If you want to use paid proxies instead:

```yaml
# In Render dashboard, set:
USE_TOR: False
AUTH: True
PROXIES: "http://user:pass@proxy.com:8080"
```

#### Performance Notes

- Tor is slower (3-5x) but free and effective
- Server defaults to 720p for better performance
- For high-volume production, consider paid proxies
- Hybrid approach: Use both Tor and paid proxies

See [TOR_SETUP.md](./TOR_SETUP.md) for detailed Tor documentation.

---

For VPS deployment (DigitalOcean, AWS, etc.) without the automatic setup:
```bash
# Install Tor on your VPS
sudo apt install tor privoxy

# Configure as above, then set environment variables in your deployment
AUTH=True
PROXIES=http://127.0.0.1:8118
```

## Cost Estimation

### Free (Tor Network)
- **Cost**: $0/month
- **Suitable for**: 
  - Personal use
  - Development/testing
  - Low-medium volume (10-100 videos/day)
- **Limitations**: 
  - Slower download speeds
  - May need multiple instances for higher volume

### Light Use (<50 videos/day)
- Free proxies or 1-2 datacenter proxies
- Cost: $0-20/month

### Medium Use (50-500 videos/day)
- 3-5 datacenter proxies or Tor + 1-2 paid proxies
- Cost: $50-100/month

### Heavy Use (500+ videos/day)
- 5-10 residential proxies
- Cost: $200-500/month

## Security Notes

1. **Never commit proxy credentials** to version control
2. **Use environment variables** for all sensitive data
3. **Rotate credentials** regularly
4. **Monitor usage** to detect unauthorized access
5. **Use HTTPS proxies** when possible

## Additional Resources

- [Pytubefix Documentation](https://github.com/JuanBindez/pytubefix)
- [Requests Proxy Documentation](https://requests.readthedocs.io/en/latest/user/advanced/#proxies)
- [YouTube API Rate Limits](https://developers.google.com/youtube/v3/getting-started#quota)

## Support

If you continue experiencing issues:
1. Check server logs: `tail -f app.log`
2. Test proxies independently
3. Verify environment variables are set correctly
4. Consider upgrading to better proxy service
