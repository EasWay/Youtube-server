# YouTube Server with Tor Network Integration

## 🎯 What This Does

Your YouTube server now routes all requests through the **Tor network** to bypass IP-based rate limiting and blocks. This is completely free and open-source.

## ✨ Key Features

- ✅ **Automatic IP Rotation**: New IP every 10 requests
- ✅ **Rate Limit Bypass**: Avoid YouTube's 429 errors
- ✅ **Free & Open Source**: No proxy costs
- ✅ **Auto-Recovery**: Renews circuit on failures
- ✅ **Docker-Based**: Easy deployment on Render
- ✅ **Monitoring**: `/tor_status` endpoint to check health

## 🚀 Quick Start

### Deploy to Render

1. **Push to GitHub**:
   ```bash
   git add .
   git commit -m "Add Tor support"
   git push origin main
   ```

2. **Create Web Service on Render**:
   - Environment: **Docker**
   - Use `render.yaml` configuration
   - Deploy!

3. **Verify**:
   ```bash
   curl https://your-service.onrender.com/tor_status
   ```

See [RENDER_DEPLOYMENT.md](./RENDER_DEPLOYMENT.md) for detailed steps.

### Test Locally (Optional)

**Windows**:
```bash
test_docker_local.bat
```

**Linux/Mac**:
```bash
chmod +x test_docker_local.sh
./test_docker_local.sh
```

## 📊 How It Works

```
Your App → YouTube Server → Tor Network → YouTube
                              ↓
                        New IP every 10 requests
                        Auto-renew on rate limits
```

## 🔍 Check if Tor is Working

### Method 1: Status Endpoint

Visit: `https://your-service.onrender.com/tor_status`

**Success Response**:
```json
{
  "tor_enabled": true,
  "tor_working": true,
  "is_tor_exit": true,
  "exit_ip": "185.220.101.xxx",
  "message": "✓ Tor is working perfectly!"
}
```

### Method 2: Test Script

```bash
python test_render_tor.py
```

### Method 3: Check Logs

In Render dashboard, look for:
```
TOR NETWORK ENABLED
Tor Proxy: 127.0.0.1:9050
Using Tor network (SOCKS5 proxy)
```

## ⚙️ Configuration

### Environment Variables (in render.yaml)

| Variable | Value | Description |
|----------|-------|-------------|
| `USE_TOR` | `True` | Enable Tor routing |
| `TOR_PROXY_HOST` | `127.0.0.1` | Tor proxy host |
| `TOR_PROXY_PORT` | `9050` | Tor proxy port |
| `TOR_CONTROL_PORT` | `9051` | Control port for circuit renewal |

### Disable Tor

Set `USE_TOR=False` in Render environment variables.

## 📈 Performance

| Metric | With Tor | Without Tor |
|--------|----------|-------------|
| Speed | 3-5x slower | Normal |
| Rate Limits | Rare | Common |
| Cost | Free | Free (or proxy costs) |
| IP Rotation | Automatic | None |

**Trade-off**: Slower downloads for avoiding rate limits.

## 🛠️ Files Overview

| File | Purpose |
|------|---------|
| `Dockerfile` | Docker image with Tor installed |
| `render.yaml` | Render deployment configuration |
| `utils.py` | Tor integration logic |
| `settings.py` | Tor configuration |
| `main.py` | `/tor_status` endpoint |
| `test_render_tor.py` | Test Tor on deployed server |
| `test_docker_local.bat/sh` | Test Docker build locally |

## 📚 Documentation

- **[RENDER_DEPLOYMENT.md](./RENDER_DEPLOYMENT.md)** - Complete deployment guide
- **[TOR_SETUP.md](./TOR_SETUP.md)** - Detailed Tor documentation
- **[CHECK_TOR_ON_RENDER.md](./CHECK_TOR_ON_RENDER.md)** - Verification guide
- **[PROXY_SETUP.md](./PROXY_SETUP.md)** - Alternative proxy options

## 🐛 Troubleshooting

### Tor Not Working

1. **Check build logs** - Look for Tor installation errors
2. **Verify environment** - Ensure `USE_TOR=True`
3. **Test endpoint** - Visit `/tor_status`
4. **Check logs** - Look for "Using Tor network"

### Still Getting Rate Limited

1. **Verify Tor is active** - Check `/tor_status`
2. **Reduce circuit age** - Edit `_tor_max_circuit_age` in `utils.py`
3. **Add backup proxies** - Set `PROXIES` env var

### Slow Performance

This is normal with Tor! Options:
1. Accept slower speeds (trade-off for avoiding blocks)
2. Use paid proxies instead (`USE_TOR=False`)
3. Hybrid: Tor + paid proxies

## 💡 Tips

1. **Monitor logs** - Watch for "Tor circuit renewed" messages
2. **Default quality** - Server uses 720p for better Tor performance
3. **Timeouts** - Increase client timeouts to 60s for Tor
4. **Upgrade plan** - Starter tier ($7/mo) for better performance

## 🔐 Security

- ✅ All traffic encrypted through Tor
- ✅ Your real IP is hidden
- ✅ YouTube sees Tor exit node IP
- ✅ HTTPS end-to-end encryption
- ✅ No logging of requests

## 📞 Support

**Issues?**
1. Check [RENDER_DEPLOYMENT.md](./RENDER_DEPLOYMENT.md) troubleshooting section
2. Review Render build/service logs
3. Test `/tor_status` endpoint
4. Verify Docker builds locally

## 🎉 Success Indicators

You'll know Tor is working when:
- ✅ `/tor_status` shows `"is_tor_exit": true`
- ✅ Logs show "Using Tor network (SOCKS5 proxy)"
- ✅ Rate limits (429 errors) are rare/gone
- ✅ Exit IP changes periodically

## 🚦 Next Steps

After deployment:

1. ✅ Test `/tor_status` endpoint
2. ✅ Download a test video
3. ✅ Monitor logs for Tor messages
4. ✅ Update Android app with new server URL
5. ✅ Set up monitoring/alerts
6. ✅ Consider Starter tier for production

---

**Ready to deploy?** See [RENDER_DEPLOYMENT.md](./RENDER_DEPLOYMENT.md) for step-by-step instructions!
