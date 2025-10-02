#!/usr/bin/env python3
"""
Demo script to show the Instagram bot folder structure and commands
without requiring Instagram login.
"""

import os
from pathlib import Path

def create_demo_structure():
    """Create demo download folder structure"""
    base_path = Path("downloads")
    
    # Demo user info
    demo_user = "thecodedevpro_192_168_1_100"
    target_users = ["seedhamaut", "someuser", "testuser"]
    
    for content_type in ["stories", "posts", "reels"]:
        for target in target_users:
            folder_path = base_path / content_type / demo_user / target
            folder_path.mkdir(parents=True, exist_ok=True)
            
            # Create demo files
            demo_file = folder_path / f"demo_{content_type}.txt"
            demo_file.write_text(f"Demo {content_type} from @{target}\nDownloaded by: {demo_user}")
    
    print("✅ Demo folder structure created!")
    print("\nFolder structure:")
    print("downloads/")
    for content_type in ["stories", "posts", "reels"]:
        print(f"├── {content_type}/")
        print(f"│   └── {demo_user}/")
        for target in target_users:
            print(f"│       ├── {target}/")
    print()

def show_commands():
    """Show available bot commands"""
    print("🤖 Instagram Bot Commands:")
    print("=" * 50)
    print("Interactive Commands:")
    print("• follow @username")
    print("• unfollow @username") 
    print("• like the latest reel of @username")
    print("• like the latest post of @username")
    print("• write <message> to @username")
    print("• download stories of @username")
    print("• download latest reel of @username")
    print("• download latest post of @username")
    print("• status of @username")
    print("• show dm / show dms 10")
    print("• show live dms / hide live dms")
    print("• resolve usernames on/off")
    print()
    print("Queue Files (batch operations):")
    print("• follow_queue.txt - usernames to follow")
    print("• unfollow_queue.txt - usernames to unfollow")
    print("• like_queue.txt - URLs to like")
    print("• comment_queue.txt - URL|comment pairs")
    print("• post_queue.txt - path|caption|type")
    print()

if __name__ == "__main__":
    print("🎯 Instagram Bot Demo Mode")
    print("=" * 40)
    create_demo_structure()
    show_commands()
    print("💡 To run the actual bot:")
    print("1. Fix Instagram login (VPN/different network)")
    print("2. Run: python insta.py")
