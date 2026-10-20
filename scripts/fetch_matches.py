#!/usr/bin/env python3
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests

# ---------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------
SOURCE_URL = "https://www.fotmob.com/api/data/matches"
TIMEZONE = "Asia%2FKathmandu"
REGION = "NPL"
FUTURE_DAYS = 7
LIVE_GRACE_MINUTES = 180

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
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
    r = requests.get(url, impersonate="chrome124", headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()

def team_slug(name: str) -> str:
    if not name: return "unknown"
    return re.sub(r"[^a-z0-9]", "", name.strip().lower())

def get_logo_url(team_id):
    if not team_id: return ""
    
    
    singhs_url = f"https://img.singhs.com.np/team/{team_id}.png"
    try:
        # Quick HEAD request to check if the image actually exists
        head = requests.head(singhs_url, timeout=3)
        if head.status_code == 200:
            return singhs_url
    except Exception:
        pass
        
   
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
        "team1_logo": get_logo_url(home_id),
        "team2_logo": get_logo_url(away_id),
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

    for day in range(FUTURE_DAYS + 1):
        d = now + timedelta(days=day)
        date_str = d.strftime("%Y%m%d")
        try:
            data = fetch_date(date_str)
        except Exception as e:
            print(f"  [{date_str}] FAILED: {e}", file=sys.stderr)
            continue

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

    all_matches.sort(key=lambda m: m.get("start") or "")
    OUT_FILE.write_text(json.dumps({"matches": all_matches}, ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
