#!/usr/bin/env python3
"""
List ZoomInfo **Lookup Enrich** fields allowed for your account (input/output per entity).

Official Data API (OpenAPI): GET {ZOOMINFO_BASE_URL}/data/v1/lookup/enrich
  ?filter[entity]=contact|company|...
  &filter[fieldType]=output|input

Some ZoomInfo docs describe POST with the same query string; use --method post if GET fails.

Requires ZOOMINFO_ACCESS_TOKEN (and optional ZOOMINFO_BASE_URL) in phlydata-zoominfo/.env
(same as other scripts). From repo root you can instead run with backend env:

  cd backend && ..\\.venv\\Scripts\\python  ..\\phlydata-zoominfo\\list_lookup_enrich_fields.py

Examples:
  python list_lookup_enrich_fields.py --entity contact --field-type output
  python list_lookup_enrich_fields.py --entity company --field-type output -o fields.json
  python list_lookup_enrich_fields.py --entity contact --method post
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

env_path = Path(__file__).resolve().parent / ".env"
if env_path.exists():
    from dotenv import load_dotenv

    load_dotenv(env_path)

# Reuse backend client (token refresh, base URL) when run from HyeAero repo
_REPO = Path(__file__).resolve().parents[1]
_BACKEND_SERVICES = _REPO / "backend" / "services"
if _BACKEND_SERVICES.is_dir():
    sys.path.insert(0, str(_REPO / "backend"))
    try:
        from services.zoominfo_client import lookup_enrich_output_fields
    except ImportError:
        lookup_enrich_output_fields = None  # type: ignore[misc,assignment]
else:
    lookup_enrich_output_fields = None  # type: ignore[misc,assignment]


def _run_standalone(entity: str, field_type: str, method: str) -> tuple[dict | None, str | None]:
    import requests

    token = os.getenv("ZOOMINFO_ACCESS_TOKEN", "").strip()
    base = os.getenv("ZOOMINFO_BASE_URL", "https://api.zoominfo.com/gtm").rstrip("/")
    if not token:
        return None, "Set ZOOMINFO_ACCESS_TOKEN in .env"
    url = f"{base}/data/v1/lookup/enrich"
    params = {"filter[entity]": entity, "filter[fieldType]": field_type}
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.api+json",
    }
    if method == "get":
        r = requests.get(url, params=params, headers=headers, timeout=30)
    else:
        r = requests.post(url, params=params, headers=headers, timeout=30)
    if r.status_code >= 400:
        try:
            err = r.json()
        except Exception:
            err = r.text
        return None, f"HTTP {r.status_code}: {err}"
    return r.json(), None


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--entity",
        default="contact",
        help="ZoomInfo entity (contact, company, scoop, news, …). Default: contact",
    )
    p.add_argument(
        "--field-type",
        choices=("output", "input"),
        default="output",
        help="Field type filter (default: output).",
    )
    p.add_argument(
        "--method",
        choices=("get", "post"),
        default="get",
        help="HTTP method (OpenAPI: get). Use post if your integration guide says POST.",
    )
    p.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help="Write JSON response to this file.",
    )
    p.add_argument(
        "--no-backend-client",
        action="store_true",
        help="Do not use backend zoominfo_client (no auto token refresh); raw .env token only.",
    )
    args = p.parse_args()

    use_client = lookup_enrich_output_fields is not None and not args.no_backend_client
    if use_client:
        data, err = lookup_enrich_output_fields(
            entity=args.entity,
            field_type=args.field_type,
            http_method=args.method,
        )
    else:
        data, err = _run_standalone(args.entity, args.field_type, args.method)

    if err:
        print(err, file=sys.stderr)
        return 1

    text = json.dumps(data, indent=2)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
