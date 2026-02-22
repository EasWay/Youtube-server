"""
Quick OAuth setup using pytubefix
This will open a browser for you to authenticate with YouTube
"""

try:
    from pytubefix import YouTube
    
    print("Starting YouTube OAuth flow...")
    print("A browser window will open for you to log in to YouTube.")
    print("After logging in, the tokens will be cached automatically.\n")
    
    # This will trigger the OAuth flow
    yt = YouTube(
        'https://youtube.com/watch?v=dQw4w9WgXcQ',
        use_oauth=True,
        allow_oauth_cache=True,
        token_file='auth/temp.json'
    )
    
    print(f"✓ OAuth completed successfully!")
    print(f"✓ Video title: {yt.title}")
    print(f"\nTokens have been saved to: auth/temp.json")
    print("Your app will automatically use these tokens when AUTH=True")
    
except ImportError:
    print("Error: pytubefix is not installed")
    print("Install it with: pip install pytubefix")
except Exception as e:
    print(f"Error during OAuth: {e}")
    print("\nTry the manual method using get_youtube_tokens.py instead")
