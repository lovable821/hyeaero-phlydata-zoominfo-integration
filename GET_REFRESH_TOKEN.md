# How to get a ZoomInfo refresh token

You only need to do this **once**. After that, `get_zoominfo_token.py` can create new access tokens without opening the Developer Portal.

**ZoomInfo only allows HTTPS redirect URIs.** You can use **local HTTPS** (no ngrok) or **ngrok**.

---

## Option A — Local HTTPS (no ngrok)

The script can run an HTTPS server on your machine with a **self-signed certificate**. You need **OpenSSL** installed (usually already on Mac/Linux; on Windows you may have it via Git for Windows or install from [openssl.org](https://wiki.openssl.org/index.php/Binaries)).

### 1. Add redirect URI in Developer Portal

1. Go to [ZoomInfo Developer Portal](https://developer.zoominfo.com) and log in.
2. Open **your application**.
3. Find **Redirect URIs** and add:
   ```text
   https://localhost:8443/callback
   ```
4. Save.

### 2. Set .env

In the `phlydata-zoominfo` folder, in `.env` set:

- `ZOOMINFO_CLIENT_ID=...` (from your app)
- `ZOOMINFO_CLIENT_SECRET=...` (from your app)
- `ZOOMINFO_REDIRECT_URI=https://localhost:8443/callback`

### 3. Run the OAuth script

```bash
python oauth_capture_refresh_token.py
```

- The first time, the script will generate a self-signed certificate (`.localhost-cert.pem` and `.localhost-key.pem`) in this folder.
- Your browser will open ZoomInfo’s login page. After you log in, ZoomInfo will redirect to `https://localhost:8443/callback`.
- Your browser may show a **warning** (e.g. “Your connection is not private”) because the cert is self-signed—choose **Advanced** → **Proceed to localhost** (or similar) to continue.
- The script will receive the callback, save `ZOOMINFO_REFRESH_TOKEN` and `ZOOMINFO_ACCESS_TOKEN` to `.env`, and you’ll see “Success” in the browser.

### 4. Use it from now on

Whenever you need a new access token (e.g. after 24 hours):

```bash
python get_zoominfo_token.py
```

---

## Option B — Ngrok (if local HTTPS is not possible)

If ZoomInfo does not accept `https://localhost:8443` or you prefer not to use a self-signed cert:

1. Install [ngrok](https://ngrok.com/download). In a **separate terminal** run: `ngrok http 8080`
2. In Developer Portal add redirect URI: `https://<your-ngrok-host>/callback` (e.g. `https://abc123.ngrok-free.app/callback`)
3. In `.env` set `ZOOMINFO_REDIRECT_URI=https://<your-ngrok-host>/callback`
4. Run `python oauth_capture_refresh_token.py` (the script will use HTTP on port 8080; ngrok forwards HTTPS to it)

---

## Troubleshooting

- **“Redirect URI mismatch”** — The redirect URI in the Developer Portal must match **exactly** the value of `ZOOMINFO_REDIRECT_URI` in `.env` (including `https://`, port, and `/callback`, no trailing slash).
- **Browser certificate warning (local HTTPS)** — Expected for a self-signed cert. Proceed to localhost to continue.
- **“Could not generate certificate”** — Install OpenSSL, or use Option B (ngrok).
- **Port in use** — Use a different port in the redirect URI (e.g. `https://localhost:9443/callback`) and add the same in the Developer Portal.
