"""
YouTube OAuth Token Extractor
This script helps you obtain the necessary tokens for YouTube authentication.
"""

import json
import os

def extract_tokens_from_browser():
    """
    Instructions to manually extract tokens from your browser.
    """
    print("=" * 60)
    print("YouTube OAuth Token Extraction Guide")
    print("=" * 60)
    print("\nMethod 1: Extract from Browser Cookies")
    print("-" * 60)
    print("1. Open YouTube (youtube.com) in your browser while logged in")
    print("2. Press F12 to open Developer Tools")
    print("3. Go to 'Application' tab (Chrome) or 'Storage' tab (Firefox)")
    print("4. Click on 'Cookies' → 'https://www.youtube.com'")
    print("5. Look for these cookies and copy their values:")
    print("   - VISITOR_INFO1_LIVE (this is your VISITOR_DATA)")
    print("   - __Secure-1PSID or SAPISID")
    print("\n6. For PO_TOKEN:")
    print("   - Go to 'Network' tab in DevTools")
    print("   - Play any video on YouTube")
    print("   - Look for requests to 'player' endpoint")
    print("   - Check request headers for 'X-Goog-Visitor-Id' and 'X-Goog-Po-Token'")
    print("\n" + "=" * 60)
    print("\nMethod 2: Use pytubefix OAuth Flow")
    print("-" * 60)
    print("Run this command to start OAuth flow:")
    print("  python -c \"from pytubefix import YouTube; yt = YouTube('https://youtube.com/watch?v=dQw4w9WgXcQ', use_oauth=True, allow_oauth_cache=True); print('OAuth completed!')\"")
    print("\nThis will:")
    print("1. Open a browser window for you to log in")
    print("2. Save tokens to a cache file")
    print("3. You can then copy tokens from the cache file")
    print("\n" + "=" * 60)

def save_tokens_to_env():
    """
    Interactive prompt to save tokens to a .env file
    """
    print("\n\nToken Input")
    print("=" * 60)
    print("Enter your tokens (press Enter to skip):\n")
    
    access_token = input("ACCESS_TOKEN: ").strip()
    refresh_token = input("REFRESH_TOKEN: ").strip()
    expires = input("EXPIRES (timestamp): ").strip()
    visitor_data = input("VISITOR_DATA: ").strip()
    po_token = input("PO_TOKEN: ").strip()
    
    if not any([access_token, refresh_token, visitor_data, po_token]):
        print("\nNo tokens entered. Exiting.")
        return
    
    env_content = "# YouTube Authentication Tokens\n"
    env_content += "AUTH=True\n"
    if access_token:
        env_content += f"ACCESS_TOKEN={access_token}\n"
    if refresh_token:
        env_content += f"REFRESH_TOKEN={refresh_token}\n"
    if expires:
        env_content += f"EXPIRES={expires}\n"
    if visitor_data:
        env_content += f"VISITOR_DATA={visitor_data}\n"
    if po_token:
        env_content += f"PO_TOKEN={po_token}\n"
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("\n✓ Tokens saved to .env file")
    print("You can now load these with python-dotenv or set them as environment variables")
    print("\nTo use them, run:")
    print("  set AUTH=True  (Windows)")
    print("  export AUTH=True  (Linux/Mac)")

def check_pytubefix_cache():
    """
    Check if pytubefix has cached OAuth tokens
    """
    cache_paths = [
        os.path.expanduser("~/.pytubefix/tokens.json"),
        os.path.expanduser("~/.cache/pytubefix/tokens.json"),
        "tokens.json",
        "auth/temp.json"
    ]
    
    print("\n\nChecking for cached tokens...")
    print("=" * 60)
    
    for path in cache_paths:
        if os.path.exists(path):
            print(f"\n✓ Found token file: {path}")
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                print("\nToken contents:")
                for key, value in data.items():
                    if value:
                        print(f"  {key}: {value[:20]}..." if len(str(value)) > 20 else f"  {key}: {value}")
                return
            except Exception as e:
                print(f"  Error reading file: {e}")
    
    print("\n✗ No cached token files found")

if __name__ == "__main__":
    print("\n")
    extract_tokens_from_browser()
    check_pytubefix_cache()
    
    print("\n\nWould you like to enter tokens now? (y/n): ", end="")
    choice = input().strip().lower()
    
    if choice == 'y':
        save_tokens_to_env()
    else:
        print("\nYou can run this script again anytime to enter tokens.")
        print("Or manually set environment variables as shown above.")
