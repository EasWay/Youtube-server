#!/usr/bin/env python3
"""
Test script to check if Tor is working on your Render deployment
Run this from your local machine to verify your server's Tor setup
"""

import requests
import json
import sys

# Your Render server URL
SERVER_URL = "https://youtube-server-k9cd.onrender.com"

def test_tor_status():
    """Check if Tor is enabled and working on the server"""
    print("Checking Tor status on Render server...")
    print(f"Server: {SERVER_URL}")
    print("-" * 60)
    
    try:
        response = requests.get(f"{SERVER_URL}/tor_status", timeout=30)
        data = response.json()
        
        print("\nTor Status Response:")
        print(json.dumps(data, indent=2))
        print("-" * 60)
        
        # Analyze results
        if data.get('tor_enabled'):
            print("✓ Tor is ENABLED in configuration")
        else:
            print("✗ Tor is DISABLED")
            print("  → Set USE_TOR=True in Render environment variables")
            return False
        
        if data.get('tor_configured'):
            print(f"✓ Tor is configured at {data.get('proxy_address')}")
        
        if data.get('tor_working'):
            print("✓ Tor proxy is RESPONDING")
        else:
            print("✗ Tor proxy is NOT responding")
            if data.get('error'):
                print(f"  → Error: {data.get('error')}")
            return False
        
        if data.get('is_tor_exit'):
            print("✓ Traffic is routing through TOR NETWORK")
            print(f"  → Exit IP: {data.get('exit_ip')}")
            print("\n🎉 SUCCESS! Tor is working perfectly on your Render server!")
            return True
        else:
            print("✗ Connected but NOT using Tor network")
            print("  → Check Tor installation in build logs")
            return False
            
    except requests.exceptions.Timeout:
        print("✗ Request timed out")
        print("  → Server might be starting up, try again in a minute")
        return False
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to server")
        print("  → Check if server is running")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_ping():
    """Test basic server connectivity"""
    print("\nTesting server connectivity...")
    try:
        response = requests.get(f"{SERVER_URL}/ping", timeout=10)
        if response.status_code == 200:
            print("✓ Server is online and responding")
            return True
        else:
            print(f"⚠ Server responded with status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Cannot reach server: {e}")
        return False

def test_video_info():
    """Test video info endpoint to see if Tor is being used"""
    print("\nTesting video info request (this will use Tor if enabled)...")
    try:
        response = requests.get(
            f"{SERVER_URL}/info",
            params={"url": "https://youtu.be/dQw4w9WgXcQ"},
            timeout=60  # Tor can be slow
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✓ Video info request successful")
            print(f"  → Title: {data.get('title', 'N/A')[:50]}...")
            print("  → Check server logs for 'Using Tor network' message")
            return True
        else:
            print(f"✗ Request failed with status {response.status_code}")
            print(f"  → Response: {response.text[:200]}")
            return False
    except requests.exceptions.Timeout:
        print("⚠ Request timed out (Tor can be slow, this might be normal)")
        return None
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    print("=" * 60)
    print("RENDER TOR STATUS CHECK")
    print("=" * 60)
    print(f"Testing: {SERVER_URL}")
    print("=" * 60)
    
    results = {}
    
    # Test 1: Basic connectivity
    results['ping'] = test_ping()
    
    if not results['ping']:
        print("\n" + "=" * 60)
        print("❌ Server is not reachable. Cannot continue tests.")
        print("=" * 60)
        return 1
    
    # Test 2: Tor status
    print("\n")
    results['tor_status'] = test_tor_status()
    
    # Test 3: Actual request
    print("\n")
    results['video_info'] = test_video_info()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, result in results.items():
        if result is True:
            status = "✓ PASS"
        elif result is None:
            status = "⚠ TIMEOUT"
        else:
            status = "✗ FAIL"
        print(f"{test_name.replace('_', ' ').title()}: {status}")
    
    print("=" * 60)
    
    if results.get('tor_status'):
        print("\n✅ TOR IS WORKING ON YOUR RENDER SERVER!")
        print("\nNext steps:")
        print("1. Your server will now bypass IP rate limits")
        print("2. IP rotates automatically every 10 requests")
        print("3. Monitor logs for 'Using Tor network' messages")
        print("4. Expect 3-5x slower speeds (trade-off for avoiding blocks)")
        return 0
    else:
        print("\n❌ TOR IS NOT WORKING")
        print("\nTroubleshooting steps:")
        print("1. Check Render build logs for Tor installation")
        print("2. Verify USE_TOR=True in environment variables")
        print("3. Check start command includes: tor -f /etc/tor/torrc &")
        print("4. Redeploy the service")
        print("\nSee CHECK_TOR_ON_RENDER.md for detailed troubleshooting")
        return 1

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
