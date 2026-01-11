#!/usr/bin/env python3
import argparse
import json
import math
import sys
from datetime import timezone
from pathlib import Path

try:
    import fitdecode
except ImportError:
    print("Missing dependency: fitdecode. Install with: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)

PACE_BIN_SEC = 15
HR_BIN_BPM = 5
DIST_BIN_M = 1000


def semicircles_to_deg(value):
    return value * 180.0 / (2 ** 31)


def normalize_lat_lon(value):
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    # fitdecode may return raw semicircles or already-scaled degrees.
    if abs(v) > 180:
        return semicircles_to_deg(v)
    return v


def ensure_utc(dt_value):
    if dt_value is None:
        return None
    if dt_value.tzinfo is None:
        return dt_value.replace(tzinfo=timezone.utc)
    return dt_value.astimezone(timezone.utc)


def iso_utc(dt_value):
    if dt_value is None:
        return None
    return ensure_utc(dt_value).isoformat().replace("+00:00", "Z")


def iso_local(dt_value):
    if dt_value is None:
        return None
    return ensure_utc(dt_value).astimezone().isoformat()


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def load_cities(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def find_nearest_city(lat, lon, cities, max_km):
    best = None
    best_km = None
    for city in cities:
        d_km = haversine_km(lat, lon, city["lat"], city["lon"])
        if best_km is None or d_km < best_km:
            best_km = d_km
            best = city
    if best is None:
        return None, None
    if max_km is not None and best_km is not None and best_km > max_km:
        return None, best_km
    return best, best_km


def city_lookup(lat, lon, cities, cache, max_km):
    if lat is None or lon is None:
        return None, None
    key = (round(lat, 3), round(lon, 3))
    if key in cache:
        return cache[key]
    result = find_nearest_city(lat, lon, cities, max_km)
    cache[key] = result
    return result


def get_field_map(frame):
    return {field.name: field.value for field in frame.fields}


def parse_fit_file(path, cities, city_cache, max_city_km):
    session = None
    records = []
    try:
        with fitdecode.FitReader(path) as fit:
            for frame in fit:
                if not isinstance(frame, fitdecode.FitDataMessage):
                    continue
                if frame.name == "session":
                    session = get_field_map(frame)
                elif frame.name == "record":
                    records.append(get_field_map(frame))
    except fitdecode.FitError as exc:
        print(f"Skipping {path.name}: {exc}", file=sys.stderr)
        return None

    if session is None:
        print(f"Skipping {path.name}: no session message", file=sys.stderr)
        return None

    sport_value = session.get("sport")
    sport = str(sport_value).lower() if sport_value is not None else "unknown"
    if sport != "running":
        return None

    start_time = session.get("start_time") or session.get("timestamp")
    start_time = ensure_utc(start_time)
    if start_time is None:
        print(f"Skipping {path.name}: missing start time", file=sys.stderr)
        return None

    first_ts = None
    last_ts = None
    last_distance = None
    hr_sum = 0.0
    hr_count = 0
    first_lat = None
    first_lon = None

    for record in records:
        ts = ensure_utc(record.get("timestamp"))
        if ts is not None:
            if first_ts is None:
                first_ts = ts
            last_ts = ts

        if record.get("distance") is not None:
            try:
                last_distance = float(record["distance"])
            except (TypeError, ValueError):
                pass

        hr = record.get("heart_rate")
        if hr is not None:
            try:
                hr_sum += float(hr)
                hr_count += 1
            except (TypeError, ValueError):
                pass

        if first_lat is None or first_lon is None:
            lat = normalize_lat_lon(record.get("position_lat"))
            lon = normalize_lat_lon(record.get("position_long"))
            if lat is not None and lon is not None:
                first_lat = lat
                first_lon = lon

    distance_m = session.get("total_distance")
    if distance_m is None:
        distance_m = last_distance
    if distance_m is not None:
        try:
            distance_m = float(distance_m)
        except (TypeError, ValueError):
            distance_m = None

    duration_s = session.get("total_timer_time")
    if duration_s is None and first_ts is not None and last_ts is not None:
        duration_s = (last_ts - first_ts).total_seconds()
    if duration_s is not None:
        try:
            duration_s = float(duration_s)
        except (TypeError, ValueError):
            duration_s = None

    avg_hr = session.get("avg_heart_rate")
    if avg_hr is None and hr_count > 0:
        avg_hr = hr_sum / hr_count
    if avg_hr is not None:
        try:
            avg_hr = float(avg_hr)
        except (TypeError, ValueError):
            avg_hr = None

    start_lat = normalize_lat_lon(session.get("start_position_lat")) or first_lat
    start_lon = normalize_lat_lon(session.get("start_position_long")) or first_lon

    pace_sec_per_km = None
    if distance_m and duration_s and distance_m > 0:
        pace_sec_per_km = duration_s / (distance_m / 1000.0)

    city_name = "unknown"
    country = None
    admin1 = None
    if cities is not None:
        city, _ = city_lookup(start_lat, start_lon, cities, city_cache, max_city_km)
        if city is not None:
            city_name = city.get("city") or "unknown"
            country = city.get("country")
            admin1 = city.get("admin1")

    start_time_local = start_time.astimezone()
    activity_id = f"{path.stem}_{int(start_time.timestamp())}"

    return {
        "id": activity_id,
        "sourceFile": path.name,
        "sport": sport,
        "startTime": iso_local(start_time),
        "startTimeUtc": iso_utc(start_time),
        "date": start_time_local.date().isoformat(),
        "distanceM": distance_m,
        "durationS": duration_s,
        "paceSecPerKm": pace_sec_per_km,
        "avgHr": avg_hr,
        "lat": start_lat,
        "lon": start_lon,
        "city": city_name,
        "country": country,
        "admin1": admin1,
    }


def add_bin(bin_map, value, distance_m, bin_size):
    if value is None:
        return
    start = int(value // bin_size) * bin_size
    entry = bin_map.get(start)
    if entry is None:
        entry = {"start": start, "end": start + bin_size, "count": 0, "distanceM": 0.0}
        bin_map[start] = entry
    entry["count"] += 1
    if distance_m:
        entry["distanceM"] += float(distance_m)


def build_daily(activities):
    daily = {}
    for activity in activities:
        date = activity["date"]
        entry = daily.get(date)
        if entry is None:
            entry = {"date": date, "distanceM": 0.0, "durationS": 0.0, "activities": []}
            daily[date] = entry

        distance_m = activity.get("distanceM") or 0.0
        duration_s = activity.get("durationS") or 0.0
        entry["distanceM"] += distance_m
        entry["durationS"] += duration_s
        entry["activities"].append(
            {
                "id": activity["id"],
                "startTime": activity["startTime"],
                "startTimeUtc": activity.get("startTimeUtc"),
                "distanceM": activity.get("distanceM"),
                "durationS": activity.get("durationS"),
                "paceSecPerKm": activity.get("paceSecPerKm"),
                "avgHr": activity.get("avgHr"),
            }
        )

    daily_list = list(daily.values())
    daily_list.sort(key=lambda item: item["date"])
    for entry in daily_list:
        entry["activities"].sort(key=lambda item: item.get("startTimeUtc") or item["startTime"])
    return daily_list


def build_summary(daily_list):
    total_days = len(daily_list)
    total_distance = sum(item["distanceM"] for item in daily_list)
    avg_distance = total_distance / total_days if total_days else 0.0
    return {
        "totalDays": total_days,
        "totalDistanceM": total_distance,
        "avgDistancePerDayM": avg_distance,
    }


def build_monthly(daily_list):
    monthly = {}
    for day in daily_list:
        year, month, _ = day["date"].split("-")
        key = (int(year), int(month))
        entry = monthly.get(key)
        if entry is None:
            entry = {
                "year": key[0],
                "month": key[1],
                "distanceM": 0.0,
                "durationS": 0.0,
                "days": 0,
            }
            monthly[key] = entry
        entry["distanceM"] += day["distanceM"]
        entry["durationS"] += day["durationS"]
        entry["days"] += 1

    monthly_list = list(monthly.values())
    monthly_list.sort(key=lambda item: (item["year"], item["month"]))
    return monthly_list


def build_city_stats(activities):
    stats = {}
    for activity in activities:
        city = activity.get("city") or "unknown"
        if city == "unknown":
            continue
        key = (city, activity.get("country"), activity.get("admin1"))
        entry = stats.get(key)
        if entry is None:
            entry = {
                "city": key[0],
                "country": key[1],
                "admin1": key[2],
                "runs": 0,
                "distanceM": 0.0,
                "durationS": 0.0,
            }
            stats[key] = entry
        entry["runs"] += 1
        if activity.get("distanceM"):
            entry["distanceM"] += float(activity["distanceM"])
        if activity.get("durationS"):
            entry["durationS"] += float(activity["durationS"])

    results = []
    for entry in stats.values():
        avg_pace = None
        if entry["distanceM"] > 0 and entry["durationS"] > 0:
            avg_pace = entry["durationS"] / (entry["distanceM"] / 1000.0)
        results.append(
            {
                "city": entry["city"],
                "country": entry["country"],
                "admin1": entry["admin1"],
                "runs": entry["runs"],
                "distanceM": entry["distanceM"],
                "avgPaceSecPerKm": avg_pace,
            }
        )
    results.sort(key=lambda item: item["distanceM"], reverse=True)
    return results


def build_distributions(activities):
    pace_bins = {}
    hr_bins = {}
    distance_bins = {}

    for activity in activities:
        distance_m = activity.get("distanceM")
        add_bin(pace_bins, activity.get("paceSecPerKm"), distance_m, PACE_BIN_SEC)
        add_bin(hr_bins, activity.get("avgHr"), distance_m, HR_BIN_BPM)
        if distance_m is not None:
            add_bin(distance_bins, distance_m, distance_m, DIST_BIN_M)

    def to_list(bin_map):
        bins = list(bin_map.values())
        bins.sort(key=lambda item: item["start"])
        return bins

    return {
        "paceSecPerKm": {"binSize": PACE_BIN_SEC, "bins": to_list(pace_bins)},
        "avgHr": {"binSize": HR_BIN_BPM, "bins": to_list(hr_bins)},
        "distanceM": {"binSize": DIST_BIN_M, "bins": to_list(distance_bins)},
    }


def write_json(path, data):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=True, separators=(",", ":"))


def main():
    parser = argparse.ArgumentParser(description="Parse FIT files and build JSON outputs.")
    parser.add_argument("--fit-dir", default="data/fit", help="Directory containing .fit files")
    parser.add_argument(
        "--cities",
        default="data/geonames/cities.json",
        help="GeoNames cities JSON (generated offline)",
    )
    parser.add_argument("--out-dir", default="data/derived", help="Output directory")
    parser.add_argument("--max-city-km", type=float, default=100.0, help="Max distance for city match")
    parser.add_argument("--no-city-lookup", action="store_true", help="Skip city matching")
    args = parser.parse_args()

    fit_dir = Path(args.fit_dir)
    if not fit_dir.exists():
        print(f"FIT directory not found: {fit_dir}", file=sys.stderr)
        sys.exit(1)

    cities = None
    city_cache = {}
    if not args.no_city_lookup:
        cities_path = Path(args.cities)
        if not cities_path.exists():
            print(f"Cities file not found: {cities_path}", file=sys.stderr)
            sys.exit(1)
        cities = load_cities(cities_path)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    fit_files = sorted(fit_dir.rglob("*.fit"))
    if not fit_files:
        print(f"No .fit files found under {fit_dir}", file=sys.stderr)
        sys.exit(1)

    activities = []
    for path in fit_files:
        activity = parse_fit_file(path, cities, city_cache, args.max_city_km)
        if activity is None:
            continue
        activities.append(activity)

    activities.sort(key=lambda item: item["startTime"])
    daily_list = build_daily(activities)
    summary = build_summary(daily_list)
    monthly_list = build_monthly(daily_list)
    city_stats = build_city_stats(activities)
    distributions = build_distributions(activities)

    write_json(out_dir / "activities.json", activities)
    write_json(out_dir / "daily.json", daily_list)
    write_json(out_dir / "summary.json", summary)
    write_json(out_dir / "monthly.json", monthly_list)
    write_json(out_dir / "city-stats.json", city_stats)
    write_json(out_dir / "distributions.json", distributions)

    print(f"Parsed {len(activities)} activities -> {out_dir}")


if __name__ == "__main__":
    main()
