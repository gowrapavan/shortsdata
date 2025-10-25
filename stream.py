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

# === Timezones ===
IST = pytz.timezone("Asia/Kolkata")
GMT = pytz.timezone("GMT")

def convert_time(timestr, src_tz):
    """Convert HH:MM string from src timezone to IST with today's date."""
    now = datetime.now()
    dt = datetime.strptime(timestr, "%H:%M")
    dt = dt.replace(year=now.year, month=now.month, day=now.day)
    dt = src_tz.localize(dt).astimezone(IST)
    return dt.strftime("%Y-%m-%d %H:%M IST")

def short_label(home, away):
    """Generate short label like bri-man."""
    h = re.sub(r'[^a-z]', '', home.lower())[:3] or home.lower()[:3]
    a = re.sub(r'[^a-z]', '', away.lower())[:3] or away.lower()[:3]
    return f"{h}-{a}"

# ---------- 1. SportsOnline ----------
def fetch_sportzonline():
    url = "https://sportsonline.pk/prog.txt"
    text = requests.get(url, timeout=10).text

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
                "league": "",
                "home_team": home.strip(),
                "away_team": away.strip(),
                "label": short_label(home, away),
                "Logo": random_logo(),
                "url": url.strip()
            })
    return matches

# ---------- 2. DoubleXX (homepage iframes) ----------
def fetch_doublexx():
    url = "https://doublexx.one/"
    headers = {"User-Agent": "Mozilla/5.0"}
    html = requests.get(url, headers=headers, timeout=10).text
    soup = BeautifulSoup(html, "html.parser")

    matches = []
    for i, iframe in enumerate(soup.find_all("iframe", src=True), start=1):
        src = iframe["src"].strip()
        if src.startswith("/"):
            src = f"https://doublexx.one{src}"
        elif not src.startswith("http"):
            src = f"https://doublexx.one/{src.lstrip('/')}"
        matches.append({
            "time": "",
            "game": "football",
            "league": "",
            "home_team": "",
            "away_team": "",
            "label": f"stream-{i}",
            "Logo": random_logo(),
            "url": src
        })
    return matches

# ---------- 3. Koora10 (alkoora.txt) ----------
def fetch_koora10():
    url = "https://cdn34.koora10.live/alkoora.txt"
    text = requests.get(url, timeout=10).text

    matches = []
    for line in text.splitlines():
        m = re.match(r"(\d{2}:\d{2})\s+(.+?) vs (.+?) \| (http.+)", line)
        if m:
            time_str, home, away, link = m.groups()
            # Koora uses GMT+3
            time_ist = convert_time(time_str, pytz.timezone("Etc/GMT-3"))
            matches.append({
                "time": time_ist,
                "game": "football",
                "league": "",
                "home_team": home.strip(),
                "away_team": away.strip(),
                "label": short_label(home, away),
                "Logo": random_logo(),
                "url": link.strip()
            })
    return matches
    # ---------- 4. Hesgoal ----------
def fetch_hesgoal():
    url = "https://hesgoal.im/today-matches/"
    headers = {"User-Agent": "Mozilla/5.0"}
    html = requests.get(url, headers=headers, timeout=10).text
    soup = BeautifulSoup(html, "html.parser")

    matches = []

    for event in soup.select("div.EventBox"):
        # Extract home and away teams
        teams = event.select("div.EventTeamName")
        if len(teams) < 2:
            continue
        home = teams[1].text.strip()  # Right team is home
        away = teams[0].text.strip()  # Left team is away

        # Extract league
        league_tag = event.select_one("ul.EventFooter li:nth-child(3)")
        league = league_tag.text.strip() if league_tag else ""

        # Extract match URL and convert to yallashoot format
        link_tag = event.select_one("a#EventLink")
        if not link_tag or "href" not in link_tag.attrs:
            continue
        href = link_tag["href"].strip()
        # Example: https://hesgoal.im/manchester-united-vs-brighton -> manchester-united-vs-brighton
        slug = href.rstrip("/").split("/")[-1]
        yalla_url = f"https://yallashoot.mobi/albaplayer/{slug}/"

        # Extract match time (data-start) and convert GMT+3 to IST
        date_tag = event.select_one("span.EventDate")
        if date_tag and "data-start" in date_tag.attrs:
            dt_str = date_tag["data-start"].strip()
            dt = datetime.fromisoformat(dt_str)  # Hesgoal is GMT+3
            dt = pytz.timezone("Etc/GMT-3").localize(dt).astimezone(IST)
            time_ist = dt.strftime("%Y-%m-%d %H:%M IST")
        else:
            time_ist = ""

        matches.append({
            "time": time_ist,
            "game": "football",
            "league": league,
            "home_team": home,
            "away_team": away,
            "label": short_label(home, away),
            "Logo": random_logo(),
            "url": yalla_url
        })

    return matches
# ---------- 4. Hesgoal ----------
def fetch_hesgoal():
    url = "https://hesgoal.im/today-matches/"
    headers = {"User-Agent": "Mozilla/5.0"}
    html = requests.get(url, headers=headers, timeout=10).text
    soup = BeautifulSoup(html, "html.parser")

    matches = []

    for event in soup.select("div.EventBox"):
        # Extract home and away teams
        teams = event.select("div.EventTeamName")
        if len(teams) < 2:
            continue
        home = teams[1].text.strip()  # Right team is home
        away = teams[0].text.strip()  # Left team is away

        # Extract league
        league_tag = event.select_one("ul.EventFooter li:nth-child(3)")
        league = league_tag.text.strip() if league_tag else ""

        # Extract match URL and convert to yallashoot format
        link_tag = event.select_one("a#EventLink")
        if not link_tag or "href" not in link_tag.attrs:
            continue
        href = link_tag["href"].strip()
        # Example: https://hesgoal.im/manchester-united-vs-brighton -> manchester-united-vs-brighton
        slug = href.rstrip("/").split("/")[-1]
        yalla_url = f"https://yallashoot.mobi/albaplayer/{slug}/"

        # Extract match time (data-start) and convert GMT+3 to IST
        date_tag = event.select_one("span.EventDate")
        if date_tag and "data-start" in date_tag.attrs:
            dt_str = date_tag["data-start"].strip()
            dt = datetime.fromisoformat(dt_str)  # Hesgoal is GMT+3
            dt = pytz.timezone("Etc/GMT-3").localize(dt).astimezone(IST)
            time_ist = dt.strftime("%Y-%m-%d %H:%M IST")
        else:
            time_ist = ""

        matches.append({
            "time": time_ist,
            "game": "football",
            "league": league,
            "home_team": home,
            "away_team": away,
            "label": short_label(home, away),
            "Logo": random_logo(),
            "url": yalla_url
        })

    return matches



# === Save JSONs ===
JSON_FOLDER = "json"
os.makedirs(JSON_FOLDER, exist_ok=True)

if __name__ == "__main__":
    sources = {
        "sportsonline.json": fetch_sportzonline,
        "doublexx.json": fetch_doublexx,
        "koora10.json": fetch_koora10,
        "hesgoal.json": fetch_hesgoal

    }

    for filename, func in sources.items():
        try:
            data = func()
            with open(os.path.join(JSON_FOLDER, filename), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✅ Saved {filename} with {len(data)} entries")
        except Exception as e:
            # If one fails, continue with others
            print(f"❌ Failed to fetch {filename}: {e}")
            with open(os.path.join(JSON_FOLDER, filename), "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)
