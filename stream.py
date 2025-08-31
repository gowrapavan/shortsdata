import requests
import re
import json
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import random
import os

# === Random logo placeholders from your GitHub ===
LOGOS = [
    "https://raw.githubusercontent.com/gowrapavan/Goal4u/main/public/assets/img/tv-logo/aves.png",
    "https://raw.githubusercontent.com/gowrapavan/Goal4u/main/public/assets/img/tv-logo/benfica.png",
    "https://raw.githubusercontent.com/gowrapavan/Goal4u/main/public/assets/img/tv-logo/braga.png",
    "https://raw.githubusercontent.com/gowrapavan/Goal4u/main/public/assets/img/tv-logo/fcboavista.png",
    "https://raw.githubusercontent.com/gowrapavan/Goal4u/main/public/assets/img/tv-logo/maritimo.png",
    "https://raw.githubusercontent.com/gowrapavan/Goal4u/main/public/assets/img/tv-logo/porto.png",
    "https://raw.githubusercontent.com/gowrapavan/Goal4u/main/public/assets/img/tv-logo/sporting.png",
    "https://raw.githubusercontent.com/gowrapavan/Goal4u/main/public/assets/img/tv-logo/valencia.png",
]

def random_logo():
    return random.choice(LOGOS)

# === Timezones (still used for SportsOnline) ===
IST = pytz.timezone("Asia/Kolkata")
GMT = pytz.timezone("GMT")

def convert_time(timestr, src_tz):
    """Convert HH:MM string from src timezone to IST with today's date."""
    now = datetime.now()
    dt = datetime.strptime(timestr, "%H:%M")
    dt = dt.replace(year=now.year, month=now.month, day=now.day)
    dt = src_tz.localize(dt).astimezone(IST)
    return dt.strftime("%Y-%m-%d %H:%M IST")

# ---------- 1. SportsOnline ----------
def fetch_sportzonline():
    url = "https://sportsonline.pk/prog.txt"
    text = requests.get(url).text

    today = datetime.now(IST).strftime("%A").upper()  # e.g. "SUNDAY"
    pattern = rf"{today}\n(.*?)(?=\n[A-Z]+\n|$)"
    m = re.search(pattern, text, re.S)
    if not m:
        return []

    block = m.group(1)
    matches = []

    for line in block.splitlines():
        m = re.match(r"(\d{2}:\d{2})\s+(.+?)\s+x\s+(.+?) \| (http.+)", line)
        if m:
            time_str, home, away, url = m.groups()
            time_ist = convert_time(time_str, GMT)
            matches.append({
                "time": time_ist,
                "game": "football",
                "home_team": home.strip(),
                "away_team": away.strip(),
                "label": f"{home.strip()} vs {away.strip()}",
                "Logo": random_logo(),
                "url": url.strip()
            })
    return matches

# ---------- 2. DoubleXX (updated to parse homepage iframes) ----------
def fetch_doublexx():
    url = "https://doublexx.one/"
    html = requests.get(url).text
    soup = BeautifulSoup(html, "html.parser")

    matches = []
    for i, iframe in enumerate(soup.find_all("iframe", src=True), start=1):
        src = iframe["src"]
        if src.startswith("/"):
            src = f"https://doublexx.one{src}"
        matches.append({
            "label": f"Stream {i}",
            "url": src,
            "Logo": random_logo()
        })
    return matches

# === Combine All Sources ===
def fetch_all():
    all_matches = []
    all_matches.extend(fetch_sportzonline())
    all_matches.extend(fetch_doublexx())
    return all_matches

# === Save JSONs ===
JSON_FOLDER = "json"
os.makedirs(JSON_FOLDER, exist_ok=True)

if __name__ == "__main__":
    sources = {
        "sportsonline.json": fetch_sportzonline,
        "doublexx.json": fetch_doublexx
    }

    for filename, func in sources.items():
        data = func()
        with open(os.path.join(JSON_FOLDER, filename), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Saved {filename} with {len(data)} entries")
