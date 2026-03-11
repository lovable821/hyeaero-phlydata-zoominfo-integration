#!/usr/bin/env python3
"""
One-time OAuth flow to get a ZoomInfo refresh token.

ZoomInfo only allows HTTPS redirect URIs. Two options:

  A) Local HTTPS (no ngrok): set ZOOMINFO_REDIRECT_URI=https://localhost:8443/callback
     In Developer Portal add that URI. The script will run an HTTPS server with a
     self-signed cert (generated once); your browser may show a warning—accept to continue.

  B) Ngrok: run "ngrok http 8080", set ZOOMINFO_REDIRECT_URI=https://<your-ngrok-host>/callback.
"""

import base64
import hashlib
import os
import secrets
import ssl
import sys
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests

env_path = Path(__file__).resolve().parent / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)

CLIENT_ID = os.getenv("ZOOMINFO_CLIENT_ID", "").strip()
CLIENT_SECRET = os.getenv("ZOOMINFO_CLIENT_SECRET", "").strip()
# ZoomInfo only allows HTTPS. Use ZOOMINFO_REDIRECT_URI with an ngrok (or similar) HTTPS URL.
REDIRECT_URI = os.getenv("ZOOMINFO_REDIRECT_URI", "").strip() or "http://localhost:8080/callback"
TOKEN_URL = "https://okta-login.zoominfo.com/oauth2/default/v1/token"
AUTH_BASE = "https://login.zoominfo.com"

# PKCE
code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
code_challenge = base64.urlsafe_b64encode(
    hashlib.sha256(code_verifier.encode()).digest()
).decode().rstrip("=")
state = secrets.token_urlsafe(16)

result_holder = {"done": False, "error": None, "refresh_token": None, "access_token": None}


CALLBACK_PATH = "/callback"


def _ensure_localhost_cert(dir_path):
    """Create self-signed cert for localhost if missing. Returns (cert_path, key_path)."""
    cert = dir_path / ".localhost-cert.pem"
    key = dir_path / ".localhost-key.pem"
    if cert.exists() and key.exists():
        return str(cert), str(key)
    print("Generating self-signed certificate for localhost (one-time)...")
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.backends import default_backend
        import ipaddress
    except ImportError:
        print("ERROR: Install the cryptography package: pip install cryptography")
        print("  Or use ngrok: ZOOMINFO_REDIRECT_URI=https://<ngrok-host>/callback and run ngrok http 8080")
        sys.exit(1)
    key_obj = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    san = x509.SubjectAlternativeName([
        x509.DNSName("localhost"),
        x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
    ])
    cert_obj = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key_obj.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=365))
        .add_extension(san, critical=False)
        .sign(key_obj, hashes.SHA256(), default_backend())
    )
    key.write_bytes(
        key_obj.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    cert.write_bytes(cert_obj.public_bytes(serialization.Encoding.PEM))
    return str(cert), str(key)


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != CALLBACK_PATH:
            self.send_response(404)
            self.end_headers()
            return
        qs = parse_qs(parsed.query)
        err = qs.get("error")
        if err:
            result_holder["error"] = err[0] + " — " + (qs.get("error_description", [""])[0])
            self._send_page("Error", result_holder["error"], False)
            result_holder["done"] = True
            return
        code = (qs.get("code") or [None])[0]
        state_back = (qs.get("state") or [None])[0]
        if state_back != state:
            result_holder["error"] = "State mismatch"
            self._send_page("Error", "State mismatch.", False)
            result_holder["done"] = True
            return
        if not code:
            result_holder["error"] = "No code in callback"
            self._send_page("Error", "No authorization code received.", False)
            result_holder["done"] = True
            return

        # Exchange code for tokens
        basic = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
        headers = {
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "code_verifier": code_verifier,
        }
        r = requests.post(TOKEN_URL, headers=headers, data=data, timeout=30)
        if r.status_code != 200:
            result_holder["error"] = f"Token exchange failed: {r.status_code} — {r.text[:300]}"
            self._send_page("Error", result_holder["error"], False)
            result_holder["done"] = True
            return
        body = r.json()
        result_holder["access_token"] = body.get("access_token")
        result_holder["refresh_token"] = body.get("refresh_token")
        result_holder["done"] = True
        msg = "Success. You can close this tab and return to the terminal."
        if result_holder["refresh_token"]:
            msg += " Refresh token has been saved to .env."
        self._send_page("Success", msg, True)

    def _send_page(self, title, message, ok):
        html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>{title}</title></head>
<body style="font-family:sans-serif;max-width:520px;margin:2em auto;padding:1em;">
<h2>{title}</h2>
<p>{message}</p>
</body></html>"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html.encode("utf-8"))))
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def log_message(self, format, *args):
        pass


def main():
    if not CLIENT_ID or not CLIENT_SECRET:
        print("Set ZOOMINFO_CLIENT_ID and ZOOMINFO_CLIENT_SECRET in .env")
        sys.exit(1)

    login_url = (
        f"{AUTH_BASE}/?"
        f"client_id={requests.utils.quote(CLIENT_ID)}"
        f"&redirect_uri={requests.utils.quote(REDIRECT_URI)}"
        f"&response_type=code"
        f"&scope={requests.utils.quote('openid api:data:company')}"
        f"&state={state}"
        f"&code_challenge={code_challenge}"
        f"&code_challenge_method=S256"
    )
    print("1. Add this redirect URI in ZoomInfo Developer Portal (if not already):")
    print("   ", REDIRECT_URI)
    print("2. Opening browser to ZoomInfo login...")
    print("   If it doesn't open, go to:")
    print("   ", login_url[:80] + "...")
    try:
        import webbrowser
        webbrowser.open(login_url)
    except Exception:
        pass

    parsed = urlparse(REDIRECT_URI)
    use_https = parsed.scheme == "https" and (parsed.hostname in ("localhost", "127.0.0.1") or not parsed.hostname)
    port = parsed.port or (8443 if use_https else 8080)
    server = HTTPServer(("localhost", port), CallbackHandler)
    if use_https:
        cert_path, key_path = _ensure_localhost_cert(env_path.parent)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(cert_path, key_path)
        server.socket = ctx.wrap_socket(server.socket, server_side=True)
        print("3. Waiting for callback at", REDIRECT_URI, "(local HTTPS, port %s) ..." % port)
        print("   If your browser warns about the certificate, accept it to continue.")
    else:
        print("3. Waiting for callback at", REDIRECT_URI, "(local port %s) ..." % port)
    while not result_holder["done"]:
        server.handle_request()
    if result_holder["error"]:
        print("ERROR:", result_holder["error"])
        sys.exit(1)
    rt = result_holder.get("refresh_token")
    at = result_holder.get("access_token")
    if not rt:
        print("No refresh_token in response; check ZoomInfo app scopes / redirect URI.")
        sys.exit(1)
    # Append or update .env
    rt = result_holder["refresh_token"]
    at = result_holder.get("access_token")
    lines = []
    replaced_refresh = replaced_access = False
    if env_path.exists():
        for line in open(env_path, "r", encoding="utf-8"):
            if line.strip().startswith("ZOOMINFO_REFRESH_TOKEN="):
                lines.append(f"ZOOMINFO_REFRESH_TOKEN={rt}\n")
                replaced_refresh = True
            elif line.strip().startswith("ZOOMINFO_ACCESS_TOKEN="):
                lines.append(f"ZOOMINFO_ACCESS_TOKEN={at or ''}\n" if at else line)
                if at:
                    replaced_access = True
            else:
                # Ensure each line ends with newline so next append doesn't merge
                lines.append(line if line.endswith("\n") else line + "\n")
    if not replaced_refresh:
        lines.append(f"ZOOMINFO_REFRESH_TOKEN={rt}\n")
    if at and not replaced_access:
        lines.append(f"ZOOMINFO_ACCESS_TOKEN={at}\n")
    if not env_path.exists():
        lines = [f"ZOOMINFO_REFRESH_TOKEN={rt}\n"]
        if at:
            lines.insert(0, f"ZOOMINFO_ACCESS_TOKEN={at}\n")
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print("Saved refresh_token (and access_token) to .env.")
    print("From now on run: python get_zoominfo_token.py")


if __name__ == "__main__":
    main()
