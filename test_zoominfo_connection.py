#!/usr/bin/env python3
"""
Test ZoomInfo API connection using a Bearer token from the Developer Portal.

Usage:
  1. In ZoomInfo Developer Portal: your app → Bearer Token → Generate
  2. Set in .env: ZOOMINFO_ACCESS_TOKEN=your_token_here
  3. Run: python test_zoominfo_connection.py
"""

import os
import sys
from pathlib import Path

# Load .env from this directory
env_path = Path(__file__).resolve().parent / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)

TOKEN = os.getenv("ZOOMINFO_ACCESS_TOKEN", "").strip()

# ZoomInfo Data API: OpenAPI spec has servers.url = https://api.zoominfo.com/gtm
ZOOMINFO_BASE = "https://api.zoominfo.com/gtm"
# JSON:API content type required by ZoomInfo
JSON_API = "application/vnd.api+json"


def test_connection():
    if not TOKEN:
        print("ERROR: ZOOMINFO_ACCESS_TOKEN is not set.")
        print("  1. Open https://developer.zoominfo.com")
        print("  2. Go to your application → Bearer Token → Generate")
        print("  3. Create a .env file here with: ZOOMINFO_ACCESS_TOKEN=<paste token>")
        sys.exit(1)

    url = f"{ZOOMINFO_BASE}/data/v1/companies/search"
    # Check if token looks like a JWT and warn if expired (no verification, just exp claim)
    if TOKEN.count(".") == 2:
        try:
            import base64
            import json
            payload_b64 = TOKEN.split(".")[1]
            payload_b64 += "=" * (4 - len(payload_b64) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
            exp = payload.get("exp")
            if exp:
                import time
                if time.time() > exp:
                    print("WARNING: Token has expired (exp in JWT). Generate a new one in the Developer Portal.")
        except Exception:
            pass

    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": JSON_API,
        "Accept": JSON_API,
    }
    body = {
        "data": {
            "type": "CompanySearch",
            "attributes": {"companyName": "ZoomInfo"},
        }
    }

    print("Calling ZoomInfo API (company search)...")
    try:
        import requests
        r = requests.post(url, json=body, headers=headers, timeout=30)
    except Exception as e:
        print(f"Request failed: {e}")
        sys.exit(1)

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
        print("FAIL — Unauthorized (401). Token may be expired or invalid.")
        print("  Generate a new Bearer token in the Developer Portal and update .env")
    elif r.status_code == 403:
        print("FAIL — Forbidden (403). Check app scopes (e.g. api:data:company).")
    else:
        print(f"FAIL — HTTP {r.status_code}")
    try:
        err = r.json()
        print("  Response:", err)
    except Exception:
        print("  Body:", r.text[:500])
    sys.exit(1)


if __name__ == "__main__":
    test_connection()
