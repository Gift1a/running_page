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
    args = parser.parse_args()

    secret = ensure_secret(args)
    client, base_url = build_client(secret, args.is_cn, args.proxy, args.use_env_proxy)

    start_time = time.time()
    activity_ids = list_activity_ids(client, base_url, args.only_run)
    downloaded = sync_fit_files(client, base_url, activity_ids, args.fit_dir)
    client.close()

    print(f"Found {len(activity_ids)} activities, downloaded {downloaded} new FIT files.")
    print(f"Sync finished in {time.time() - start_time:.1f}s")

    if not args.skip_parse:
        run_parse(ROOT, args.fit_dir)
    if not args.skip_publish:
        publish_data(ROOT, args.public_dir)


if __name__ == "__main__":
    main()
