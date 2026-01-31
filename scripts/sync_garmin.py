#!/usr/bin/env python3
import argparse
import base64
import io
import json
import os
import inspect
import shutil
import sys
import time
import zipfile
from pathlib import Path
from datetime import datetime, timezone

import garth
import httpx


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SECRET_FILE = ROOT / "data" / "secrets" / "garmin_secret.txt"
DEFAULT_FIT_DIR = ROOT / "data" / "fit"
DEFAULT_PUBLIC_DIR = ROOT / "public" / "data"

URLS = {
    "COM": "https://connectapi.garmin.com",
    "CN": "https://connectapi.garmin.cn",
}

PROXY_ENV_KEYS = [
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
]
NO_PROXY_KEYS = ["NO_PROXY", "no_proxy"]

PR_NAME_KEYS = [
    "recordType",
    "recordName",
    "name",
    "displayName",
    "distanceName",
    "distanceLabel",
]
PR_DISTANCE_KEYS = [
    "distance",
    "distanceM",
    "distanceMeters",
    "distanceInMeters",
    "distanceValue",
    "recordDistance",
    "recordDistanceInMeters",
]
PR_TIME_KEYS = [
    "duration",
    "durationS",
    "durationSeconds",
    "durationInSeconds",
    "time",
    "timeInSeconds",
    "recordTime",
    "recordTimeInSeconds",
    "recordValue",
]
PR_DATE_KEYS = [
    "date",
    "activityDate",
    "startTimeLocal",
    "startTimeGMT",
    "startTime",
]
PR_ACTIVITY_KEYS = ["activityId", "activityID", "activity_id", "activityIdValue"]


def _parse_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_time_seconds(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        v = float(value)
        if v <= 0:
            return None
        if v > 1e7:
            v /= 1000.0
        return v
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if ":" in text:
            parts = [p for p in text.split(":") if p]
            try:
                nums = [float(p) for p in parts]
            except ValueError:
                return None
            if len(nums) == 2:
                minutes, seconds = nums
                return minutes * 60 + seconds
            if len(nums) == 3:
                hours, minutes, seconds = nums
                return hours * 3600 + minutes * 60 + seconds
        v = _parse_float(text)
        if v is None or v <= 0:
            return None
        if v > 1e7:
            v /= 1000.0
        return v
    return None


def parse_distance_m(value):
    v = _parse_float(value)
    if v is None or v <= 0:
        return None
    if v < 1000:
        return v * 1000.0
    return v


def normalize_date(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 1e12:
            ts /= 1000.0
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
        except (OSError, ValueError):
            return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if "T" in text:
            return text.split("T")[0]
        if len(text) >= 10 and text[4] == "-" and text[7] == "-":
            return text[:10]
        return text
    return None


def _collect_record_dicts(raw, output):
    if isinstance(raw, list):
        for item in raw:
            _collect_record_dicts(item, output)
        return
    if isinstance(raw, dict):
        if any(key in raw for key in PR_NAME_KEYS + PR_DISTANCE_KEYS + PR_TIME_KEYS):
            output.append(raw)
        for value in raw.values():
            _collect_record_dicts(value, output)


def _record_label(record):
    for key in PR_NAME_KEYS:
        value = record.get(key)
        if value:
            return str(value)
    return None


def _record_activity_id(record):
    for key in PR_ACTIVITY_KEYS:
        value = record.get(key)
        if value is not None:
            return str(value)
    return None


def _record_distance(record):
    for key in PR_DISTANCE_KEYS:
        if key in record:
            return parse_distance_m(record.get(key))
    return None


def _record_time(record):
    for key in PR_TIME_KEYS:
        if key in record:
            return parse_time_seconds(record.get(key))
    return None


def _record_date(record):
    for key in PR_DATE_KEYS:
        if key in record:
            return normalize_date(record.get(key))
    return None


def _matches_distance(distance_m, target_m):
    if distance_m is None:
        return False
    return abs(distance_m - target_m) <= target_m * 0.05


def normalize_personal_records(raw):
    records = []
    _collect_record_dicts(raw, records)
    if not records:
        return None

    best5k = None
    best10k = None
    longest = None
    best5k_time = None
    best10k_time = None
    longest_distance = None

    for record in records:
        label = _record_label(record)
        label_text = label.lower() if label else ""
        distance_m = _record_distance(record)
        time_s = _record_time(record)
        date = _record_date(record)
        activity_id = _record_activity_id(record)

        is_5k = "5k" in label_text or "5 km" in label_text or "5公里" in label_text
        is_10k = "10k" in label_text or "10 km" in label_text or "10公里" in label_text

        if not is_5k and _matches_distance(distance_m, 5000):
            is_5k = True
        if not is_10k and _matches_distance(distance_m, 10000):
            is_10k = True

        if is_5k and time_s:
            if best5k_time is None or time_s < best5k_time:
                best5k_time = time_s
                best5k = {
                    "timeSec": time_s,
                    "distanceM": distance_m,
                    "date": date,
                    "activityId": activity_id,
                    "label": label,
                }

        if is_10k and time_s:
            if best10k_time is None or time_s < best10k_time:
                best10k_time = time_s
                best10k = {
                    "timeSec": time_s,
                    "distanceM": distance_m,
                    "date": date,
                    "activityId": activity_id,
                    "label": label,
                }

        if distance_m:
            if longest_distance is None or distance_m > longest_distance:
                longest_distance = distance_m
                longest = {
                    "distanceM": distance_m,
                    "timeSec": time_s,
                    "date": date,
                    "activityId": activity_id,
                    "label": label,
                }

    if not best5k and not best10k and not longest:
        return None

    return {
        "source": "garmin",
        "fetchedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "best5k": best5k,
        "best10k": best10k,
        "longestDistance": longest,
    }


def fetch_personal_records(email, password, is_cn):
    try:
        from garminconnect import Garmin
    except Exception as exc:
        print(f"Personal records disabled: garminconnect not installed ({exc}).")
        return None

    try:
        try:
            client = Garmin(email, password, is_cn=is_cn)
        except TypeError:
            client = Garmin(email, password)
        if hasattr(client, "login"):
            client.login()
        elif hasattr(client, "login_retry"):
            client.login_retry()
        if hasattr(client, "get_personal_records"):
            return client.get_personal_records()
        if hasattr(client, "get_personal_record"):
            return client.get_personal_record()
    except Exception as exc:
        print(f"Personal records fetch failed: {exc}")
        return None
    return None


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=True, separators=(",", ":"))


def clear_personal_records(out_dir, public_dir):
    for name in ("personal-records.json", "personal-records-raw.json"):
        for base in (Path(out_dir), Path(public_dir)):
            path = base / name
            if path.exists():
                path.unlink()


def is_valid_secret(secret):
    try:
        payload = base64.b64decode(secret)
        json.loads(payload)
    except Exception:
        return False
    return True


def configure_garth(is_cn, proxy, use_env_proxy):
    proxies = None
    if proxy:
        proxies = {"http": proxy, "https": proxy}
    if is_cn:
        garth.configure(domain="garmin.cn", ssl_verify=False, proxies=proxies)
    else:
        garth.configure(proxies=proxies)
    if not use_env_proxy and not proxy:
        garth.client.sess.trust_env = False
        garth.client.sess.proxies = {}


def apply_proxy_env(proxy, use_env_proxy):
    if proxy:
        for key in PROXY_ENV_KEYS:
            os.environ[key] = proxy
    elif not use_env_proxy:
        for key in PROXY_ENV_KEYS:
            os.environ.pop(key, None)
        for key in NO_PROXY_KEYS:
            os.environ[key] = "*"


def fetch_secret(email, password, is_cn, proxy, use_env_proxy):
    apply_proxy_env(proxy, use_env_proxy)
    configure_garth(is_cn, proxy, use_env_proxy)
    garth.login(email, password)
    secret = garth.client.dumps()
    if not is_valid_secret(secret):
        raise SystemExit("Failed to fetch a valid Garmin secret string.")
    return secret


def ensure_secret(args):
    secret_file = Path(args.secret_file)
    if secret_file.exists() and not args.refresh_secret:
        cached = secret_file.read_text(encoding="utf-8").strip()
        if is_valid_secret(cached):
            return cached
        raise SystemExit("Cached Garmin secret is invalid. Re-run with --refresh-secret.")

    if not args.email or not args.password:
        raise SystemExit("Missing Garmin email/password for secret refresh.")

    secret = fetch_secret(args.email, args.password, args.is_cn, args.proxy, args.use_env_proxy)
    secret_file.parent.mkdir(parents=True, exist_ok=True)
    secret_file.write_text(secret, encoding="utf-8")
    return secret


def build_client(secret, is_cn, proxy, use_env_proxy):
    apply_proxy_env(proxy, use_env_proxy)
    configure_garth(is_cn, proxy, use_env_proxy)
    garth.client.loads(secret)
    if garth.client.oauth2_token.expired:
        garth.client.refresh_oauth2()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0 Safari/537.36",
        "Authorization": str(garth.client.oauth2_token),
    }
    kwargs = {
        "headers": headers,
        "timeout": httpx.Timeout(120.0, connect=120.0),
        "trust_env": use_env_proxy,
    }
    if proxy:
        params = inspect.signature(httpx.Client).parameters
        if "proxies" in params:
            kwargs["proxies"] = proxy
        elif "proxy" in params:
            kwargs["proxy"] = proxy
    client = httpx.Client(**kwargs)
    base_url = URLS["CN"] if is_cn else URLS["COM"]
    return client, base_url


def fetch_activity_page(client, base_url, start, limit, only_run):
    url = f"{base_url}/activitylist-service/activities/search/activities?start={start}&limit={limit}"
    if only_run:
        url += "&activityType=running"
    response = client.get(url)
    response.raise_for_status()
    return response.json()


def list_activity_ids(client, base_url, only_run):
    ids = []
    start = 0
    limit = 100
    while True:
        page = fetch_activity_page(client, base_url, start, limit, only_run)
        if not page:
            break
        ids.extend([str(item.get("activityId")) for item in page if item.get("activityId")])
        if len(page) < limit:
            break
        start += limit
    return ids


def download_fit(client, base_url, activity_id):
    url = f"{base_url}/download-service/files/activity/{activity_id}"
    response = client.get(url)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    data = response.content
    if data[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            fit_name = next((name for name in zf.namelist() if name.lower().endswith(".fit")), None)
            if not fit_name:
                raise RuntimeError(f"No FIT file inside zip for activity {activity_id}")
            return zf.read(fit_name)
    return data


def sync_fit_files(client, base_url, activity_ids, target_dir):
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    existing = {path.stem for path in target_dir.glob("*.fit")}
    downloaded = 0

    for activity_id in activity_ids:
        if activity_id in existing:
            continue
        fit_data = download_fit(client, base_url, activity_id)
        if fit_data is None:
            continue
        (target_dir / f"{activity_id}.fit").write_bytes(fit_data)
        downloaded += 1
    return downloaded


def run_parse(root, fit_dir):
    import subprocess

    subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / "parse_fit.py"),
            "--fit-dir",
            str(fit_dir),
            "--out-dir",
            str(root / "data" / "derived"),
        ],
        cwd=root,
        check=True,
    )


def publish_data(root, public_dir):
    source_dir = root / "data" / "derived"
    public_dir = Path(public_dir)
    public_dir.mkdir(parents=True, exist_ok=True)
    for json_file in source_dir.glob("*.json"):
        shutil.copy2(json_file, public_dir / json_file.name)


def main():
    parser = argparse.ArgumentParser(description="Sync Garmin FIT data and rebuild derived JSON.")
    parser.add_argument("--email", help="Garmin account email")
    parser.add_argument("--password", help="Garmin account password")
    parser.add_argument("--secret-file", default=str(DEFAULT_SECRET_FILE))
    parser.add_argument("--refresh-secret", action="store_true")
    parser.add_argument("--is-cn", action="store_true", help="Use Garmin CN endpoints")
    parser.add_argument("--only-run", action="store_true", help="Sync running activities only")
    parser.add_argument("--skip-parse", action="store_true", help="Skip parse_fit step")
    parser.add_argument("--fit-dir", default=str(DEFAULT_FIT_DIR))
    parser.add_argument("--proxy", help="HTTP proxy URL, e.g. http://127.0.0.1:7890")
    parser.add_argument("--use-env-proxy", action="store_true", help="Use system proxy env")
    parser.add_argument("--public-dir", default=str(DEFAULT_PUBLIC_DIR))
    parser.add_argument("--skip-publish", action="store_true", help="Skip copying JSON to public")
    parser.add_argument("--fetch-pr", action="store_true", help="Fetch personal records (optional)")
    parser.add_argument("--pr-debug", action="store_true", help="Write raw personal records JSON")
    args = parser.parse_args()

    secret = ensure_secret(args)
    client, base_url = build_client(secret, args.is_cn, args.proxy, args.use_env_proxy)

    start_time = time.time()
    activity_ids = list_activity_ids(client, base_url, args.only_run)
    downloaded = sync_fit_files(client, base_url, activity_ids, args.fit_dir)
    client.close()

    print(f"Found {len(activity_ids)} activities, downloaded {downloaded} new FIT files.")
    print(f"Sync finished in {time.time() - start_time:.1f}s")

    personal_records = None
    if args.fetch_pr:
        if not args.email or not args.password:
            print("Personal records fetch skipped: missing --email/--password.")
        else:
            raw_records = fetch_personal_records(args.email, args.password, args.is_cn)
            if raw_records is not None:
                personal_records = normalize_personal_records(raw_records)
                if personal_records:
                    write_json(ROOT / "data" / "derived" / "personal-records.json", personal_records)
                    if args.pr_debug:
                        write_json(
                            ROOT / "data" / "derived" / "personal-records-raw.json",
                            raw_records,
                        )
                else:
                    print("Personal records returned but no usable entries were parsed.")
            else:
                print("Personal records fetch failed or returned no data.")

        if personal_records is None:
            clear_personal_records(ROOT / "data" / "derived", args.public_dir)

    if not args.skip_parse:
        run_parse(ROOT, args.fit_dir)
    if not args.skip_publish:
        publish_data(ROOT, args.public_dir)


if __name__ == "__main__":
    main()
