# Get a new ZoomInfo access token directly (no Developer Portal)

Use this when your token is invalid or expired (e.g. 401 Unauthorized). The script calls ZoomInfo’s token endpoint and updates `.env` with the new token.

---

## Prerequisites (one-time)

You need a **refresh token** first. Two options:

### Option 1 — You already have a refresh token

If `.env` already has `ZOOMINFO_REFRESH_TOKEN` (from a previous OAuth run), skip to **Run the script** below.

### Option 2 — Get a refresh token once (OAuth)

1. In [ZoomInfo Developer Portal](https://developer.zoominfo.com) → your app:
   - Add redirect URI: `https://localhost:8443/callback`
   - Note your **Client ID** and **Client Secret**
2. In `phlydata-zoominfo/.env` set:
   - `ZOOMINFO_CLIENT_ID=...`
   - `ZOOMINFO_CLIENT_SECRET=...`
   - `ZOOMINFO_REDIRECT_URI=https://localhost:8443/callback`
3. Run once:
   ```bash
   python oauth_capture_refresh_token.py
   ```
   Log in in the browser when prompted. The script saves `ZOOMINFO_REFRESH_TOKEN` and `ZOOMINFO_ACCESS_TOKEN` to `.env`.  
   Full steps: see **GET_REFRESH_TOKEN.md**.

---

## Run the script (get new access token)

From the `phlydata-zoominfo` folder:

```bash
python get_zoominfo_token.py
```

- On Windows you can also run: `get_token.cmd`
- The script requests a new access token from ZoomInfo (Okta), then updates `.env` with `ZOOMINFO_ACCESS_TOKEN` (and the new refresh token if ZoomInfo rotated it).
- Then run your API calls as usual, e.g.:
  ```bash
  python zoominfo_enrich_company.py -n "Apex Aircraft Sales"
  python test_zoominfo_connection.py
  ```

If you see **"ZOOMINFO_REFRESH_TOKEN is not set"**, complete the one-time OAuth step above (Option 2).
