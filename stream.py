import requests
import re
import json
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
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

# === Timezones ===
IST = pytz.timezone("Asia/Kolkata")
GMT = pytz.timezone("GMT")
GMT_PLUS3 = pytz.FixedOffset(180)  # Koora timezone

def convert_time(timestr, src_tz):
    """Convert HH:MM string from src timezone to IST with today's date."""
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
                    "Logo": random_logo(),
                    "url1": link.strip(),
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

# ---------- 3. DoubleXX ----------
def fetch_doublexx():
    url = "https://doublexx.one/schedule.html"
    html = requests.get(url).text
    soup = BeautifulSoup(html, "html.parser")

    today_str = datetime.now().strftime("%d.%m.%Y")
    header = soup.find("h4", string=re.compile(today_str))
    if not header:
        return []

    matches_dict = {}
    for btn in header.find_all_next("button", class_="accordion"):
        if btn.find_previous("h4") != header:
            break

        text = btn.get_text(" ", strip=True)
        time_m = re.match(r"(\d{2}:\d{2})\s+(.+?) vs (.+)", text)
        if not time_m:
            continue

        time_utc, home, away = time_m.groups()
        time_ist = convert_time(time_utc, GMT)  # times in UTC
        key = f"{home.strip()} vs {away.strip()} {time_ist}"

        links = []
        div_siblings = btn.find_next_siblings("div")
        if div_siblings:
            for a in div_siblings[0].find_all("a", href=True):
                href = a['href']
                if href.endswith(".html"):
                    href = href.replace(".html", ".php")
                href = re.sub(r"(https://doublexx\.one/)", r"\1aw/", href)
                links.append(href)

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
            existing_urls = [k for k in matches_dict[key] if k.startswith("url")]
            next_index = len(existing_urls) + 1
            for link in links:
                matches_dict[key][f"url{next_index}"] = link
                next_index += 1

    return list(matches_dict.values())

# === Combine All Sources ===
def fetch_all():
    all_matches = []
    all_matches.extend(fetch_koora())
    all_matches.extend(fetch_sportzonline())
    all_matches.extend(fetch_doublexx())  # updated
    return all_matches

# === Save JSONs ===
JSON_FOLDER = "json"
os.makedirs(JSON_FOLDER, exist_ok=True)

if __name__ == "__main__":
    sources = {
        "koora.json": fetch_koora,
        "sportsonline.json": fetch_sportzonline,
        "doublexx.json": fetch_doublexx
    }

    for filename, func in sources.items():
        data = func()
        with open(os.path.join(JSON_FOLDER, filename), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Saved {filename} with {len(data)} matches")
