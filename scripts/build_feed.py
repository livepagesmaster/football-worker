#!/usr/bin/env python3
"""

"""

import json
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

SEL_FILE = DATA_DIR / "selected.json"
OUT_FILE = DATA_DIR / "matchfeed.json"


def team_code(name: str) -> str:
    """Make a short 3-letter code from a team name."""
    if not name:
        return "???"
    clean = name.replace("FC", "").replace("AFC", "").strip()
    words = clean.split()
    if len(words) >= 3:
        return "".join(w[0] for w in words[:3]).upper()
    return clean[:3].upper()


def iso_to_widget_time(iso: str) -> str:
    """2026-10-15T16:45Z -> 26/10/15 16:45:00 (Nepal time)."""
    if not iso:
        return ""
    try:
        # Parse ISO with Z
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        # Convert to Nepal time (UTC+5:45)
        from datetime import timedelta
        nepal = dt.astimezone(timezone(timedelta(hours=5, minutes=45)))
        return nepal.strftime("%y/%m/%d %H:%M:%S")
    except Exception:
        return ""


def compute_status(start_iso: str, duration_hours: float) -> str:
    """Upcoming / LIVE / Ended based on current time."""
    if not start_iso:
        return "Upcoming"
    try:
        s = datetime.fromisoformat(start_iso.replace("Z", "+00:00")).timestamp()
        end = s + (duration_hours or 2.2) * 3600
        now = datetime.now(timezone.utc).timestamp()
        if now >= end:
            return "Ended"
        if now >= s:
            return "LIVE"
        return "Upcoming"
    except Exception:
        return "Upcoming"


def main():
    if not SEL_FILE.exists():
        print(f"No {SEL_FILE} — writing empty feed.")
        OUT_FILE.write_text('{"matches": []}', encoding="utf-8")
        return

    try:
        sel = json.loads(SEL_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Failed to parse {SEL_FILE}: {e}")
        OUT_FILE.write_text('{"matches": []}', encoding="utf-8")
        return

    selected = sel.get("matches") if isinstance(sel, dict) else sel
    if not isinstance(selected, list):
        selected = []

    out_matches = []
    for m in selected:
        # The dashboard saves full match objects — we just reshape.
        start_iso = m.get("start") or ""
        duration = float(m.get("duration") or 2.2)

        # Generate the unique ID for the URL (e.g. real-betis-vs-barcelona)
        t1_slug = (m.get("team1") or "team1").strip().lower().replace(" ", "-")
        t2_slug = (m.get("team2") or "team2").strip().lower().replace(" ", "-")
        eid = m.get("event_id") or ""
        match_id = f"{t1_slug}-vs-{t2_slug}-{eid}"

        out_matches.append({
            "id": match_id, # <--- THIS IS THE UNIQUE ID
            "team1": {
                "name": m.get("team1") or "TBD",
                "img": m.get("team1_logo") or "",
                "code": team_code(m.get("team1") or ""),
            },
            "team2": {
                "name": m.get("team2") or "TBD",
                "img": m.get("team2_logo") or "",
                "code": team_code(m.get("team2") or ""),
            },
            "time": iso_to_widget_time(start_iso),
            "status": compute_status(start_iso, duration),
            "endTime": duration,
            "type": m.get("league") or "Football",
            "redirectUrl": f"https://www.yashintv.xyz/match-details.html?id={match_id}",
        })

    OUT_FILE.write_text(
        json.dumps({"matches": out_matches}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(out_matches)} matches -> {OUT_FILE}")


if __name__ == "__main__":
    main()
