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

## Prerequisites

- **PostgreSQL** — Same database used by the HyeAero ETL pipeline (aircraft, aircraft_listings, faa_registrations).
- **ZoomInfo API** — Credentials and API access for contact/company enrichment.
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
