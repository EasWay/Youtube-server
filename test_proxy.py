#!/usr/bin/env python3
"""
Test script to verify proxy configuration and functionality
"""

import os
import sys
from pytubefix import YouTube
from utils import get_proxies, create_youtube_with_retry
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_proxy_parsing():
    """Test that proxies are parsed correctly from environment"""
    print("\n=== Testing Proxy Parsing ===")
    proxies = get_proxies()
    
    if not proxies:
        print("❌ No proxies configured")
        print("   Set PROXIES environment variable")
        print("   Example: export PROXIES=http://proxy1.com:8080,http://proxy2.com:8080")
        return False
    
    print(f"✓ Found {len(proxies)} proxy(ies)")
    for i, proxy in enumerate(proxies, 1):
        print(f"  {i}. {proxy['server']}")
        if 'username' in proxy and proxy['username']:
            print(f"     Auth: {proxy['username']}:***")
    
    return True

def test_youtube_connection(test_url="https://youtu.be/dQw4w9WgXcQ"):
    """Test YouTube connection with proxy rotation"""
    print(f"\n=== Testing YouTube Connection ===")
    print(f"Test URL: {test_url}")
    
    try:
        yt = create_youtube_with_retry(test_url, max_retries=3)
        print(f"✓ Successfully connected!")
        print(f"  Title: {yt.title}")
        print(f"  Author: {yt.author}")
        print(f"  Length: {yt.length}s")
        print(f"  Views: {yt.views:,}")
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def test_multiple_requests():
    """Test multiple requests to verify rotation"""
    print("\n=== Testing Multiple Requests ===")
    
    test_urls = [
        "https://youtu.be/dQw4w9WgXcQ",
        "https://youtu.be/jNQXAC9IVRw",
        "https://youtu.be/9bZkp7q19f0"
    ]
    
    success_count = 0
    for i, url in enumerate(test_urls, 1):
        print(f"\nRequest {i}/3: {url}")
        try:
            yt = create_youtube_with_retry(url, max_retries=2)
            print(f"  ✓ {yt.title}")
            success_count += 1
        except Exception as e:
            print(f"  ❌ Failed: {e}")
    
    print(f"\n{success_count}/{len(test_urls)} requests succeeded")
    return success_count == len(test_urls)

def main():
    """Run all tests"""
    print("=" * 60)
    print("YouTube Server Proxy Test Suite")
    print("=" * 60)
    
    # Check AUTH setting
    auth = os.environ.get("AUTH", "False") == "True"
    print(f"\nAUTH: {auth}")
    
    if not auth:
        print("\n⚠️  WARNING: AUTH=False")
        print("   Proxies only work when AUTH=True")
        print("   Set: export AUTH=True")
        return 1
    
    # Run tests
    results = []
    
    # Test 1: Proxy parsing
    results.append(("Proxy Parsing", test_proxy_parsing()))
    
    # Test 2: Single connection
    if results[0][1]:  # Only if proxies are configured
        results.append(("YouTube Connection", test_youtube_connection()))
    
    # Test 3: Multiple requests (optional)
    if len(sys.argv) > 1 and sys.argv[1] == "--full":
        if results[-1][1]:  # Only if connection works
            results.append(("Multiple Requests", test_multiple_requests()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed. Check configuration.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
