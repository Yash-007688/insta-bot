import time
from instagrapi import Client
from instagrapi.exceptions import ClientConnectionError
import requests
import re
import threading
import os
from pathlib import Path
import json
try:
    from dotenv import load_dotenv  # optional
    load_dotenv()
except Exception:
    pass
from getpass import getpass

SECRETS_PATH = "secrets.json"

def load_secrets(path=SECRETS_PATH):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {
                "username": data.get("username"),
                "password": data.get("password"),
                "allowed_ips": data.get("allowed_ips", []),
                "credentials_by_ip": data.get("credentials_by_ip", {}),
            }
    except FileNotFoundError:
        return {"username": None, "password": None, "allowed_ips": [], "credentials_by_ip": {}}

def write_secrets(secrets, path=SECRETS_PATH):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "username": secrets.get("username"),
                    "password": secrets.get("password"),
                    "allowed_ips": secrets.get("allowed_ips", []),
                    "credentials_by_ip": secrets.get("credentials_by_ip", {}),
                },
                f,
                indent=2,
            )
    except Exception as e:
        print(f"Warning: failed to persist secrets: {e}")

def get_public_ip():
    try:
        # Try multiple providers for resilience
        for url in (
            "https://api.ipify.org",
            "https://ifconfig.me/ip",
            "https://ipv4.icanhazip.com",
        ):
            try:
                r = requests.get(url, timeout=5)
                if r.ok:
                    return r.text.strip()
            except Exception:
                continue
    except Exception:
        pass
    return None

def require_allowed_ip(secrets):
    ip = get_public_ip()
    if not ip:
        print("Could not determine public IP; blocking run for safety.")
        raise SystemExit(1)
    allowed_ips = secrets.get("allowed_ips", []) or []
    if not allowed_ips:
        # Auto-authorize first detected IP
        secrets["allowed_ips"] = [ip]
        write_secrets(secrets)
        print(f"Auto-authorized current IP {ip} (saved to secrets).")
        return True
    if ip not in set(allowed_ips):
        # Auto-append current IP and allow
        allowed_ips.append(ip)
        secrets["allowed_ips"] = allowed_ips
        write_secrets(secrets)
        print(f"Added new IP {ip} to allowed list (saved to secrets).")
        return True
    return True

# Login (secured via secrets.json, optional .env, or environment variables)
secrets = load_secrets()
require_allowed_ip(secrets)
current_ip = get_public_ip()
username_env = os.environ.get("IG_USERNAME")
password_env = os.environ.get("IG_PASSWORD")

# If ENV creds are missing, interactively prompt and persist to .env
if not username_env or not password_env:
    print("Instagram credentials not found in environment. Please enter them now.")
    entered_user = input("IG_USERNAME: ").strip()
    entered_pass = getpass("IG_PASSWORD: ")
    if not entered_user or not entered_pass:
        print("Credentials are required to start the session.")
        raise SystemExit(1)
    # Persist to .env
    try:
        env_path = Path(".env")
        existing = ""
        if env_path.exists():
            existing = env_path.read_text(encoding="utf-8")
        # Remove existing keys if present
        lines = [ln for ln in existing.splitlines() if not ln.startswith("IG_USERNAME=") and not ln.startswith("IG_PASSWORD=")]
        lines.append(f"IG_USERNAME={entered_user}")
        lines.append(f"IG_PASSWORD={entered_pass}")
        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        # Reload env for current process
        try:
            load_dotenv(override=True)
        except Exception:
            pass
        username_env = entered_user
        password_env = entered_pass
        print("Saved credentials to .env")
    except Exception as e:
        print(f"Warning: failed to write .env ({e}). Proceeding without saving.")
        username_env = entered_user
        password_env = entered_pass

# Resolve credentials precedence:
# 1) Environment (.env or OS env)
# 2) Per-IP credentials in secrets
# 3) Global credentials in secrets
creds_by_ip = secrets.get("credentials_by_ip", {}) or {}
ip_creds = creds_by_ip.get(current_ip or "", {}) if current_ip else {}
username = username_env or ip_creds.get("username") or secrets.get("username")
password = password_env or ip_creds.get("password") or secrets.get("password")

if username_env and password_env and current_ip:
    # Remember env credentials for this IP so future runs work without env
    if current_ip not in creds_by_ip:
        creds_by_ip[current_ip] = {"username": username_env, "password": password_env}
        secrets["credentials_by_ip"] = creds_by_ip
        write_secrets(secrets)

if not username or not password:
    print("Missing credentials. Provide .env (IG_USERNAME/IG_PASSWORD) or secrets.json.")
    raise SystemExit(1)
cl = Client()
cl.login(username, password)

# Track last seen message IDs
seen_messages = set()
# Control whether to print DMs continuously
PRINT_DMS = False
# Control whether to resolve user_id -> username via network (may block)
RESOLVE_USERNAMES = False

def safe_username(api_client, user_id):
    if not RESOLVE_USERNAMES:
        return str(user_id)
    try:
        # Prefer private API to avoid public GraphQL 'data' KeyError
        return api_client.user_info_v1(user_id).username
    except Exception:
        return str(user_id)

def get_user_id_from_username(api_client, username):
    uname = username.lstrip("@")
    # Prefer private search to avoid public GQL paths
    try:
        users = api_client.search_users(uname)
        if users:
            exact = next((u for u in users if getattr(u, "username", "").lower() == uname.lower()), None)
            cand = exact or users[0]
            user_pk = getattr(cand, "pk", None) or getattr(cand, "id", None)
            if user_pk:
                return user_pk
    except Exception:
        pass
    # Fallback to library method if available
    try:
        return api_client.user_id_from_username(uname)
    except Exception as e:
        raise e

def process_queue_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            usernames = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []
    # Clear file after reading
    try:
        open(path, "w").close()
    except Exception:
        pass
    return usernames

def process_follow_queue(api_client):
    usernames = process_queue_file("follow_queue.txt")
    for uname in usernames:
        try:
            user_id = get_user_id_from_username(api_client, uname)
            api_client.user_follow(user_id)
            print(f"Followed: {uname}")
        except Exception as e:
            print(f"Follow failed for {uname}: {e}")

def process_unfollow_queue(api_client):
    usernames = process_queue_file("unfollow_queue.txt")
    for uname in usernames:
        try:
            user_id = get_user_id_from_username(api_client, uname)
            api_client.user_unfollow(user_id)
            print(f"Unfollowed: {uname}")
        except Exception as e:
            print(f"Unfollow failed for {uname}: {e}")

def process_like_queue(api_client):
    urls = process_queue_file("like_queue.txt")
    for url in urls:
        try:
            media_id = api_client.media_id_from_url(url)
            api_client.media_like(media_id)
            print(f"Liked: {url}")
        except Exception as e:
            print(f"Like failed for {url}: {e}")

def process_comment_queue(api_client):
    # Each line: <url>|<comment text>
    try:
        with open("comment_queue.txt", "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        open("comment_queue.txt", "w").close()
    except FileNotFoundError:
        lines = []
    for line in lines:
        try:
            if "|" not in line:
                print(f"Skip invalid comment line: {line}")
                continue
            url, text = line.split("|", 1)
            media_id = api_client.media_id_from_url(url)
            api_client.media_comment(media_id, text)
            print(f"Commented on {url}: {text}")
        except Exception as e:
            print(f"Comment failed for line '{line}': {e}")

def process_post_queue(api_client):
    # Each line: <path>|<caption>|<type>
    # type: photo | reel | video (default photo if missing)
    try:
        with open("post_queue.txt", "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        open("post_queue.txt", "w").close()
    except FileNotFoundError:
        lines = []
    for line in lines:
        try:
            parts = line.split("|")
            if len(parts) < 1:
                continue
            path = parts[0]
            caption = parts[1] if len(parts) > 1 else ""
            post_type = parts[2].lower() if len(parts) > 2 else "photo"
            if post_type == "photo":
                api_client.photo_upload(path, caption)
                print(f"Posted photo: {path}")
            elif post_type == "reel":
                # Reels
                api_client.clip_upload(path, caption)
                print(f"Posted reel: {path}")
            elif post_type == "video":
                api_client.video_upload(path, caption)
                print(f"Posted video: {path}")
            else:
                print(f"Unknown post type '{post_type}' for line: {line}")
        except Exception as e:
            print(f"Post failed for line '{line}': {e}")

def like_latest_reel(api_client, username):
    try:
        uname = username.lstrip("@")
        user_id = get_user_id_from_username(api_client, uname)
        if not user_id:
            print(f"Could not resolve user: @{uname}")
            return
        medias = []
        # Try user_clips first
        try:
            medias = api_client.user_clips(user_id, amount=18) or []
        except Exception:
            medias = []
        # Fallback: filter from user_medias
        if not medias:
            try:
                all_medias = api_client.user_medias(user_id, amount=24) or []
                medias = [m for m in all_medias if str(getattr(m, "product_type", "")).lower() in ("clips", "reel", "clips_together")]
            except Exception:
                medias = []
        if not medias:
            print(f"No reels available (private account or none posted) for @{uname}")
            return
        latest = sorted(medias, key=lambda m: getattr(m, "taken_at", None) or 0, reverse=True)[0]
        api_client.media_like(latest.id)
        print(f"Liked latest reel of @{uname}")
    except Exception as e:
        print(f"Like latest reel failed for @{username}: {e}")

def like_latest_post(api_client, username):
    try:
        uname = username.lstrip("@")
        user_id = get_user_id_from_username(api_client, uname)
        if not user_id:
            print(f"Could not resolve user: @{uname}")
            return
        medias = []
        try:
            medias = api_client.user_medias(user_id, amount=30) or []
        except Exception:
            medias = []
        # Exclude reels/igtv
        medias = [m for m in medias if str(getattr(m, "product_type", "")).lower() not in ("clips", "igtv")]
        if not medias:
            print(f"No standard posts available (private account or none posted) for @{uname}")
            return
        latest = sorted(medias, key=lambda m: getattr(m, "taken_at", None) or 0, reverse=True)[0]
        api_client.media_like(latest.id)
        print(f"Liked latest post of @{uname}")
    except Exception as e:
        print(f"Like latest post failed for @{username}: {e}")

def try_parse_and_execute_commands(api_client, text):
    global PRINT_DMS, RESOLVE_USERNAMES
    if not text:
        return False
    t = text.strip()
    m = re.search(r"like\s+(?:the\s+)?latest\s+reel\s+of\s+@([A-Za-z0-9._]+)", t, flags=re.IGNORECASE)
    if m:
        like_latest_reel(api_client, m.group(1))
        return True
    m = re.search(r"like\s+(?:the\s+)?latest\s+post\s+of\s+@([A-Za-z0-9._]+)", t, flags=re.IGNORECASE)
    if m:
        like_latest_post(api_client, m.group(1))
        return True
    m = re.search(r"^follow\s+@([A-Za-z0-9._]+)$", t, flags=re.IGNORECASE)
    if m:
        uname = m.group(1)
        try:
            user_id = api_client.user_id_from_username(uname)
            api_client.user_follow(user_id)
            print(f"Followed: {uname}")
        except Exception as e:
            print(f"Follow failed for {uname}: {e}")
        return True
    m = re.search(r"^unfollow\s+@([A-Za-z0-9._]+)$", t, flags=re.IGNORECASE)
    if m:
        uname = m.group(1)
        try:
            user_id = api_client.user_id_from_username(uname)
            api_client.user_unfollow(user_id)
            print(f"Unfollowed: {uname}")
        except Exception as e:
            print(f"Unfollow failed for {uname}: {e}")
        return True
    m = re.search(r"(?:write|send)\s+(.+?)\s+to\s+@([A-Za-z0-9._]+)$", t, flags=re.IGNORECASE)
    if m:
        dm_text = m.group(1).strip()
        uname = m.group(2).strip()
        send_dm_to_username(api_client, uname, dm_text)
        return True
    m = re.search(r"download\s+(?:story|stories)\s+of\s+@([A-Za-z0-9._]+)$", t, flags=re.IGNORECASE)
    if m:
        download_stories_of_username(api_client, m.group(1))
        return True
    m = re.search(r"download\s+(?:latest\s+)?reel\s+of\s+@([A-Za-z0-9._]+)$", t, flags=re.IGNORECASE)
    if m:
        download_latest_reel_of_username(api_client, m.group(1))
        return True
    m = re.search(r"download\s+(?:latest\s+)?post\s+of\s+@([A-Za-z0-9._]+)$", t, flags=re.IGNORECASE)
    if m:
        download_latest_post_of_username(api_client, m.group(1))
        return True
    m = re.search(r"status\s+of\s+@([A-Za-z0-9._]+)$", t, flags=re.IGNORECASE)
    if m:
        print_user_status(api_client, m.group(1))
        return True
    m = re.search(r"^show\s+dms?(?:\s+(\d+))?$", t, flags=re.IGNORECASE)
    if m:
        count = int(m.group(1)) if m.group(1) else 5
        show_recent_dms(api_client, max(1, min(count, 20)))
        return True
    if t.lower() == "show live dms":
        PRINT_DMS = True
        print("Live DM printing enabled.")
        return True
    if t.lower() == "hide live dms":
        PRINT_DMS = False
        print("Live DM printing disabled.")
        return True
    if t.lower() == "resolve usernames on":
        RESOLVE_USERNAMES = True
        print("Username resolution enabled.")
        return True
    if t.lower() == "resolve usernames off":
        RESOLVE_USERNAMES = False
        print("Username resolution disabled.")
        return True
    return False

def send_dm_to_username(api_client, username, message_text):
    try:
        uname = username.lstrip("@")
        user_id = get_user_id_from_username(api_client, uname)
        api_client.direct_send(message_text, [user_id])
        print(f"DM sent to {uname}: {message_text}")
    except Exception as e:
        print(f"DM failed to {username}: {e}")

def _command_session_loop(api_client):
    print("Command session started. Type commands or 'help'/'exit'.")
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nCommand session closed.")
            return
        if not line:
            continue
        if line.lower() in ("exit", "quit"):
            print("Exiting command session (bot continues running).")
            return
        if line.lower() in ("help", "h", "?"):
            print(
                "Commands: follow <username> | unfollow <username> | "
                "like the latest reel of <username> | "
                "write <message> to <username>"
            )
            continue
        handled = try_parse_and_execute_commands(api_client, line)
        if not handled:
            print("Unknown command. Type 'help' for options.")

def start_command_session(api_client):
    t = threading.Thread(target=_command_session_loop, args=(api_client,), daemon=True)
    t.start()

def download_stories_of_username(api_client, username):
    try:
        uname = username.lstrip("@")
        user_id = get_user_id_from_username(api_client, uname)
        stories = api_client.user_stories(user_id)
        if not stories:
            print(f"No active stories for {uname}")
            return
        out_dir = Path("downloads") / "stories" / uname
        out_dir.mkdir(parents=True, exist_ok=True)
        downloaded = 0
        for story in stories:
            try:
                api_client.story_download(story.id, filename=str(out_dir))
                downloaded += 1
            except Exception as e:
                print(f"Failed to download a story for {uname}: {e}")
        print(f"Downloaded {downloaded} stories for {uname} into {out_dir}")
    except Exception as e:
        print(f"Download stories failed for {username}: {e}")

def download_latest_reel_of_username(api_client, username):
    try:
        uname = username.lstrip("@")
        user_id = get_user_id_from_username(api_client, uname)
        try:
            medias = api_client.user_clips(user_id, amount=10)
        except Exception:
            medias = api_client.user_medias(user_id, amount=15)
            medias = [m for m in medias if getattr(m, "product_type", "").lower() == "clips"]
        if not medias:
            print(f"No reels found for {uname}")
            return
        latest = sorted(medias, key=lambda m: getattr(m, "taken_at", None) or 0, reverse=True)[0]
        out_dir = Path("downloads") / "reels" / uname
        out_dir.mkdir(parents=True, exist_ok=True)
        api_client.clip_download(latest.id, filename=str(out_dir))
        print(f"Downloaded latest reel of {uname} into {out_dir}")
    except Exception as e:
        print(f"Download latest reel failed for {username}: {e}")

def download_latest_post_of_username(api_client, username):
    try:
        uname = username.lstrip("@")
        user_id = get_user_id_from_username(api_client, uname)
        medias = api_client.user_medias(user_id, amount=15)
        medias = [m for m in medias if getattr(m, "product_type", "").lower() not in ("clips", "igtv")]
        if not medias:
            print(f"No posts found for {uname}")
            return
        latest = sorted(medias, key=lambda m: getattr(m, "taken_at", None) or 0, reverse=True)[0]
        out_dir = Path("downloads") / "posts" / uname
        out_dir.mkdir(parents=True, exist_ok=True)
        # Choose download based on media type
        try:
            api_client.photo_download(latest.id, filename=str(out_dir))
        except Exception:
            api_client.media_download(latest.id, filename=str(out_dir))
        print(f"Downloaded latest post of {uname} into {out_dir}")
    except Exception as e:
        print(f"Download latest post failed for {username}: {e}")

def print_user_status(api_client, username):
    try:
        uname = username.lstrip("@")
        user_id = api_client.user_id_from_username(uname)
        try:
            activity = api_client.user_last_activity(user_id)
        except Exception:
            activity = None
        if activity and getattr(activity, "timestamp", None):
            ts = activity.timestamp
            delta = max(0, int((time.time() - ts.timestamp()) // 60))
            print(f"{uname} was last active {delta} minutes ago")
        else:
            # Try direct presence as fallback
            try:
                presence = api_client.direct_presence(user_id)
                is_active = bool(getattr(presence, "is_active", False))
                if is_active:
                    print(f"{uname} is online now")
                else:
                    print(f"{uname} is offline (last seen unknown)")
            except Exception:
                print(f"Status unknown for {uname}")
    except Exception as e:
        print(f"Status check failed for {username}: {e}")

def show_recent_dms(api_client, threads_amount=5):
    try:
        inbox = api_client.direct_threads(amount=threads_amount)
    except (ClientConnectionError, requests.exceptions.RequestException) as e:
        print(f"Show DM error: {e}")
        return
    for thread in inbox:
        try:
            for message in getattr(thread, "messages", []) or []:
                try:
                    user_id = getattr(message, "user_id", None)
                    sender = safe_username(api_client, user_id) if user_id else "?"
                    ts = getattr(message, "timestamp", None)
                    timestamp = ts.strftime("%Y-%m-%d %H:%M:%S") if ts else ""
                    text = getattr(message, "text", None)
                    print(f"[{timestamp}] {sender}: {text}")
                except Exception as inner_e:
                    print(f"Skip malformed message: {inner_e}")
        except Exception as e:
            print(f"Error reading a thread: {e}")

start_command_session(cl)

while True:
    try:
    inbox = cl.direct_threads(amount=5)  # fetch recent 5 threads
    except (ClientConnectionError, requests.exceptions.RequestException) as e:
        print(f"Inbox fetch error: {e}")
        time.sleep(30)
        continue
    
    for thread in inbox:
        for message in thread.messages:
            if message.id not in seen_messages:
                sender = safe_username(cl, message.user_id)
                timestamp = (
                    message.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    if getattr(message, "timestamp", None)
                    else ""
                )
                text = getattr(message, "text", None)
                if PRINT_DMS:
                    print(f"[{timestamp}] {sender}: {text}")
                try_parse_and_execute_commands(cl, text)
                
                # mark as seen
                seen_messages.add(message.id)
    
    # Process follow / unfollow queues each cycle
    process_follow_queue(cl)
    process_unfollow_queue(cl)
    process_like_queue(cl)
    process_comment_queue(cl)
    process_post_queue(cl)
    
    time.sleep(30)  # check every 30 sec
