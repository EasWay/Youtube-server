# Tor Network Integration for YouTube Server

This guide explains how to use the Tor network with your YouTube server on Render to bypass IP blocks and rate limits.

## What is Tor?

Tor (The Onion Router) is a free, open-source network that routes your traffic through multiple relays, providing:
- **Anonymity**: Your real IP is hidden
- **IP Rotation**: Get a new IP address by renewing circuits
- **Bypass Blocks**: Circumvent IP-based rate limiting
- **Free & Open Source**: No cost, community-maintained

## How It Works

1. Your server connects to the Tor network via a SOCKS5 proxy (localhost:9050)
2. All YouTube requests are routed through Tor
3. The circuit (IP address) automatically renews every 10 requests
4. On rate limits, the circuit is immediately renewed for a fresh IP

## Setup on Render

### Automatic Setup (Recommended)

The server is pre-configured to use Tor. Just deploy with these environment variables:

```yaml
USE_TOR: True
TOR_PROXY_HOST: 127.0.0.1
TOR_PROXY_PORT: 9050
TOR_CONTROL_PORT: 9051
```

These are already set in `render.yaml`, so deployment should work out of the box.

### Manual Configuration

If you need to customize, set these environment variables in Render dashboard:

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_TOR` | `False` | Enable/disable Tor routing |
| `TOR_PROXY_HOST` | `127.0.0.1` | Tor SOCKS5 proxy host |
| `TOR_PROXY_PORT` | `9050` | Tor SOCKS5 proxy port |
| `TOR_CONTROL_PORT` | `9051` | Tor control port for circuit renewal |

## Features

### Automatic IP Rotation
- New circuit every 10 requests
- Immediate renewal on rate limits (429 errors)
- Configurable in `utils.py` via `_tor_max_circuit_age`

### Retry Logic
- 3 retry attempts with exponential backoff
- Automatic circuit renewal between retries
- Detailed logging for debugging

### Fallback Support
- Works alongside regular proxies
- Tor takes priority if enabled
- Falls back to direct connection if Tor fails

## Testing Tor Connection

### Check if Tor is Running

```bash
# SSH into your Render instance
curl --socks5 127.0.0.1:9050 https://check.torproject.org/api/ip
```

Expected response:
```json
{"IsTor": true, "IP": "xxx.xxx.xxx.xxx"}
```

### Test with Python

Create `test_tor.py`:

```python
import requests

proxies = {
    'http': 'socks5://127.0.0.1:9050',
    'https': 'socks5://127.0.0.1:9050'
}

# Check your IP through Tor
response = requests.get('https://api.ipify.org?format=json', proxies=proxies)
print(f"Your Tor IP: {response.json()['ip']}")

# Verify it's a Tor exit node
response = requests.get('https://check.torproject.org/api/ip', proxies=proxies)
print(f"Is Tor: {response.json()['IsTor']}")
```

Run: `python test_tor.py`

## Performance Considerations

### Speed
- Tor is slower than direct connections (3-5x typically)
- High-resolution downloads will take longer
- Trade-off: Speed vs. avoiding rate limits

### Optimization Tips
1. **Default to 720p**: Server defaults to 720p instead of highest quality
2. **Batch Requests**: Group multiple operations when possible
3. **Circuit Renewal**: Adjust `_tor_max_circuit_age` based on your needs
4. **Timeout Settings**: Increase timeouts for large downloads

## Troubleshooting

### Tor Not Starting

Check logs for:
```
Tor is running successfully on port 9050
```

If missing, Tor installation failed. Check build logs.

### Connection Timeouts

Tor can be slow. Increase timeouts:
```python
# In utils.py, modify create_youtube_with_retry
initial_delay = 5  # Increase from 2
```

### Rate Limits Still Occurring

1. Check if Tor is actually being used:
   ```python
   logger.info(f"Using Tor: {USE_TOR}")
   ```

2. Verify circuit renewal:
   ```python
   logger.info(f"Circuit age: {_tor_circuit_age}")
   ```

3. Reduce `_tor_max_circuit_age` for more frequent IP changes

### Tor Circuit Renewal Failing

Requires `stem` library and control port access:
```bash
pip install stem
```

Check control port is accessible:
```bash
netstat -an | grep 9051
```

## Advanced Configuration

### Custom Tor Configuration

Edit `setup_tor.sh` to customize `/etc/tor/torrc`:

```bash
# Faster circuit building
CircuitBuildTimeout 10
LearnCircuitBuildTimeout 0

# Prefer fast exit nodes
ExitNodes {us},{ca},{gb}
StrictNodes 0

# More aggressive circuit renewal
MaxCircuitDirtiness 300
```

### Multiple Tor Instances

Run multiple Tor instances on different ports for parallel requests:

```bash
# Instance 1: Port 9050
tor -f /etc/tor/torrc1 &

# Instance 2: Port 9060
tor -f /etc/tor/torrc2 &
```

Update `utils.py` to rotate between instances.

## Security Notes

1. **HTTPS**: Always use HTTPS endpoints (YouTube uses HTTPS by default)
2. **No Logging**: Tor doesn't log your traffic
3. **Exit Node Risk**: Exit nodes can see unencrypted traffic (not an issue with HTTPS)
4. **Legal**: Using Tor is legal in most countries, but check local laws

## Monitoring

### Check Tor Status

```python
# Add to main.py
@app.route('/tor_status')
async def tor_status():
    if not USE_TOR:
        return jsonify({"tor_enabled": False})
    
    try:
        # Test Tor connection
        proxies = {'http': f'socks5://{TOR_PROXY_HOST}:{TOR_PROXY_PORT}'}
        response = requests.get('https://check.torproject.org/api/ip', 
                              proxies=proxies, timeout=10)
        return jsonify({
            "tor_enabled": True,
            "is_tor": response.json().get('IsTor', False),
            "exit_ip": response.json().get('IP'),
            "circuit_age": _tor_circuit_age
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

### Logs to Watch

```bash
# Render logs will show:
"Using Tor network (SOCKS5 proxy)"
"Tor circuit renewed - new IP address obtained"
"Rate limited on Tor, renewing circuit..."
```

## Comparison: Tor vs Regular Proxies

| Feature | Tor | Regular Proxies |
|---------|-----|-----------------|
| Cost | Free | Usually paid |
| Speed | Slow (3-5x slower) | Fast |
| IP Rotation | Automatic | Manual/limited |
| Anonymity | High | Medium |
| Setup | Complex | Simple |
| Reliability | Variable | Depends on provider |

## When to Use Tor

✅ **Use Tor when:**
- Experiencing frequent rate limits
- Need free IP rotation
- Privacy is important
- Budget is limited

❌ **Don't use Tor when:**
- Speed is critical
- Downloading very large files
- Have reliable paid proxies
- Tor is blocked in your region

## Alternative: Hybrid Approach

Use both Tor and regular proxies:

```python
# In settings.py
USE_TOR = True
PROXIES = "http://proxy1.com:8080,http://proxy2.com:8080"

# In utils.py - modify get_proxies() to return both
# Tor will be tried first, then fall back to regular proxies
```

## Support

If you encounter issues:
1. Check Render build logs
2. Verify Tor is running: `pgrep -x "tor"`
3. Test connection: `curl --socks5 127.0.0.1:9050 https://check.torproject.org/api/ip`
4. Review application logs for Tor-related messages

## References

- [Tor Project](https://www.torproject.org/)
- [Stem Documentation](https://stem.torproject.org/)
- [PySocks Documentation](https://github.com/Anorov/PySocks)
- [Render Documentation](https://render.com/docs)
