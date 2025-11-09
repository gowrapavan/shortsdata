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

# ===============================
# 🏟️ LOAD TEAM CRESTS FROM JSONS
# ===============================
TEAM_JSONS = {
    "EPL": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/EPL.json",
    "ESP": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/ESP.json",
    "ITSA": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/ITSA.json",
    "FRL1": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/FRL1.json",
    "DED": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/DED.json",
    "DEB": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/DEB.json",
}

TEAM_LOGO_MAP = {}

def load_team_logos():
    """Load team crest URLs from multiple league JSONs."""
    global TEAM_LOGO_MAP
    for code, url in TEAM_JSONS.items():
        try:
            res = requests.get(url, timeout=10)
            teams = res.json()
            for team in teams:
                name = team.get("name", "").lower()
                short_name = team.get("shortName", "").lower()
                tla = team.get("tla", "").lower()
                crest = team.get("crest", "")
                if name:
                    TEAM_LOGO_MAP[name] = crest
                if short_name:
                    TEAM_LOGO_MAP[short_name] = crest
                if tla:
                    TEAM_LOGO_MAP[tla] = crest
        except Exception as e:
            print(f"⚠️ Failed to load {code}: {e}")

def find_team_logo(team_name):
    """Try to find crest by fuzzy team name."""
    name = team_name.lower().strip()
    for key, logo in TEAM_LOGO_MAP.items():
        if key in name or name in key:
            return logo
    return random_logo()

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

            # ✅ Try to fetch crest for home team
            logo = find_team_logo(home)

            matches.append({
                "time": time_ist,
                "game": "football",
                "league": "",
                "home_team": home.strip(),
                "away_team": away.strip(),
                "label": short_label(home, away),
                "Logo": logo,
                "url": url.strip()
            })
    return matches

# ---------- 2. Hesgoal ----------
def fetch_hesgoal():
    url = "https://hesgoal.im/today-matches/"
    headers = {"User-Agent": "Mozilla/5.0"}
    html = requests.get(url, headers=headers, timeout=10).text
    soup = BeautifulSoup(html, "html.parser")

    matches = []

    for event in soup.select("div.EventBox"):
        teams = event.select("div.EventTeamName")
        if len(teams) < 2:
            continue
        home = teams[1].text.strip()
        away = teams[0].text.strip()

        league_tag = event.select_one("ul.EventFooter li:nth-child(3)")
        league = league_tag.text.strip() if league_tag else ""

        link_tag = event.select_one("a#EventLink")
        if not link_tag or "href" not in link_tag.attrs:
            continue
        href = link_tag["href"].strip()
        slug = href.rstrip("/").split("/")[-1]
        yalla_url = f"https://yallashoot.mobi/albaplayer/{slug}/"

        date_tag = event.select_one("span.EventDate")
        if date_tag and "data-start" in date_tag.attrs:
            dt_str = date_tag["data-start"].strip()
            dt = datetime.fromisoformat(dt_str)
            dt_ist = dt.astimezone(IST)
            time_ist = dt_ist.strftime("%Y-%m-%d %H:%M IST")
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

# ---------- 3. LiveKora ----------
def fetch_livekora():
    url = "https://www.livekora.vip/"
    headers = {"User-Agent": "Mozilla/5.0"}
    html = requests.get(url, headers=headers, timeout=10).text
    soup = BeautifulSoup(html, "html.parser")

    matches = []
    for a_tag in soup.select("div.benacer-matches-container a[href]"):
        href = a_tag["href"].strip()
        slug = href.rstrip("/").split("/")[-1]
        albaplayer_url = f"https://pl.yallashooot.video/albaplayer/{slug}/"

        right_team_name = a_tag.select_one("div.right-team .team-name")
        left_team_name = a_tag.select_one("div.left-team .team-name")
        home = right_team_name.text.strip() if right_team_name else ""
        away = left_team_name.text.strip() if left_team_name else ""

        home_logo_tag = a_tag.select_one("div.right-team .team-logo img")
        home_logo = home_logo_tag["src"].strip() if home_logo_tag and "src" in home_logo_tag.attrs else random_logo()

        time_tag = a_tag.select_one("div.match-container span.date")
        if time_tag and time_tag.has_attr("data-start"):
            dt_str = time_tag["data-start"].strip()
            dt = datetime.fromisoformat(dt_str)
            dt_ist = dt.astimezone(IST)
            time_ist = dt_ist.strftime("%Y-%m-%d %H:%M IST")
        else:
            time_ist = ""

        matches.append({
            "time": time_ist,
            "game": "football",
            "league": "",
            "home_team": home,
            "away_team": away,
            "label": short_label(home, away) if home and away else "livekora-stream",
            "Logo": home_logo,
            "url": albaplayer_url
        })

    return matches

# === Save JSONs ===
JSON_FOLDER = "json"
os.makedirs(JSON_FOLDER, exist_ok=True)

if __name__ == "__main__":
    print("⏳ Loading team crests...")
    load_team_logos()
    print(f"✅ Loaded {len(TEAM_LOGO_MAP)} team logos from all leagues.\n")

    sources = {
        "sportsonline.json": fetch_sportzonline,
        "hesgoal.json": fetch_hesgoal,
        "livekora.json": fetch_livekora
    }

    for filename, func in sources.items():
        try:
            data = func()
            with open(os.path.join(JSON_FOLDER, filename), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✅ Saved {filename} with {len(data)} entries")
        except Exception as e:
            print(f"❌ Failed to fetch {filename}: {e}")
            with open(os.path.join(JSON_FOLDER, filename), "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)
