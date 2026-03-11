# PhlyData → ZoomInfo Contact Enrichment Tool

Look up aircraft owners from your data sources and enrich contact details using ZoomInfo.

## Overview

This tool:

1. **Lists serial numbers** from PhlyData (internal DB from [phlydata.com](https://phlydata.com)), which are already loaded into PostgreSQL via the ETL pipeline.
2. **Finds owners** for a given serial number by searching your data sources (Controller, FAA, AircraftExchange) in PostgreSQL.
3. **Enriches contacts** by fetching additional detail (email, phone, company, etc.) from ZoomInfo.

## Data Flow

```
[PhlyData serial number] 
    → PostgreSQL (aircraft) 
    → Owner lookup (Controller, FAA, AircraftExchange in PostgreSQL) 
    → ZoomInfo API (contact enrichment)
```

## Data Sources (PostgreSQL)

| Source | Table(s) | Owner / Contact fields |
|--------|----------|------------------------|
| **PhlyData** (internal) | `aircraft` | Serial numbers from internal loader (`aircraft.csv` → `aircraft.serial_number`) |
| **Controller** | `aircraft_listings` + `aircraft` | `seller_contact_name`, `seller_phone`, `seller_email`, `seller`, `seller_broker` |
| **FAA** | `faa_registrations` + `aircraft` | `registrant_name`, `street`, `city`, `state`, `zip_code`, `country` |
| **AircraftExchange** | `aircraft_listings` + `aircraft` | `seller` (dealer_name), `seller_contact_name`, `seller_phone`, `seller_email` |

Owner lookup uses `aircraft` as the link: match by `serial_number` (and optionally `registration_number`), then join to `aircraft_listings` (Controller, AircraftExchange) and `faa_registrations` (FAA) via `aircraft_id`.

## Test ZoomInfo connection

### Option A — Manual token (Developer Portal)

1. Log in to [ZoomInfo Developer Portal](https://developer.zoominfo.com) → your app → **Bearer Token** → **Generate**.
2. Copy `.env.example` to `.env` and set `ZOOMINFO_ACCESS_TOKEN=<paste token>`.
3. Run: `pip install -r requirements.txt` then `python test_zoominfo_connection.py`.  
   Success: `OK — ZoomInfo connection successful. Found N result(s).`

Token is valid 24 hours; repeat Generate when it expires.

### Option B — Create token directly (OAuth, no portal each time)

ZoomInfo only allows **HTTPS** redirect URIs. You can use **local HTTPS** (no ngrok) or ngrok:

1. **One-time setup** — get a refresh token:
   - **Local HTTPS:** In Developer Portal add redirect URI `https://localhost:8443/callback`. In `.env` set `ZOOMINFO_REDIRECT_URI=https://localhost:8443/callback`. The script will run an HTTPS server with a self-signed cert (generated once); accept the browser warning when redirected.
   - **Or ngrok:** Run `ngrok http 8080`, add `https://<your-ngrok-host>/callback` in the portal and set `ZOOMINFO_REDIRECT_URI` in `.env`.
   - In `.env` set `ZOOMINFO_CLIENT_ID` and `ZOOMINFO_CLIENT_SECRET`.
   - Run: `python oauth_capture_refresh_token.py` → log in in the browser when prompted.
   - The script saves `ZOOMINFO_REFRESH_TOKEN` and `ZOOMINFO_ACCESS_TOKEN` to `.env`. See **GET_REFRESH_TOKEN.md** for full steps.

2. **Whenever you need a new access token** (e.g. after 24h):
   ```bash
   python get_zoominfo_token.py
   ```
   This calls ZoomInfo’s token endpoint with your refresh token, gets a new access token (and rotated refresh token), and updates `.env`. Then run `python test_zoominfo_connection.py` as usual.

Keep Client ID, Client Secret, and tokens in `.env` only; do not commit `.env`.

### Option C — ZoomInfo official client (api-auth-python-client)

Uses ZoomInfo’s [api-auth-python-client](https://github.com/Zoominfo/api-auth-python-client) with your `.env`:

1. In `.env` set `ZOOMINFO_USERNAME` and `ZOOMINFO_PASSWORD` (your ZoomInfo login).
2. Run:
   ```bash
   pip install -r requirements.txt
   python test_zoominfo_with_official_client.py
   ```
   The script gets a JWT via `api.zoominfo.com/authenticate` (username/password), then calls the Data API company search. If you prefer to use an existing token, set `ZOOMINFO_ACCESS_TOKEN` instead; the script will use it and skip the official client.

**If you see 403 "User … is not authorized to access the API"** — Your ZoomInfo account does not have access to the **enterprise** authenticate endpoint. Use **Option A** (Bearer token from Developer Portal) or **Option B** (OAuth refresh token) for the Data API instead. To get the official client working, contact ZoomInfo Integration Support: integrationsupport@zoominfo.com.

## Prerequisites

- **PostgreSQL** — Same database used by the HyeAero ETL pipeline (aircraft, aircraft_listings, faa_registrations).
- **ZoomInfo API** — Bearer token (or OAuth app) from [ZoomInfo Developer Portal](https://developer.zoominfo.com).
- **Python 3.11+** — For the tool implementation.

## Setup (planned)

1. Configure `.env`:
   - `POSTGRES_CONNECTION_STRING` — PostgreSQL connection string (same as ETL/backend).
   - `ZOOMINFO_API_KEY` (or equivalent) — ZoomInfo API credentials.

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run:
   ```bash
   python main.py                    # Interactive: input serial number, list results
   python main.py --serial SN12345   # CLI: lookup serial and enrich
   ```

## Project Structure (planned)

```
phlydata-zoominfo/
├── README.md
├── requirements.txt
├── .env.example
├── config.py           # Load Postgres + ZoomInfo config
├── lookup.py           # Query PostgreSQL for serial → owner
├── zoominfo.py         # ZoomInfo API client for contact enrichment
├── main.py             # CLI / entrypoint
└── output/             # Optional: export enriched contacts (CSV, etc.)
```

## Implementation Notes

- **Serial number list**: Query `aircraft` for distinct `serial_number` values. PhlyData records are those loaded by the internal loader from `store/raw/internaldb/aircraft.csv`. If you need to distinguish PhlyData-only serials, consider adding a `source` or `source_metadata` filter.
- **Owner resolution**: For a given serial, query `aircraft` → `aircraft_listings` (source_platform IN ('controller','aircraftexchange')) and `aircraft` → `faa_registrations` to collect seller/registrant/contact names and basic info.
- **ZoomInfo**: Use ZoomInfo Search API or Contact Enrichment API to find additional contact details (email, direct phone, LinkedIn, etc.) from the owner/seller name and company.

## Related

- **ETL pipeline** (`etl-pipeline/`) — Loads PhlyData (internal), Controller, AircraftExchange, FAA into PostgreSQL.
- **Backend** — HyeAero API; can optionally expose this tool as an endpoint or keep it as a standalone script.
