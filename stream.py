import requests
import re
import json
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import random

# === Random logo placeholder (comment this out later) ===
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


# === Timezones ===
IST = pytz.timezone("Asia/Kolkata")
GMT = pytz.timezone("GMT")
GMT_PLUS3 = pytz.FixedOffset(180)  # Koora timezone

def convert_time(timestr, src_tz):
    """Convert HH:MM string from src timezone to IST (with date shift)."""
    now = datetime.now()
    dt = datetime.strptime(timestr, "%H:%M")
    dt = dt.replace(year=now.year, month=now.month, day=now.day)
    dt = src_tz.localize(dt).astimezone(IST)
    return dt.strftime("%Y-%m-%d %H:%M IST")

# ---------- 1. Koora ----------
def fetch_koora():
    url = "https://cdn22.koora10.live/alkoora.txt"
    text = requests.get(url).text

    matches_dict = {}
    for line in text.splitlines():
        m = re.match(r"(\d{2}:\d{2}) (.+?) vs (.+?) \| (http.+)", line)
        if m:
            time_gmt3, home, away, link = m.groups()
            time_ist = convert_time(time_gmt3, GMT_PLUS3)
            key = f"{home.strip()} vs {away.strip()} {time_ist}"

            if key not in matches_dict:
                matches_dict[key] = {
                    "time": time_ist,
                    "game": "football",
                    "home_team": home.strip(),
                    "away_team": away.strip(),
                    "label": f"{home.strip()} vs {away.strip()}",
                    "url": link.strip(),
                    "Logo": random_logo(),
                }
            else:
                # add url2, url3...
                next_index = len([k for k in matches_dict[key] if k.startswith("url")]) + 1
                matches_dict[key][f"url{next_index}"] = link.strip()

    return list(matches_dict.values())

# ---------- 2. SportsOnline ----------
def fetch_sportzonline():
    url = "https://sportsonline.pk/prog.txt"
    text = requests.get(url).text

    # figure out today's weekday name
    today = datetime.now(IST).strftime("%A").upper()   # e.g. "SUNDAY"

    # find today’s block
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
            time_ist = convert_time(time_str, GMT)  # source is GMT!
            match = {
                "time": time_ist,
                "game": "football",
                "home_team": home.strip(),
                "away_team": away.strip(),
                "label": f"{home.strip()} vs {away.strip()}",
                "url": url.strip(),
                "Logo": random_logo()
            }
            matches.append(match)
    return matches

# ---------- 3. Elixx ----------
def fetch_elixx():
    url = "https://elixx.cc/schedule.html"
    html = requests.get(url).text
    soup = BeautifulSoup(html, "html.parser")

    today_str = datetime.now().strftime("%d.%m.%Y")
    header = soup.find("h4", string=re.compile(today_str))
    matches_dict = {}

    if not header:
        return []

    for btn in header.find_all_next("button", class_="accordion"):
        if btn.find_previous("h4") != header:
            break
        text = btn.get_text(" ", strip=True)
        time_m = re.match(r"(\d{2}:\d{2})\s+(.+?) vs (.+)", text)
        if time_m:
            time_utc, home, away = time_m.groups()
            time_ist = convert_time(time_utc, GMT)  # Elixx times in UTC
            key = f"{home.strip()} vs {away.strip()} {time_ist}"

            # convert .html to .php in links
            links = [a['href'].replace(".html", ".php") for a in btn.find_next_siblings("div")[0].find_all("a", href=True)]

            if key not in matches_dict:
                matches_dict[key] = {
                    "time": time_ist,
                    "game": "football",
                    "home_team": home.strip(),
                    "away_team": away.strip(),
                    "Logo": random_logo(),
                    "label": f"{home.strip()} vs {away.strip()}",
                }
                for i, link in enumerate(links, start=1):
                    matches_dict[key][f"url{i}"] = link
            else:
                # append more links
                existing_urls = [k for k in matches_dict[key] if k.startswith("url")]
                next_index = len(existing_urls) + 1
                for link in links:
                    matches_dict[key][f"url{next_index}"] = link
                    next_index += 1

    return list(matches_dict.values())


# === Combine All ===
def fetch_all():
    all_matches = []
    all_matches.extend(fetch_koora())
    all_matches.extend(fetch_sportzonline())
    all_matches.extend(fetch_elixx())
    return all_matches

import os

# Folder for JSONs
JSON_FOLDER = "json"
os.makedirs(JSON_FOLDER, exist_ok=True)

if __name__ == "__main__":
    koora_data = fetch_koora()
    sportsonline_data = fetch_sportzonline()
    elixx_data = fetch_elixx()

    with open(os.path.join(JSON_FOLDER, "koora.json"), "w", encoding="utf-8") as f:
        json.dump(koora_data, f, ensure_ascii=False, indent=2)

    with open(os.path.join(JSON_FOLDER, "sportsonline.json"), "w", encoding="utf-8") as f:
        json.dump(sportsonline_data, f, ensure_ascii=False, indent=2)

    with open(os.path.join(JSON_FOLDER, "elixx.json"), "w", encoding="utf-8") as f:
        json.dump(elixx_data, f, ensure_ascii=False, indent=2)

    print("Saved koora.json with", len(koora_data), "matches")
    print("Saved sportsonline.json with", len(sportsonline_data), "matches")
    print("Saved elixx.json with", len(elixx_data), "matches")
