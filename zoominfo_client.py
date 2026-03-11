"""
ZoomInfo REST client using a session + Bearer token from .env.
Pattern: setup → consume(process items) → close.
"""

import os
from pathlib import Path
from urllib.parse import urljoin

import requests

# Load .env from this directory
_env_path = Path(__file__).resolve().parent / ".env"
if _env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_path)

# ZoomInfo Data API expects JSON:API
JSON_API = "application/vnd.api+json"


class HttpTargetRestJsonPost:
    def __init__(self, base_url=None, api_path="/data/v1/companies/search"):
        self.base_url = (base_url or os.getenv("ZOOMINFO_BASE_URL", "https://api.zoominfo.com/gtm")).rstrip("/")
        self.api_path = api_path
        self.session = None

    def setup(self):
        token = os.getenv("ZOOMINFO_ACCESS_TOKEN", "").strip()
        if not token:
            raise ValueError("ZOOMINFO_ACCESS_TOKEN is not set in .env")
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": JSON_API,
            "Content-Type": JSON_API,
            "Authorization": f"Bearer {token}",
        })

    def consume(self, generator, done):
        for item in generator:
            self.process(item)
        done()

    def process(self, item):
        url = urljoin(self.base_url + "/", self.api_path.lstrip("/"))
        response = self.session.post(url, json=item, timeout=30)
        response.raise_for_status()
        return response

    def close(self):
        pass


# Quick test when run as script
if __name__ == "__main__":
    client = HttpTargetRestJsonPost(api_path="/data/v1/companies/search")
    client.setup()
    try:
        body = {
            "data": {
                "type": "CompanySearch",
                "attributes": {"companyName": "ZoomInfo"},
            }
        }
        r = client.process(body)
        data = r.json()
        total = data.get("meta", {}).get("totalResults", 0)
        print("OK — ZoomInfo connection successful.")
        print(f"  Found {total} result(s).")
    except requests.HTTPError as e:
        if e.response.status_code == 401:
            print("401 Unauthorized — token expired or invalid.")
            print("  Update ZOOMINFO_ACCESS_TOKEN in .env (Developer Portal → Generate, or run get_zoominfo_token.py).")
        elif e.response.status_code == 403:
            print("403 Forbidden — check app scopes in Developer Portal.")
        else:
            print(f"HTTP {e.response.status_code}: {e}")
        raise SystemExit(1)
    finally:
        client.close()
