# How to Check if Tor is Working on Your Render Server

## Quick Check

Visit this URL in your browser:
```
https://youtube-server-2n1t.onrender.com/tor_status
```

### Expected Response (Tor Working):
```json
{
  "tor_enabled": true,
  "tor_configured": true,
  "tor_working": true,
  "is_tor_exit": true,
  "exit_ip": "xxx.xxx.xxx.xxx",
  "proxy_address": "127.0.0.1:9050",
  "message": "✓ Tor is working perfectly!"
}
```

### If Tor is Not Working:
```json
{
  "tor_enabled": true,
  "tor_configured": true,
  "tor_working": false,
  "is_tor_exit": false,
  "exit_ip": null,
  "error": "Connection refused...",
  "message": "✗ Tor connection failed"
}
```

## Step-by-Step Verification

### 1. Check Render Logs

Go to your Render dashboard → Your service → Logs

Look for these messages on startup:

✅ **Success indicators:**
```
Setting up Tor...
Starting Tor service...
Tor is running successfully on port 9050
============================================================
TOR NETWORK ENABLED
Tor Proxy: 127.0.0.1:9050
All YouTube requests will be routed through Tor
============================================================
```

❌ **Failure indicators:**
```
Warning: Tor may not have started properly
```

### 2. Test the /tor_status Endpoint

**Using curl:**
```bash
curl https://youtube-server-2n1t.onrender.com/tor_status
```

**Using Python:**
```python
import requests

response = requests.get('https://youtube-server-2n1t.onrender.com/tor_status')
print(response.json())
```

**Using your browser:**
Just visit: https://youtube-server-2n1t.onrender.com/tor_status

### 3. Check Environment Variables

In Render Dashboard:
1. Go to your service
2. Click "Environment" tab
3. Verify these are set:

```
USE_TOR = True
TOR_PROXY_HOST = 127.0.0.1
TOR_PROXY_PORT = 9050
TOR_CONTROL_PORT = 9051
```

### 4. Test with a Real Request

Try downloading a video and check the logs:

```bash
curl -X POST https://youtube-server-2n1t.onrender.com/info \
  -H "Content-Type: application/json" \
  -d '{"url": "https://youtu.be/dQw4w9WgXcQ"}'
```

In the logs, you should see:
```
Using Tor network (SOCKS5 proxy)
Successfully created YouTube object for: [Video Title]
```

## Troubleshooting

### Issue: "tor_enabled": false

**Solution:** Set environment variable in Render:
```
USE_TOR = True
```
Then redeploy.

### Issue: "tor_working": false with connection error

**Possible causes:**
1. Tor didn't install during build
2. Tor service didn't start
3. Build script didn't run

**Solution:**
1. Check build logs for errors
2. Verify `setup_tor.sh` has execute permissions
3. Redeploy the service

### Issue: Build fails with "apt-get: command not found"

**Cause:** Render's Python environment doesn't have apt-get by default

**Solution:** The setup script should handle this, but if it fails:
1. Check if Render changed their build environment
2. May need to use a Docker deployment instead
3. Alternative: Use paid proxies instead of Tor

### Issue: Tor installs but doesn't start

**Check logs for:**
```
Starting Tor service...
```

**Solution:**
1. The start command in `render.yaml` should start Tor
2. Verify the start command includes: `tor -f /etc/tor/torrc &`

## Alternative: Check from Application Logs

When your server handles a request, it logs proxy usage:

```
INFO - Using Tor network (SOCKS5 proxy)
INFO - Successfully created YouTube object for: Video Title
```

Or if there's an issue:
```
WARNING - Not using proxies because AUTH = False
```

## What Each Field Means

| Field | Meaning |
|-------|---------|
| `tor_enabled` | USE_TOR environment variable is True |
| `tor_configured` | Tor settings are configured |
| `tor_working` | Successfully connected to Tor proxy |
| `is_tor_exit` | Confirmed traffic is going through Tor network |
| `exit_ip` | The Tor exit node IP address (changes periodically) |
| `proxy_address` | The local Tor SOCKS5 proxy address |
| `error` | Error message if connection failed |

## Expected Behavior

### On Startup:
1. Build script installs Tor
2. Start command launches Tor service
3. Server starts and logs Tor status
4. `/tor_status` endpoint becomes available

### During Operation:
1. All YouTube requests route through Tor
2. IP changes every 10 requests
3. On rate limits, circuit renews automatically
4. Logs show "Using Tor network" for each request

## Performance Expectations

With Tor enabled:
- **Speed**: 3-5x slower than direct connection
- **Default quality**: 720p (optimized for Tor)
- **Rate limits**: Should be rare due to IP rotation
- **Reliability**: Good, but depends on Tor network

## Quick Test Script

Save this as `test_render_tor.py`:

```python
import requests
import json

SERVER_URL = "https://youtube-server-2n1t.onrender.com"

def test_tor_status():
    print("Testing Tor status...")
    response = requests.get(f"{SERVER_URL}/tor_status")
    data = response.json()
    
    print(json.dumps(data, indent=2))
    
    if data.get('is_tor_exit'):
        print("\n✓ SUCCESS: Tor is working!")
        print(f"Exit IP: {data.get('exit_ip')}")
        return True
    else:
        print("\n✗ FAILED: Tor is not working")
        if data.get('error'):
            print(f"Error: {data.get('error')}")
        return False

def test_video_info():
    print("\nTesting video info request...")
    response = requests.get(
        f"{SERVER_URL}/info",
        params={"url": "https://youtu.be/dQw4w9WgXcQ"}
    )
    
    if response.status_code == 200:
        print("✓ Video info request successful")
        data = response.json()
        print(f"Title: {data.get('title', 'N/A')}")
        return True
    else:
        print(f"✗ Request failed: {response.status_code}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Render Tor Status Check")
    print("=" * 60)
    
    tor_ok = test_tor_status()
    video_ok = test_video_info()
    
    print("\n" + "=" * 60)
    if tor_ok and video_ok:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed")
    print("=" * 60)
```

Run it:
```bash
python test_render_tor.py
```

## Need Help?

1. **Check Render logs first** - Most issues show up there
2. **Verify environment variables** - USE_TOR must be True
3. **Test /tor_status endpoint** - Quick way to verify
4. **Check build logs** - See if Tor installed correctly
5. **Redeploy** - Sometimes a fresh deploy fixes issues

## Disabling Tor

If you want to disable Tor and use direct connection or other proxies:

In Render dashboard, set:
```
USE_TOR = False
```

Or to use paid proxies instead:
```
USE_TOR = False
AUTH = True
PROXIES = http://user:pass@proxy.com:8080
```
