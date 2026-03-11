#!/usr/bin/env python3
"""
Search ZoomInfo companies with pagination.

Usage:
  python zoominfo_search_companies.py
  python zoominfo_search_companies.py --company-name "Acme"
  python zoominfo_search_companies.py --company-name "Tech" --page-size 50 --pages 3
  python zoominfo_search_companies.py --output results.json

You cannot get "all" companies in one go: the API is search-based. Use search criteria
(companyName, industryCodes, metroRegion, etc.) and paginate. See ZoomInfo Data API docs
for full attribute list. Contacts require api:data:contact scope and /data/v1/contacts/search.
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


def search_companies(company_name=None, page_number=1, page_size=25):
    url = f"{BASE}/data/v1/companies/search"
    params = {"page[number]": page_number, "page[size]": min(100, max(1, page_size))}
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": JSON_API, "Accept": JSON_API}
    body = {"data": {"type": "CompanySearch", "attributes": {}}}
    if company_name:
        body["data"]["attributes"]["companyName"] = company_name
    r = requests.post(url, json=body, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()


def main():
    parser = argparse.ArgumentParser(description="Search ZoomInfo companies with pagination")
    parser.add_argument("--company-name", "-n", default=None, help="Filter by company name (partial match)")
    parser.add_argument("--page-size", "-s", type=int, default=25, help="Results per page (1-100)")
    parser.add_argument("--pages", "-p", type=int, default=1, help="Number of pages to fetch")
    parser.add_argument("--output", "-o", default=None, help="Write all results to JSON file")
    args = parser.parse_args()

    if not TOKEN:
        print("ERROR: ZOOMINFO_ACCESS_TOKEN not set in .env", file=sys.stderr)
        sys.exit(1)

    all_data = []
    total_results = None
    for page_num in range(1, args.pages + 1):
        data = search_companies(company_name=args.company_name, page_number=page_num, page_size=args.page_size)
        meta = data.get("meta", {})
        total_results = meta.get("totalResults")
        page = data.get("data", [])
        all_data.extend(page)
        print(f"Page {page_num}: got {len(page)} companies (total so far: {len(all_data)})")
        if total_results is not None and len(all_data) >= total_results:
            break
        if len(page) < args.page_size:
            break

    if total_results is not None:
        print(f"Total results for this search: {total_results}")
    print(f"Collected {len(all_data)} companies.")
    for i, co in enumerate(all_data[:10], 1):
        attrs = co.get("attributes", {})
        print(f"  {i}. {attrs.get('name', '—')} (id: {co.get('id', '—')})")
    if len(all_data) > 10:
        print(f"  ... and {len(all_data) - 10} more")

    if args.output and all_data:
        out = {"meta": {"totalCollected": len(all_data), "totalResults": total_results}, "data": all_data}
        Path(args.output).write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"Wrote {len(all_data)} companies to {args.output}")


if __name__ == "__main__":
    main()
