#!/usr/bin/env python3
"""
Get a ZoomInfo access token directly using Client ID, Client Secret, and Refresh Token.

Use this so you don't have to generate tokens manually in the Developer Portal.
You need a refresh token once (see README: run oauth_capture_refresh_token.py),
then set ZOOMINFO_REFRESH_TOKEN in .env. After that, run this script to get
a new access token; it will update .env with the new token and the new refresh token.
"""

import base64
import os
import sys
from pathlib import Path

import requests

# Load .env
env_path = Path(__file__).resolve().parent / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)

TOKEN_URL = "https://okta-login.zoominfo.com/oauth2/default/v1/token"

CLIENT_ID = os.getenv("ZOOMINFO_CLIENT_ID", "").strip()
CLIENT_SECRET = os.getenv("ZOOMINFO_CLIENT_SECRET", "").strip()
REFRESH_TOKEN = os.getenv("ZOOMINFO_REFRESH_TOKEN", "").strip()


def get_new_token():
    if not CLIENT_ID or not CLIENT_SECRET:
        print("ERROR: Set ZOOMINFO_CLIENT_ID and ZOOMINFO_CLIENT_SECRET in .env")
        sys.exit(1)
    if not REFRESH_TOKEN:
        print("ERROR: ZOOMINFO_REFRESH_TOKEN is not set. Get it once with the OAuth flow:")
        print("")
        print("  ZoomInfo only allows HTTPS. Easiest: local HTTPS (no ngrok):")
        print("  1. In Developer Portal add redirect URI:  https://localhost:8443/callback")
        print("  2. In .env set ZOOMINFO_REDIRECT_URI=https://localhost:8443/callback")
        print("  3. Run:  python oauth_capture_refresh_token.py  (accept browser cert warning if shown)")
        print("  4. Script saves ZOOMINFO_REFRESH_TOKEN to .env. Then run this script again.")
        print("")
        print("  Full steps (or ngrok): see GET_REFRESH_TOKEN.md")
        sys.exit(1)

    basic = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    headers = {
        "Authorization": f"Basic {basic}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN,
    }

    print("Requesting new access token from ZoomInfo (Okta)...")
    r = requests.post(TOKEN_URL, headers=headers, data=data, timeout=30)

    if r.status_code != 200:
        print(f"FAIL — HTTP {r.status_code}")
        try:
            err = r.json()
            print("  ", err)
        except Exception:
            print("  ", r.text[:400])
        sys.exit(1)

    body = r.json()
    access_token = body.get("access_token")
    new_refresh = body.get("refresh_token")
    expires_in = body.get("expires_in", 86400)

    if not access_token:
        print("FAIL — No access_token in response")
        sys.exit(1)

    print("OK — New access token received (expires in {}s).".format(expires_in))

    # Update .env: set ZOOMINFO_ACCESS_TOKEN and optionally ZOOMINFO_REFRESH_TOKEN (rotated)
    if not env_path.exists():
        print("  .env not found; not updating. Add to .env manually:")
        print("  ZOOMINFO_ACCESS_TOKEN=" + access_token[:50] + "...")
        return

    lines = []
    done_access = False
    done_refresh = False
    for line in open(env_path, "r", encoding="utf-8"):
        if line.strip().startswith("ZOOMINFO_ACCESS_TOKEN="):
            lines.append(f"ZOOMINFO_ACCESS_TOKEN={access_token}\n")
            done_access = True
        elif line.strip().startswith("ZOOMINFO_REFRESH_TOKEN=") and new_refresh:
            lines.append(f"ZOOMINFO_REFRESH_TOKEN={new_refresh}\n")
            done_refresh = True
        else:
            lines.append(line if line.endswith("\n") else line + "\n")
    if not done_access:
        lines.append(f"ZOOMINFO_ACCESS_TOKEN={access_token}\n")
    if new_refresh and not done_refresh:
        lines.append(f"ZOOMINFO_REFRESH_TOKEN={new_refresh}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print("  Updated .env with ZOOMINFO_ACCESS_TOKEN" + (" and ZOOMINFO_REFRESH_TOKEN" if new_refresh else ""))
    print("  Next: python test_zoominfo_connection.py   or   python zoominfo_enrich_company.py -n \"Apex Aircraft Sales\"")


if __name__ == "__main__":
    get_new_token()
