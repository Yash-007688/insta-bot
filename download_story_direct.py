import requests
import re
import os
from datetime import datetime

def download_instagram_story(username):
    """
    Attempt to download Instagram story without login
    Note: This may not work for private accounts or if Instagram blocks the request
    """
    try:
        # Create download directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        download_dir = f"downloads/stories/direct_{timestamp}"
        os.makedirs(download_dir, exist_ok=True)
        
        print(f"Attempting to download stories from @{username}")
        print("Note: This method may not work due to Instagram's restrictions")
        
        # Try to get story URL (this is a simplified approach)
        # In reality, Instagram stories require authentication to access
        print("Unable to download story directly without authentication")
        print("Please use the main bot with proper login credentials")
        
        return False
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    username = "kuldeepb_01"
    download_instagram_story(username)