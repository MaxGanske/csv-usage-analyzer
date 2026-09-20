<!-- Project overview, local setup, API contract, and DigitalOcean deployment guide. -->
<!-- The document also records prototype scope boundaries and operational assumptions. -->
# CSV Usage Analyzer

FastAPI service foundation for uploading API request-log CSV files and generating usage reports.

## Local setup

1. Create a virtual environment and install dependencies:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -e ".[dev]"
   ```

2. Copy `.env.example` to `.env` and set `DATABASE_URL` to your database connection string. The application accepts the standard `postgresql://...` URL and converts it for asyncpg.

3. Start the API:

   ```powershell
   fastapi dev src/app/main.py
   ```

The application exposes `GET /health` and `GET /health/db` alongside the report API below.

## Report API

- `POST /reports` - upload a CSV file and create a report
- `GET /reports` - list reports
- `GET /reports/{report_id}` - retrieve one report

The upload must contain `request_id`, `service`, `status_code`, `latency_ms`, and `tokens_used` columns. Status codes must be standard HTTP values from `100` through `599`; `latency_ms` and `tokens_used` must be between `0` and `10000`; and `request_id` values must be unique within the file. Reports include overall failure rate and per-service breakdowns. Report updates and deletes are not supported in this prototype.

## DigitalOcean deployment

1. Create a Managed PostgreSQL database in DigitalOcean and add your application as a trusted source.
2. Copy the database connection string from DigitalOcean. Set it as the App Platform environment variable `DATABASE_URL` with type **Secret**.
3. Deploy this repository as an App Platform service using the included `deploy/app.yaml`, or configure the service to build from the `Dockerfile`.
4. Check `/health/db` after deployment to verify database connectivity.

The deployment manifest includes an empty secret placeholder. Set `DATABASE_URL` through App Platform or `doctl` before the service starts; do not commit the actual connection string.

## Scope

Migrating existing production data and handling complex schema upgrades are outside the current scope.

## Project layout

- `src/app/main.py` - FastAPI application entry point
- `src/app/core/` - application settings
- `src/app/db/` - database session boundary
- `src/app/api/` - API route package
- `tests/` - test package placeholder
