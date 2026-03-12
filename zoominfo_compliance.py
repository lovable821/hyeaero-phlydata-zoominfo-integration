#!/usr/bin/env python3
"""
Test ZoomInfo Compliance API.

The Compliance API returns data privacy and opt-out compliance details for *contacts*
(people) in ZoomInfo's database — not companies. Use it to check whether a contact
has opted out, or to see regulatory flags (EU, California, Canada).

Docs: https://api-docs.zoominfo.com (Compliance API section)
Endpoint: POST https://api.zoominfo.com/compliance

Input params: companyName, personFirstName, personLastName, personEmailAddress,
  personPhone, personState, personCountry, personZipCode, personFullName, companyId

Output: id, firstName, lastName, title, companyName, employmentHistory,
  emailAddresses, withinEu, withinCalifornia, withinCanada, noticeProvidedDate, etc.

Usage:
  python zoominfo_compliance.py
  python zoominfo_compliance.py --company "ZoomInfo" --first "Henry" --last "Schuck"
  python zoominfo_compliance.py --email "john.doherty@zoominfo.com"
"""

import argparse
import json
import os
import sys
from pathlib import Path

import requests

env_path = Path(__file__).resolve().parent / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)

TOKEN = os.getenv("ZOOMINFO_ACCESS_TOKEN", "").strip()
USERNAME = os.getenv("ZOOMINFO_USERNAME", "").strip()
PASSWORD = os.getenv("ZOOMINFO_PASSWORD", "").strip()
# Compliance API is part of Legacy API at api.zoominfo.com (not /gtm).
# It typically requires JWT from api.zoominfo.com/authenticate (Legacy), not Developer Portal token.
COMPLIANCE_URL = "https://api.zoominfo.com/compliance"


def get_legacy_jwt() -> str:
    """Get JWT via zi-api-auth-client (username/password) for Legacy API."""
    try:
        import zi_api_auth_client
        return zi_api_auth_client.user_name_pwd_authentication(USERNAME, PASSWORD)
    except ImportError:
        return ""
    except Exception:
        return ""


def compliance_check(match_person_input: list, token: str) -> requests.Response:
    """
    POST to ZoomInfo Compliance API.
    matchPersonInput: list of dicts, each with keys like companyName, personFirstName,
      personLastName, personEmailAddress, etc.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    body = {"matchPersonInput": match_person_input}
    r = requests.post(COMPLIANCE_URL, json=body, headers=headers, timeout=30)
    return r


def main():
    parser = argparse.ArgumentParser(
        description="Test ZoomInfo Compliance API (contact privacy/opt-out data)"
    )
    parser.add_argument("--company", "-c", default=None, help="Company name")
    parser.add_argument("--first", "-f", default=None, help="Contact first name")
    parser.add_argument("--last", "-l", default=None, help="Contact last name")
    parser.add_argument("--email", "-e", default=None, help="Contact email")
    parser.add_argument("--output", "-o", default=None, help="Write response to JSON file")
    args = parser.parse_args()

    token = TOKEN
    if not token and USERNAME and PASSWORD:
        print("ZOOMINFO_ACCESS_TOKEN not set. Trying Legacy JWT (username/password)...")
        token = get_legacy_jwt()
    if not token:
        print("ERROR: Set ZOOMINFO_ACCESS_TOKEN in .env (Developer Portal token), or")
        print("       ZOOMINFO_USERNAME and ZOOMINFO_PASSWORD for Legacy API JWT.", file=sys.stderr)
        sys.exit(1)

    # Build match input — use example from docs if no args
    match_input = []
    if args.company or args.first or args.last:
        obj = {}
        if args.company:
            obj["companyName"] = args.company
        if args.first:
            obj["personFirstName"] = args.first
        if args.last:
            obj["personLastName"] = args.last
        if obj:
            match_input.append(obj)
    if args.email:
        match_input.append({"personEmailAddress": args.email})

    if not match_input:
        # Default: ZoomInfo example from docs
        match_input = [
            {"companyName": "ZoomInfo", "personFirstName": "Henry", "personLastName": "Schuck"},
            {"personEmailAddress": "john.doherty@zoominfo.com"},
        ]
        print("No input provided. Using default: company=ZoomInfo, first=Henry, last=Schuck + one email lookup")

    print(f"POST {COMPLIANCE_URL}")
    print(f"matchPersonInput: {json.dumps(match_input, indent=2)}")
    print()

    resp = compliance_check(match_input, token)
    # If 401 and we have username/password, try Legacy JWT (Compliance is Legacy API)
    if resp.status_code == 401 and token == TOKEN and USERNAME and PASSWORD:
        print("401 with Developer Portal token. Retrying with Legacy JWT (username/password)...")
        legacy = get_legacy_jwt()
        if legacy:
            resp = compliance_check(match_input, legacy)

    print(f"Status: {resp.status_code}")
    try:
        data = resp.json()
    except Exception:
        print(f"Response (raw): {resp.text[:500]}")
        sys.exit(1)

    if resp.status_code == 200:
        success = data.get("success", False)
        result = data.get("data", {}).get("result", [])
        print(f"success: {success}, results: {len(result)}")
        for i, item in enumerate(result):
            inp = item.get("input", {})
            rows = item.get("data", [])
            print(f"  [{i+1}] input={inp} -> {len(rows)} match(es)")
            for j, r in enumerate(rows[:3]):
                print(f"       {r.get('firstName')} {r.get('lastName')} @ {r.get('companyName')}")
            if len(rows) > 3:
                print(f"       ... and {len(rows)-3} more")
        if args.output:
            Path(args.output).write_text(json.dumps(data, indent=2), encoding="utf-8")
            print(f"Wrote full response to {args.output}")
    else:
        print(f"Error: {data}")
        if resp.status_code == 401:
            print()
            print("Note: The Compliance API (api.zoominfo.com/compliance) is part of the Legacy API.")
            print("  401 can mean: (a) token type mismatch (try Legacy JWT via ZOOMINFO_USERNAME/PASSWORD),")
            print("  (b) your ZoomInfo plan may not include Compliance API access.")
            print("  Contact ZoomInfo Integration Support: integrationsupport@zoominfo.com")
        sys.exit(1)


if __name__ == "__main__":
    main()
