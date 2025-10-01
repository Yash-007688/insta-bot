## Instagram Automation Bot

This script uses `instagrapi` to automate common Instagram actions and to react to commands sent via DMs or typed directly in an interactive terminal session.

### Requirements
- Python 3.11+ (tested with 3.13)
- pip packages: `instagrapi`, `requests`, `python-dotenv` (optional)

Install:
```bash
pip install instagrapi requests python-dotenv
```

### Configure
Create `secrets.json` (not tracked) from the template (you can also use a `.env` file):
```json
{
  "username": "your_username_here",
  "password": "your_password_here",
  "allowed_ips": ["1.2.3.4"],
  "credentials_by_ip": {
    "1.2.3.4": {"username": "u", "password": "p"}
  }
}
```
Notes:
- `secrets.json` is ignored by git via `.gitignore`.
- Optionally set environment variables `IG_USERNAME` and `IG_PASSWORD` (e.g., in a `.env` file). The app will remember env credentials per-IP into `secrets.json` automatically.
- If `allowed_ips` is empty, your current IP is auto-authorized and saved. New IPs you run from are also auto-added.

### Run
```bash
python insta.py
```
On first run, if `IG_USERNAME` / `IG_PASSWORD` are missing, the app will prompt you to enter them and will save them into `.env` automatically.
The bot will:
- Start polling your DMs every 30 seconds
- Start an interactive command session in the terminal (type `help`)

### Interactive Commands (type these in the terminal session)
All commands now require an `@username`.
- follow @<username>
- unfollow @<username>
- like the latest reel of @<username>
- like the latest post of @<username>
- write <message> to @<username>
- show dm
- show dms <n>
- show live dms (toggle on)
- hide live dms (toggle off)
- download stories of @<username>
- download latest reel of @<username>
- download latest post of @<username>
- status of @<username>

Notes:
- `@username` is required in all commands (e.g., `@seedhamaut`).
- Type `help` to reprint available commands. Type `exit` to close the input session (the bot continues running).
- DMs are not printed continuously by default. Use `show live dms` to enable stream; use `hide live dms` to disable.
- Username resolution (showing names instead of numeric IDs) is OFF by default to avoid network blocking. Toggle with:
  - `resolve usernames on`
  - `resolve usernames off`

### DM Commands (send to your own account)
You can issue the same commands via DM text to your own account. Examples:
- like the latest reel of @seedhamaut
- like the latest post of @seedhamaut
- write hello to @vansh
- follow @someuser
- unfollow @someuser
- download stories of @someuser
- download latest reel of @someuser
- download latest post of @someuser
- status of @someuser

### Queue Files (optional batch actions)
Create these text files in the same folder; the bot will read and clear them each loop:
- follow_queue.txt — one username per line to follow
- unfollow_queue.txt — one username per line to unfollow
- like_queue.txt — one media URL per line to like
- comment_queue.txt — each line: `<url>|<comment text>`
- post_queue.txt — each line: `<file_path>|<caption>|<type>` where `<type>` is `photo`, `reel`, or `video` (default `photo`)

### Downloads
- Stories saved to `downloads/stories/<username>/`
- Latest reel: `downloads/reels/<username>/`
- Latest post: `downloads/posts/<username>/`

### Troubleshooting
- DNS/Network errors like `Failed to resolve 'i.instagram.com'`:
  - Switch network (Wi‑Fi/mobile hotspot/VPN)
  - Set DNS to `1.1.1.1` or `8.8.8.8`
  - Ensure system date/time is correct
  - Check firewall is not blocking Python
- Login challenges or 2FA: complete verification in the Instagram app and rerun.

### Safety & Limits
- Instagram rate limits and anti‑abuse systems may block frequent actions. Space out bulk operations.
- Use your own account at your own risk.


