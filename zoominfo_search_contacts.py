#!/usr/bin/env python3
"""
Search ZoomInfo contacts (people) by full name.

Uses the same API as the backend: POST /data/v1/contacts/search with fullName only.

Usage:
  python zoominfo_search_contacts.py --full-name "John Smith"
  python zoominfo_search_contacts.py -n "Jane Doe" --page-size 25 --pages 2
  python zoominfo_search_contacts.py -n "Saxton Craig" --output contacts_results.json

Requires ZOOMINFO_ACCESS_TOKEN in .env (same as company search).
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
BASE = os.getenv("ZOOMINFO_BASE_URL", "https://api.zoominfo.com/gtm").rstrip("/")
JSON_API = "application/vnd.api+json"


def search_contacts(full_name=None, page_number=1, page_size=25):
    """POST /data/v1/contacts/search with fullName in attributes."""
    url = f"{BASE}/data/v1/contacts/search"
    params = {"page[number]": page_number, "page[size]": min(100, max(1, page_size))}
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": JSON_API, "Accept": JSON_API}
    body = {"data": {"type": "ContactSearch", "attributes": {}}}
    if full_name:
        body["data"]["attributes"]["fullName"] = full_name.strip()
    r = requests.post(url, json=body, params=params, headers=headers, timeout=30)
    if r.status_code == 403:
        err_body = r.text
        try:
            err_body = r.json()
        except Exception:
            pass
        raise requests.HTTPError(
            f"403 Forbidden: Contact Search may not be included in your ZoomInfo plan. "
            f"Company Search often works with the same token; Contact/People data may require a different product or scope. "
            f"Response: {err_body}",
            response=r,
        )
    r.raise_for_status()
    return r.json()


def main():
    parser = argparse.ArgumentParser(description="Search ZoomInfo contacts (people) by full name")
    parser.add_argument("--full-name", "-n", default=None, help="Full name to search (e.g. 'John Smith')")
    parser.add_argument("--page-size", "-s", type=int, default=25, help="Results per page (1-100)")
    parser.add_argument("--pages", "-p", type=int, default=1, help="Number of pages to fetch")
    parser.add_argument("--output", "-o", default=None, help="Write all results to JSON file")
    args = parser.parse_args()

    if not TOKEN:
        print("ERROR: ZOOMINFO_ACCESS_TOKEN not set in .env", file=sys.stderr)
        sys.exit(1)

    if not args.full_name or not args.full_name.strip():
        print("ERROR: --full-name / -n is required", file=sys.stderr)
        sys.exit(1)

    all_data = []
    total_results = None
    try:
        for page_num in range(1, args.pages + 1):
            data = search_contacts(full_name=args.full_name, page_number=page_num, page_size=args.page_size)
            meta = data.get("meta", {})
            total_results = meta.get("totalResults")
            page = data.get("data", [])
            all_data.extend(page)
            print(f"Page {page_num}: got {len(page)} contacts (total so far: {len(all_data)})")
            if total_results is not None and len(all_data) >= total_results:
                break
            if len(page) < args.page_size:
                break
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 403:
            print("ERROR: 403 Forbidden on Contact Search.", file=sys.stderr)
            print("Your ZoomInfo token likely has access to Company Search only, not Contact/People Search.", file=sys.stderr)
            print("Contact ZoomInfo or check your plan to enable Contact Search (e.g. api:data:contact scope).", file=sys.stderr)
            if str(e):
                print(str(e), file=sys.stderr)
        else:
            print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    if total_results is not None:
        print(f"Total results for this search: {total_results}")
    print(f"Collected {len(all_data)} contacts.")
    for i, c in enumerate(all_data[:10], 1):
        attrs = c.get("attributes", {})
        name = attrs.get("fullName") or f"{attrs.get('firstName', '')} {attrs.get('lastName', '')}".strip() or "—"
        company = attrs.get("companyName") or attrs.get("company") or "—"
        phone = attrs.get("phone") or attrs.get("directPhone") or attrs.get("mobilePhone") or "—"
        city = attrs.get("city") or "—"
        print(f"  {i}. {name}")
        print(f"      Company: {company} | Phone: {phone} | City: {city}")
    if len(all_data) > 10:
        print(f"  ... and {len(all_data) - 10} more")

    if args.output and all_data:
        out = {"meta": {"totalCollected": len(all_data), "totalResults": total_results, "queryFullName": args.full_name}, "data": all_data}
        Path(args.output).write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"Wrote {len(all_data)} contacts to {args.output}")


if __name__ == "__main__":
    main()
