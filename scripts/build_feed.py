#!/usr/bin/env python3
import json
import re
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SEL_FILE = DATA_DIR / "selected.json"
OUT_FILE = DATA_DIR / "matchfeed.json"

def team_code(name: str) -> str:
    if not name: return "???"
    clean = name.replace("FC", "").replace("AFC", "").strip()
    words = clean.split()
    if len(words) >= 3: return "".join(w[0] for w in words[:3]).upper()
    return clean[:3].upper()

def iso_to_widget_time(iso: str) -> str:
    if not iso: return ""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        from datetime import timedelta
        nepal = dt.astimezone(timezone(timedelta(hours=5, minutes=45)))
        return nepal.strftime("%y/%m/%d %H:%M:%S")
    except Exception: return ""

def compute_status(start_iso: str, duration_hours: float) -> str:
    if not start_iso: return "Upcoming"
    try:
        s = datetime.fromisoformat(start_iso.replace("Z", "+00:00")).timestamp()
        end = s + (duration_hours or 2.2) * 3600
        now = datetime.now(timezone.utc).timestamp()
        if now >= end: return "Ended"
        if now >= s: return "LIVE"
        return "Upcoming"
    except Exception: return "Upcoming"

def main():
    if not SEL_FILE.exists():
        OUT_FILE.write_text('{"matches": []}', encoding="utf-8")
        return

    try:
        sel = json.loads(SEL_FILE.read_text(encoding="utf-8"))
    except Exception:
        OUT_FILE.write_text('{"matches": []}', encoding="utf-8")
        return

    selected = sel.get("matches") if isinstance(sel, dict) else sel
    if not isinstance(selected, list): selected = []

    out_matches = []
    for m in selected:
        start_iso = m.get("start") or ""
        duration = float(m.get("duration") or 2.2)

        t1_raw = (m.get("team1") or "match").strip()
        first_word = t1_raw.split()[0].lower() if t1_raw else "match"
        first_word = re.sub(r'[^a-z0-9]', '', first_word)
        
        match_id = first_word
        counter = 1
        while any(x.get("id") == match_id for x in out_matches):
            counter += 1
            match_id = f"{first_word}-{counter}"

        detail_url = f"https://www.yashintv.xyz/p/match-details.html?id={match_id}"

        out_matches.append({
            "id": match_id,
            "team1": { 
                "name": m.get("team1") or "TBD", 
                "img": m.get("team1_logo") or "", 
                "code": team_code(m.get("team1") or "") 
            },
            "team2": { 
                "name": m.get("team2") or "TBD", 
                "img": m.get("team2_logo") or "", 
                "code": team_code(m.get("team2") or "") 
            },
            "time": iso_to_widget_time(start_iso),
            "status": compute_status(start_iso, duration),
            "endTime": duration,
            "type": m.get("league") or "Football",
            "redirectUrl": detail_url,
        })

    OUT_FILE.write_text(json.dumps({"matches": out_matches}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(out_matches)} matches.")

if __name__ == "__main__":
    main()
