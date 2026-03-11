#!/usr/bin/env python3
"""
Test ZoomInfo using ZoomInfo's official api-auth-python-client (zi-api-auth-client)
and credentials from .env.

Uses .env:
  - ZOOMINFO_USERNAME + ZOOMINFO_PASSWORD  → get JWT via official client (api.zoominfo.com/authenticate)
  - or ZOOMINFO_ACCESS_TOKEN               → use existing Bearer token (Developer Portal)

Then calls the same Data API company search to verify the token works.
"""

import os
import sys
from pathlib import Path

env_path = Path(__file__).resolve().parent / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)

ZOOMINFO_USERNAME = os.getenv("ZOOMINFO_USERNAME", "").strip()
ZOOMINFO_PASSWORD = os.getenv("ZOOMINFO_PASSWORD", "").strip()
ZOOMINFO_ACCESS_TOKEN = os.getenv("ZOOMINFO_ACCESS_TOKEN", "").strip()

ZOOMINFO_BASE = "https://api.zoominfo.com/gtm"
JSON_API = "application/vnd.api+json"


def get_token_from_official_client():
    try:
        import zi_api_auth_client
    except ImportError:
        print("ERROR: Install the official client: pip install zi-api-auth-client")
        sys.exit(1)
    print("Using ZoomInfo official client (username/password) to get JWT...")
    try:
        jwt_token = zi_api_auth_client.user_name_pwd_authentication(
            ZOOMINFO_USERNAME, ZOOMINFO_PASSWORD
        )
        return jwt_token
    except Exception as e:
        err = str(e)
        if "403" in err and "not authorized to access the API" in err:
            print("Official client auth failed: Your ZoomInfo user is not enabled for the")
            print("enterprise API (api.zoominfo.com/authenticate). Use Developer Portal instead:")
            print("  • Option A: Developer Portal → Bearer Token → Generate, set ZOOMINFO_ACCESS_TOKEN in .env")
            print("  • Option B: OAuth flow (oauth_capture_refresh_token.py then get_zoominfo_token.py)")
            print("To enable the official client, contact ZoomInfo: integrationsupport@zoominfo.com")
        else:
            print(f"Official client auth failed: {e}")
        sys.exit(1)


def test_company_search(token):
    url = f"{ZOOMINFO_BASE}/data/v1/companies/search"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": JSON_API,
        "Accept": JSON_API,
    }
    body = {
        "data": {
            "type": "CompanySearch",
            "attributes": {"companyName": "ZoomInfo"},
        }
    }
    import requests
    print("Calling ZoomInfo Data API (company search)...")
    r = requests.post(url, json=body, headers=headers, timeout=30)
    if r.status_code == 200:
        data = r.json()
        total = data.get("meta", {}).get("totalResults", 0)
        companies = data.get("data", [])
        print("OK — ZoomInfo connection successful.")
        print(f"  Found {total} result(s).")
        if companies:
            name = companies[0].get("attributes", {}).get("name", "—")
            print(f"  Sample company: {name}")
        return
    if r.status_code == 401:
        print("FAIL — Unauthorized (401). Token may be for a different API (e.g. enterprise vs data).")
    elif r.status_code == 403:
        print("FAIL — Forbidden (403). Check app scopes.")
    else:
        print(f"FAIL — HTTP {r.status_code}")
    try:
        print("  Response:", r.json())
    except Exception:
        print("  Body:", r.text[:500])
    sys.exit(1)


def main():
    # Prefer Developer Portal / OAuth token when set (works for Data API)
    if ZOOMINFO_ACCESS_TOKEN:
        print("Using ZOOMINFO_ACCESS_TOKEN from .env")
        token = ZOOMINFO_ACCESS_TOKEN
    elif ZOOMINFO_USERNAME and ZOOMINFO_PASSWORD:
        token = get_token_from_official_client()
    else:
        print("ERROR: Set in .env either:")
        print("  ZOOMINFO_ACCESS_TOKEN=  (Developer Portal or get_zoominfo_token.py)")
        print("  or  ZOOMINFO_USERNAME= and ZOOMINFO_PASSWORD=  (official client, if enabled)")
        sys.exit(1)
    test_company_search(token)


if __name__ == "__main__":
    main()
