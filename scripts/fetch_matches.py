#!/usr/bin/env python3
import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from curl_cffi import requests

SOURCE_URL = "https://www.fotmob.com/api/data/matches"
TIMEZONE = "Asia%2FKathmandu"
REGION = "NPL"
FUTURE_DAYS = 7
LIVE_GRACE_MINUTES = 180

# Updated to match Chrome 131
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.fotmob.com/",
    "Origin": "https://www.fotmob.com",
}

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUT_FILE = DATA_DIR / "all-matches.json"

def fetch_date(date_str: str) -> dict:
    url = f"{SOURCE_URL}?date={date_str}&timezone={TIMEZONE}&ccode3={REGION}&includeNextDayLateNight=true"
    
    # Try different impersonations if one fails
    impersonations = ["chrome131", "chrome124", "chrome120"]
    
    for imp in impersonations:
        try:
            r = requests.get(url, impersonate=imp, headers=HEADERS, timeout=30)
            if r.status_code == 200:
                return r.json()
            else:
                print(f"  [{date_str}] Blocked with {imp} (Status: {r.status_code})", file=sys.stderr)
        except Exception as e:
            print(f"  [{date_str}] Error with {imp}: {e}", file=sys.stderr)
        
        time.sleep(1) # Wait 1 second before trying next

    raise Exception(f"All impersonations failed for {date_str}")

def team_slug(name: str) -> str:
    if not name: return "unknown"
    return re.sub(r"[^a-z0-9]", "", name.strip().lower())

def logo_url(team_id):
    if not team_id: return ""
    return f"https://img.singhs.com.np/team/{team_id}.png"

def logo_fallback(team_id):
    if not team_id: return ""
    return f"https://images.fotmob.com/image_resources/logo/teamlogo/{team_id}.png"

def normalize_start(utc_time):
    if not utc_time: return None
    m = re.match(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2})", utc_time)
    if m: return m.group(1) + "Z"
    return utc_time

def transform_match(lg: dict, m: dict) -> dict:
    team1 = (m.get("home") or {}).get("name") or "TBD"
    team2 = (m.get("away") or {}).get("name") or "TBD"
    home_id = (m.get("home") or {}).get("id")
    away_id = (m.get("away") or {}).get("id")
    league = lg.get("name") or "Football"
    league_id = lg.get("primaryId") or lg.get("id")
    league_country = lg.get("ccode") or ""

    start = normalize_start((m.get("status") or {}).get("utcTime") or datetime.fromtimestamp((m.get("timeTS") or 0) / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%MZ"))
    event_id = m.get("id")

    return {
        "team1": team1,
        "team2": team2,
        "team1_logo": logo_url(home_id),
        "team1_logo_fallback": logo_fallback(home_id),
        "team2_logo": logo_url(away_id),
        "team2_logo_fallback": logo_fallback(away_id),
        "league": league,
        "league_id": league_id,
        "league_country": league_country,
        "start": start,
        "duration": 2.2,
        "event_id": event_id,
        "slug": team_slug(team1),
    }

def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    cutoff_start = now - timedelta(minutes=LIVE_GRACE_MINUTES)
    cutoff_end = now + timedelta(days=FUTURE_DAYS)

    all_matches = []
    seen_ids = set()
    success_count = 0

    for day in range(FUTURE_DAYS + 1):
        d = now + timedelta(days=day)
        date_str = d.strftime("%Y%m%d")
        try:
            data = fetch_date(date_str)
            success_count += 1
            
            for lg in (data.get("leagues") or []):
                for m in (lg.get("matches") or []):
                    try:
                        status = m.get("status") or {}
                        if status.get("finished") or status.get("cancelled"): continue

                        utc_time = status.get("utcTime") or datetime.fromtimestamp((m.get("timeTS") or 0) / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
                        start_dt = datetime.strptime(utc_time[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)

                        if start_dt < cutoff_start or start_dt > cutoff_end: continue

                        tm = transform_match(lg, m)
                        eid = tm["event_id"]
                        if eid is not None:
                            if eid in seen_ids: continue
                            seen_ids.add(eid)
                        all_matches.append(tm)
                    except Exception as e:
                        print(f"  Warning: skipping item — {e}", file=sys.stderr)
                        
        except Exception as e:
            print(f"  [{date_str}] FAILED completely: {e}", file=sys.stderr)
            continue

    # Don't overwrite the file if we got 0 successful days (prevents blanking the widget)
    if success_count == 0:
        print("All requests failed. Keeping old data file intact.", file=sys.stderr)
        sys.exit(0)

    all_matches.sort(key=lambda m: m.get("start") or "")
    OUT_FILE.write_text(json.dumps({"matches": all_matches}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {len(all_matches)} matches -> {OUT_FILE}")

if __name__ == "__main__":
    main()
