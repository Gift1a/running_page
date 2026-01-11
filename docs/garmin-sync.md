# Garmin Sync Integration

This project pulls Garmin FIT files directly (via Garmin Connect APIs), then runs
`scripts/parse_fit.py` to build the JSON data used by the frontend.

## Prerequisites

- Python 3.10+
- Install dependencies:
  - `pip install -r requirements.txt`

## First-time setup

1) Run sync:

```bash
python scripts/sync_garmin.py --email "you@example.com" --password "your_password" --is-cn --only-run
```

This will:
- Fetch Garmin `secret_string` and store it at `data/secrets/garmin_secret.txt`
- Download new FIT files into `data/fit`
- Regenerate `data/derived/*.json`
- Copy JSON into `public/data` for runtime fetch

## Proxy notes

If you have a system proxy enabled and Garmin login fails, run without env proxy:

```bash
python scripts/sync_garmin.py --is-cn --only-run
```

To explicitly use an HTTP proxy (Clash local port):

```bash
python scripts/sync_garmin.py --proxy "http://127.0.0.1:7890" --is-cn --only-run
```

If you must use system proxy env variables, add `--use-env-proxy`.

Note: Clash usually exposes an HTTP proxy. If you set `HTTPS_PROXY` to an `https://` URL,
requests may fail with SSL errors. Prefer `http://127.0.0.1:7890`.

If secret fetch fails, run the command directly to see the error:

```bash
python vendor/running_page/run_page/get_garmin_secret.py "you@example.com" "your_password" --is-cn
```

If you see a secret but sync still fails, delete `data/secrets/garmin_secret.txt` or run with:

```bash
python scripts/sync_garmin.py --refresh-secret --email "you@example.com" --password "your_password" --is-cn --only-run
```

## Publish JSON to frontend

If you regenerate JSON manually, copy it into `public/data`:

```bash
python scripts/publish_data.py
```

## Daily update (cron)

Example cron entry (runs at 03:00 daily):

```bash
0 3 * * * /usr/bin/python3 /path/to/RunningPage/scripts/sync_garmin.py --only-run --is-cn >> /var/log/garmin_sync.log 2>&1
```

If you want to refresh the Garmin secret token:

```bash
python scripts/sync_garmin.py --email "you@example.com" --password "your_password" --refresh-secret --is-cn --only-run
```
