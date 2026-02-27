#!/usr/bin/env python3
"""
Test script to verify Tor connection is working properly
Run this after deploying to Render to verify Tor setup
"""

import requests
import time
import sys

TOR_PROXY = {
    'http': 'socks5://127.0.0.1:9050',
    'https': 'socks5://127.0.0.1:9050'
}

def test_tor_connection():
    """Test if Tor is running and accessible"""
    print("Testing Tor connection...")
    try:
        response = requests.get(
            'https://check.torproject.org/api/ip',
            proxies=TOR_PROXY,
            timeout=30
        )
        data = response.json()
        
        if data.get('IsTor'):
            print(f"✓ Tor is working! Exit IP: {data.get('IP')}")
            return True
        else:
            print(f"✗ Connected but not through Tor. IP: {data.get('IP')}")
            return False
    except Exception as e:
        print(f"✗ Tor connection failed: {e}")
        return False

def test_ip_rotation():
    """Test if Tor circuit renewal changes IP"""
    print("\nTesting IP rotation...")
    
    try:
        # Get first IP
        response1 = requests.get(
            'https://api.ipify.org?format=json',
            proxies=TOR_PROXY,
            timeout=30
        )
        ip1 = response1.json()['ip']
        print(f"First IP: {ip1}")
        
        # Renew circuit (requires stem library and control port access)
        try:
            from stem import Signal
            from stem.control import Controller
            
            print("Renewing Tor circuit...")
            with Controller.from_port(port=9051) as controller:
                controller.authenticate()
                controller.signal(Signal.NEWNYM)
            
            time.sleep(5)  # Wait for new circuit
            
            # Get second IP
            response2 = requests.get(
                'https://api.ipify.org?format=json',
                proxies=TOR_PROXY,
                timeout=30
            )
            ip2 = response2.json()['ip']
            print(f"Second IP: {ip2}")
            
            if ip1 != ip2:
                print("✓ IP rotation working!")
                return True
            else:
                print("✗ IP didn't change (may need more time)")
                return False
                
        except ImportError:
            print("⚠ stem library not available, skipping circuit renewal test")
            return None
        except Exception as e:
            print(f"⚠ Circuit renewal failed: {e}")
            return None
            
    except Exception as e:
        print(f"✗ IP rotation test failed: {e}")
        return False

def test_youtube_access():
    """Test if YouTube is accessible through Tor"""
    print("\nTesting YouTube access through Tor...")
    
    try:
        response = requests.get(
            'https://www.youtube.com',
            proxies=TOR_PROXY,
            timeout=30,
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        
        if response.status_code == 200:
            print(f"✓ YouTube accessible (Status: {response.status_code})")
            return True
        else:
            print(f"⚠ YouTube returned status: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ YouTube access failed: {e}")
        return False

def test_direct_connection():
    """Test direct connection (without Tor) for comparison"""
    print("\nTesting direct connection (no Tor)...")
    
    try:
        response = requests.get(
            'https://api.ipify.org?format=json',
            timeout=10
        )
        ip = response.json()['ip']
        print(f"Direct connection IP: {ip}")
        return True
    except Exception as e:
        print(f"✗ Direct connection failed: {e}")
        return False

def main():
    print("=" * 60)
    print("Tor Connection Test Suite")
    print("=" * 60)
    
    results = {
        'tor_connection': test_tor_connection(),
        'direct_connection': test_direct_connection(),
        'ip_rotation': test_ip_rotation(),
        'youtube_access': test_youtube_access()
    }
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else ("⚠ SKIP" if result is None else "✗ FAIL")
        print(f"{test_name.replace('_', ' ').title()}: {status}")
    
    # Overall status
    critical_tests = ['tor_connection', 'youtube_access']
    all_critical_passed = all(results.get(t) for t in critical_tests)
    
    print("\n" + "=" * 60)
    if all_critical_passed:
        print("✓ All critical tests passed! Tor is ready to use.")
        return 0
    else:
        print("✗ Some critical tests failed. Check configuration.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
