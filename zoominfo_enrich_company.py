#!/usr/bin/env python3
"""
Get detailed company data from ZoomInfo by company name or company ID (Enrich API).

Usage:
  python zoominfo_enrich_company.py --company-name "ZoomInfo"
  python zoominfo_enrich_company.py --company-id 344589814
  python zoominfo_enrich_company.py -n "Acme Corp" --output company_detail.json

Uses POST /data/v1/companies/enrich. Each successful match uses ZoomInfo credits.

Match status (meta.matchStatus) can be:
  FULL_MATCH   - Input matched a company with high confidence (credit used).
  NO_MATCH    - No company found (no credit).
  LIMIT_EXCEEDED - Enrich credit limit exceeded.
  INVALID_INPUT  - Error with the input data.
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

# Exact set from ZoomInfo doc example; expand if your account has access (use Lookup Enrich filter[entity]=company, filter[fieldType]=output).
DEFAULT_OUTPUT_FIELDS = ["id", "ticker", "name", "website", "socialMediaUrls"]


def enrich_company(company_id=None, company_name=None, output_fields=None, debug=False):
    """POST /data/v1/companies/enrich with companyId or companyName."""
    match_input = {}
    if company_id is not None:
        match_input["companyId"] = int(company_id)
    if company_name and company_name.strip():
        match_input["companyName"] = company_name.strip()
    if not match_input:
        return None, "Provide --company-id or --company-name"
    url = f"{BASE}/data/v1/companies/enrich"
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": JSON_API, "Accept": JSON_API}
    body = {
        "data": {
            "type": "CompanyEnrich",
            "attributes": {
                "matchCompanyInput": [match_input],
                "outputFields": output_fields or DEFAULT_OUTPUT_FIELDS,
            },
        }
    }
    if debug:
        print("Request body:", json.dumps(body, indent=2), file=sys.stderr)
    r = requests.post(url, json=body, headers=headers, timeout=30)
    if r.status_code == 403:
        try:
            err = r.json()
        except Exception:
            err = r.text
        if debug:
            print("Response:", r.text, file=sys.stderr)
        return None, f"403 Forbidden. Enrich may not be in your plan. Response: {err}"
    if r.status_code == 400:
        try:
            err = r.json()
        except Exception:
            err = r.text
        if debug:
            print("Response:", r.text, file=sys.stderr)
        return None, f"400 Bad Request. ZoomInfo may reject some outputFields or request format. Response: {err}"
    r.raise_for_status()
    data = r.json()
    records = data.get("data") or []
    if not records:
        return None, None
    first = records[0]
    if first.get("meta", {}).get("matchStatus") == "NO_MATCH":
        return None, "No match"
    return first, None


def main():
    parser = argparse.ArgumentParser(description="Get ZoomInfo company details by name or ID (Enrich API)")
    parser.add_argument("--company-name", "-n", default=None, help="Company name to look up")
    parser.add_argument("--company-id", "-i", type=int, default=None, help="ZoomInfo company ID")
    parser.add_argument("--output", "-o", default=None, help="Write result JSON to file")
    parser.add_argument("--debug", action="store_true", help="Print request body and full response on error")
    args = parser.parse_args()

    if not TOKEN:
        print("ERROR: ZOOMINFO_ACCESS_TOKEN not set in .env", file=sys.stderr)
        sys.exit(1)

    if not args.company_id and not (args.company_name and args.company_name.strip()):
        print("ERROR: Provide --company-name or --company-id", file=sys.stderr)
        sys.exit(1)

    record, err = enrich_company(company_id=args.company_id, company_name=args.company_name, debug=args.debug)
    if err and err != "No match":
        print(f"ERROR: {err}", file=sys.stderr)
        sys.exit(1)

    if not record:
        print("No match.")
        sys.exit(0)

    attrs = record.get("attributes", {})
    meta = record.get("meta", {})
    status = meta.get("matchStatus", "—")
    print(f"Match: {status}  (FULL_MATCH=confident match; NO_MATCH=no result; other=see ZoomInfo docs)")
    print(f"ID: {record.get('id', '—')}")
    print(f"Name: {attrs.get('name', '—')}")
    print(f"Website: {attrs.get('website', '—')}")
    print(f"Phone: {attrs.get('phone', '—')}")
    print(f"Address: {attrs.get('address') or attrs.get('addressLine1', '—')}")
    print(f"City: {attrs.get('city', '—')} State: {attrs.get('state', '—')} Zip: {attrs.get('zipCode', '—')}")
    print(f"Country: {attrs.get('country', '—')}")
    print(f"Revenue: {attrs.get('revenue', '—')} Employee range: {attrs.get('employeeRange', '—')}")
    print(f"Founded: {attrs.get('foundedYear', '—')} Status: {attrs.get('companyStatus', '—')}")

    if args.output:
        Path(args.output).write_text(json.dumps(record, indent=2), encoding="utf-8")
        print(f"Wrote to {args.output}")


if __name__ == "__main__":
    main()
