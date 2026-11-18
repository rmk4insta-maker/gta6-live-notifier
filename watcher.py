#!/usr/bin/env python3
"""
watcher.py - Fast Stream Monitor for GitHub Actions / Local Execution

Monitors:
  - IShowSpeed: https://www.youtube.com/@IShowSpeed/live (detects '"isLive":true' and extracts watch URL)
  - Kai Cenat:   https://gql.twitch.tv/gql (public GQL query for user stream status)

State:
  Persisted in state.json to track transitions (False -> True and True -> False).
"""

import os
import sys
import json
import re
from pathlib import Path

# Try importing requests; fallback gracefully if not installed
try:
    import requests
except ImportError:
    requests = None

BASE_DIR = Path(__file__).resolve().parent
STATE_FILE = BASE_DIR / "state.json"
ENV_FILE = BASE_DIR / ".env"

# Public Twitch Web Client-ID for GQL queries
TWITCH_CLIENT_ID = "kimne78kx3ncx6brgo4mv6wki5h1ko"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"


def load_env_if_present():
    """Load variables from .env file if present without overriding existing env."""
    for p in [ENV_FILE, BASE_DIR.parent / ".env"]:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip("'\"")
                            if k not in os.environ:
                                os.environ[k] = v
            except Exception:
                pass


def load_state() -> dict:
    """Load streamer state from state.json."""
    default_state = {
        "ishowspeed": {"is_live": False, "last_url": ""},
        "kaicenat": {"is_live": False, "last_url": ""}
    }
    if not STATE_FILE.exists():
        return default_state
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for k in default_state:
                if k not in data:
                    data[k] = default_state[k]
            return data
    except Exception as e:
        print(f"[Watcher] Warning reading state.json: {e}", file=sys.stderr)
        return default_state


def save_state(state: dict):
    """Save updated streamer state to state.json."""
    try:
        tmp_file = BASE_DIR / "state.tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
            f.write("\n")
        tmp_file.replace(STATE_FILE)
    except Exception as e:
        print(f"[Watcher] Error saving state.json: {e}", file=sys.stderr)


def send_telegram_alert(text: str):
    """Send text alert via Telegram Bot API using requests or urllib."""
    load_env_if_present()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

    if not token or not chat_id:
        print(f"[Watcher] Alert generated (Telegram not configured):\n{text}")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": False
    }

    try:
        if requests:
            r = requests.post(url, json=payload, timeout=15)
            r.raise_for_status()
        else:
            import urllib.request
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=15) as res:
                res.read()
        print(f"[Watcher] Telegram alert sent to {chat_id}")
    except Exception as e:
        print(f"[Watcher] Telegram send failed: {e}", file=sys.stderr)


def check_ishowspeed() -> dict:
    """
    Check if IShowSpeed is live on YouTube.
    Looks for '"isLive":true' and extracts the watch?v= URL.
    """
    url = "https://www.youtube.com/@IShowSpeed/live"
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    try:
        html = ""
        final_url = url
        if requests:
            res = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            if res.status_code == 200:
                html = res.text
                final_url = res.url
        else:
            import urllib.request
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as res:
                html = res.read().decode("utf-8", errors="ignore")
                final_url = res.geturl()

        # Check for live marker
        is_live = ('"isLive":true' in html) or ('"liveStreamabilityRenderer"' in html and '"isLive":true' in html)

        # Extract specific watch?v= URL
        watch_url = ""
        if "watch?v=" in final_url:
            watch_url = final_url
        else:
            # Regex search for canonical watch link or videoId
            m_canon = re.search(r'<link rel="canonical" href="(https://www\.youtube\.com/watch\?v=[^"&]+)">', html)
            if m_canon:
                watch_url = m_canon.group(1)
            else:
                m_vid = re.search(r'"videoId":"([a-zA-Z0-9_-]{11})"', html)
                if m_vid:
                    watch_url = f"https://www.youtube.com/watch?v={m_vid.group(1)}"
                else:
                    watch_url = url

        return {"is_live": is_live, "url": watch_url or url}
    except Exception as e:
        print(f"[Watcher] Network error checking IShowSpeed: {e}", file=sys.stderr)
        return {"is_live": False, "url": url}


def check_kaicenat() -> dict:
    """
    Check if Kai Cenat is live on Twitch via public GQL query.
    Query: query { user(login: "kaicenat") { stream { id title } } }
    """
    url = "https://gql.twitch.tv/gql"
    channel_url = "https://www.twitch.tv/kaicenat"
    payload = {
        "query": 'query { user(login: "kaicenat") { stream { id title } } }'
    }
    headers = {
        "Client-Id": TWITCH_CLIENT_ID,
        "User-Agent": USER_AGENT,
        "Content-Type": "application/json"
    }

    try:
        data = None
        if requests:
            res = requests.post(url, json=payload, headers=headers, timeout=15)
            if res.status_code == 200:
                data = res.json()
        else:
            import urllib.request
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
            with urllib.request.urlopen(req, timeout=15) as res:
                data = json.loads(res.read().decode("utf-8"))

        if data:
            user_data = data.get("data", {}).get("user")
            stream = user_data.get("stream") if user_data else None
            is_live = stream is not None and bool(stream.get("id"))
            return {"is_live": is_live, "url": channel_url}

        return {"is_live": False, "url": channel_url}
    except Exception as e:
        print(f"[Watcher] Network error checking Kai Cenat: {e}", file=sys.stderr)
        return {"is_live": False, "url": channel_url}


def main():
    try:
        state = load_state()
        state_changed = False

        targets = [
            ("ishowspeed", "IShowSpeed", check_ishowspeed),
            ("kaicenat", "Kai Cenat", check_kaicenat)
        ]

        for key, name, checker_fn in targets:
            prev_status = state.get(key, {"is_live": False, "last_url": ""})
            prev_live = bool(prev_status.get("is_live", False))
            prev_url = prev_status.get("last_url", "")

            curr = checker_fn()
            curr_live = bool(curr.get("is_live", False))
            curr_url = curr.get("url") or prev_url

            print(f"[Watcher] {name}: Previous={prev_live}, Current={curr_live}")

            # Transition 1: False -> True (Streamer went live)
            if not prev_live and curr_live:
                alert = (
                    f"🔴 LIVE NOW: {name} just started streaming!\n"
                    f"Link: {curr_url}\n"
                    f"Turn on your PC and run /clip {curr_url} in Antigravity."
                )
                send_telegram_alert(alert)
                state[key]["is_live"] = True
                state[key]["last_url"] = curr_url
                state_changed = True

            # Transition 2: True -> False (Stream ended)
            elif prev_live and not curr_live:
                vod_url = prev_url or curr_url
                alert = (
                    f"🏁 STREAM ENDED: {name} finished!\n"
                    f"VOD: {vod_url}\n"
                    f"Run /clip {vod_url} in Antigravity to grab all remaining viral clips."
                )
                send_telegram_alert(alert)
                state[key]["is_live"] = False
                state_changed = True

            # Update URL if currently live and URL updated
            elif curr_live and curr_url and curr_url != prev_url:
                state[key]["last_url"] = curr_url
                state_changed = True

        if state_changed:
            save_state(state)
            print("[Watcher] state.json updated with new statuses.")
        else:
            print("[Watcher] No state change detected.")

    except Exception as e:
        # Wrap all execution in try/except so network blips exit cleanly with code 0
        print(f"[Watcher] Exception caught (exiting cleanly): {e}", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
