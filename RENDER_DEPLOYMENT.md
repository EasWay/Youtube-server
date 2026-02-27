# Deploying YouTube Server with Tor on Render

## Overview

This guide shows how to deploy the YouTube server with Tor network integration on Render using Docker.

## Why Docker?

Render's native Python environment doesn't allow installing system packages like Tor. Docker gives us full control to install Tor and configure it properly.

## Prerequisites

- GitHub account (to connect your repository)
- Render account (free tier works)
- Your code pushed to GitHub

## Deployment Steps

### 1. Push Your Code to GitHub

Make sure all files are committed and pushed:

```bash
cd Youtube-server
git add .
git commit -m "Add Tor support with Docker"
git push origin main
```

### 2. Create New Web Service on Render

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Select your repository

### 3. Configure the Service

**Basic Settings:**
- **Name**: `youtube-server` (or your preferred name)
- **Region**: Choose closest to your users
- **Branch**: `main` (or your default branch)
- **Root Directory**: `Youtube-server` (if server is in subdirectory)

**Build Settings:**
- **Environment**: `Docker`
- **Dockerfile Path**: `./Dockerfile` (or `Youtube-server/Dockerfile` if in subdirectory)

**Instance Type:**
- **Free** (for testing)
- **Starter** or higher (for production - better performance)

### 4. Environment Variables

Render will automatically use the variables from `render.yaml`, but you can also set them manually:

| Variable | Value | Description |
|----------|-------|-------------|
| `USE_TOR` | `True` | Enable Tor routing |
| `TOR_PROXY_HOST` | `127.0.0.1` | Tor SOCKS5 host |
| `TOR_PROXY_PORT` | `9050` | Tor SOCKS5 port |
| `TOR_CONTROL_PORT` | `9051` | Tor control port |
| `DEBUG` | `False` | Disable debug mode |
| `AUTH` | `False` | OAuth authentication |
| `PORT` | `8080` | Server port |

### 5. Deploy

Click "Create Web Service"

Render will:
1. Build the Docker image
2. Install Tor and dependencies
3. Start Tor service
4. Launch your application

**Build time**: 5-10 minutes (first deployment)

### 6. Verify Deployment

Once deployed, check:

**1. Build Logs:**
Look for:
```
Successfully built [image-id]
Successfully tagged [image-name]
```

**2. Service Logs:**
Look for:
```
[notice] Bootstrapped 100% (done): Done
TOR NETWORK ENABLED
Tor Proxy: 127.0.0.1:9050
```

**3. Test Endpoint:**
Visit: `https://your-service.onrender.com/tor_status`

Expected response:
```json
{
  "tor_enabled": true,
  "tor_working": true,
  "is_tor_exit": true,
  "exit_ip": "xxx.xxx.xxx.xxx"
}
```

## Testing Your Deployment

### From Your Local Machine

Run the test script:

```bash
# Update SERVER_URL in test_render_tor.py to your Render URL
python test_render_tor.py
```

### Using curl

```bash
# Check Tor status
curl https://your-service.onrender.com/tor_status

# Test video info
curl "https://your-service.onrender.com/info?url=https://youtu.be/dQw4w9WgXcQ"
```

### Using Browser

Simply visit:
```
https://your-service.onrender.com/tor_status
```

## Troubleshooting

### Build Fails

**Error: "Cannot find Dockerfile"**
- Solution: Check `dockerfilePath` in render.yaml
- Ensure Dockerfile is in the correct location

**Error: "apt-get: command not found"**
- Solution: You're using Python environment instead of Docker
- Change environment to Docker in Render settings

### Tor Not Starting

**Check logs for:**
```
[warn] Failed to bind one of the listener ports
```

**Solution:**
- Tor might be trying to bind to a port that's already in use
- The Dockerfile is configured correctly, redeploy

### Tor Working But Slow

This is normal! Tor is 3-5x slower than direct connections.

**Optimizations:**
1. Server defaults to 720p (already configured)
2. Use Starter plan or higher for better CPU
3. Consider hybrid approach (Tor + paid proxies)

### Connection Timeouts

**Increase timeouts in your client:**

```python
response = requests.get(
    'https://your-service.onrender.com/info',
    params={'url': video_url},
    timeout=60  # Increase from default 10s
)
```

## Monitoring

### Check Tor Status Regularly

Add this to your monitoring:

```python
import requests

def check_tor_health():
    response = requests.get('https://your-service.onrender.com/tor_status')
    data = response.json()
    return data.get('is_tor_exit', False)
```

### Watch Logs

In Render dashboard:
1. Go to your service
2. Click "Logs" tab
3. Look for:
   - "Using Tor network (SOCKS5 proxy)"
   - "Tor circuit renewed"
   - Any error messages

## Updating Your Deployment

### Method 1: Auto-Deploy (Recommended)

Render auto-deploys when you push to GitHub:

```bash
git add .
git commit -m "Update server"
git push origin main
```

Render will automatically rebuild and redeploy.

### Method 2: Manual Deploy

In Render dashboard:
1. Go to your service
2. Click "Manual Deploy" → "Deploy latest commit"

## Performance Expectations

### Free Tier
- **Spins down after 15 minutes of inactivity**
- **Cold start**: 30-60 seconds
- **Good for**: Testing, personal use

### Starter Tier ($7/month)
- **Always on**
- **Better CPU/RAM**
- **Good for**: Production, regular use

### With Tor Enabled
- **Download speed**: 3-5x slower than direct
- **Rate limits**: Rare (IP rotates automatically)
- **Reliability**: Good

## Cost Estimation

### Free Tier
- **Cost**: $0/month
- **Limitations**: 
  - 750 hours/month
  - Spins down after inactivity
  - Slower performance

### Starter Tier
- **Cost**: $7/month
- **Benefits**:
  - Always on
  - Better performance
  - No spin-down

### Bandwidth
- Render includes generous bandwidth
- Tor traffic counts toward your bandwidth
- Monitor usage in dashboard

## Alternative: Disable Tor

If Tor is too slow or you have paid proxies:

**In Render Dashboard:**
1. Go to Environment variables
2. Set `USE_TOR` = `False`
3. Set `AUTH` = `True`
4. Set `PROXIES` = `http://user:pass@proxy.com:8080`
5. Save changes (auto-redeploys)

## Security Notes

1. **HTTPS**: Render provides free SSL certificates
2. **Environment Variables**: Never commit secrets to Git
3. **Tor**: All traffic is encrypted through Tor network
4. **Logs**: Don't log sensitive information

## Best Practices

### 1. Use Environment Variables

Never hardcode:
- API keys
- Proxy credentials
- OAuth tokens

### 2. Monitor Logs

Set up log monitoring:
- Check for errors daily
- Watch for rate limit messages
- Monitor Tor circuit renewals

### 3. Set Up Alerts

In Render:
- Enable email notifications
- Set up health checks
- Monitor uptime

### 4. Regular Updates

Keep dependencies updated:
```bash
pip list --outdated
pip install --upgrade package-name
```

Update requirements.txt and redeploy.

## Support Resources

- **Render Docs**: https://render.com/docs
- **Tor Project**: https://www.torproject.org/
- **This Project**: See TOR_SETUP.md for detailed Tor info

## Quick Reference

### Important URLs

```
Service URL: https://your-service.onrender.com
Tor Status: https://your-service.onrender.com/tor_status
Health Check: https://your-service.onrender.com/ping
```

### Important Files

```
Dockerfile          - Docker configuration with Tor
render.yaml         - Render deployment config
requirements.txt    - Python dependencies
main.py            - Application entry point
utils.py           - Tor integration logic
settings.py        - Configuration
```

### Key Commands

```bash
# Test locally with Docker
docker build -t youtube-server .
docker run -p 8080:8080 youtube-server

# Test Tor status
curl https://your-service.onrender.com/tor_status

# View logs
# (Use Render dashboard)

# Redeploy
git push origin main
```

## Next Steps

After successful deployment:

1. ✅ Test `/tor_status` endpoint
2. ✅ Try downloading a video
3. ✅ Monitor logs for "Using Tor network"
4. ✅ Update your Android app to use new server URL
5. ✅ Set up monitoring/alerts
6. ✅ Consider upgrading to Starter tier for production

## Getting Help

If you encounter issues:

1. Check build logs in Render dashboard
2. Review service logs for errors
3. Test `/tor_status` endpoint
4. See TROUBLESHOOTING section above
5. Check TOR_SETUP.md for detailed Tor info
