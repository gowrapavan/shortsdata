#!/usr/bin/env python3
import requests
import re
import json
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import random
import os

# === Random logo placeholders ===
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


# === Load Team Data from GitHub (includes WC) ===
TEAM_SOURCES = {
    "EPL": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/EPL.json",
    "ESP": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/ESP.json",
    "FRL1": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/FRL1.json",
    "ITSA": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/ITSA.json",
    "DED": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/DED.json",
    "DEB": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/DEB.json",
    "WC": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/WC.json",
}

TEAM_DATA = []

def load_team_data():
    """Load and cache all team data from GitHub sources, including World Cup teams."""
    global TEAM_DATA
    if TEAM_DATA:
        return TEAM_DATA

    for name, url in TEAM_SOURCES.items():
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                # WC file has nested structure: [{ "teams": [...] }]
                if name == "WC":
                    if isinstance(data, list) and len(data) > 0 and "teams" in data[0]:
                        TEAM_DATA.extend(data[0]["teams"])
                else:
                    TEAM_DATA.extend(data)
        except Exception as e:
            print(f"⚠️ Failed loading {name}: {e}")

    print(f"✅ Loaded {len(TEAM_DATA)} total teams from GitHub sources")
    return TEAM_DATA


def find_team_crest(team_name):
    """Find crest URL for given team name."""
    team_name_low = team_name.lower()

    # Try exact or short name match
    for team in TEAM_DATA:
        if team_name_low in team["name"].lower() or team_name_low in team.get("shortName", "").lower():
            return team.get("crest")

    # Try partial (first word) match
    for team in TEAM_DATA:
        if team_name_low.split()[0] in team["name"].lower():
            return team.get("crest")

    # Try by area name (for national teams in WC)
    for team in TEAM_DATA:
        area = team.get("area", {}).get("name", "").lower()
        if area and (area in team_name_low or team_name_low in area):
            return team.get("crest")

    return random_logo()


# ---------- 1. SportsOnline ----------
def fetch_sportzonline():
    load_team_data()
    url = "https://sportsonline.pk/prog.txt"
    text = requests.get(url, timeout=10).text

    today = datetime.now(IST).strftime("%A").upper()
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
            home_logo = find_team_crest(home.strip())
            away_logo = find_team_crest(away.strip())

            matches.append({
                "time": time_ist,
                "game": "football",
                "league": "",
                "home_team": home.strip(),
                "away_team": away.strip(),
                "label": short_label(home, away),
                "home_logo": home_logo,
                "away_logo": away_logo,
                "url": url.strip()
            })
    return matches


# ---------- 2. Hesgoal ----------
def fetch_hesgoal():
    load_team_data()
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

        imgs = event.select("img")
        home_logo = imgs[1]["data-img"] if len(imgs) > 1 and imgs[1].has_attr("data-img") else find_team_crest(home)
        away_logo = imgs[0]["data-img"] if imgs and imgs[0].has_attr("data-img") else find_team_crest(away)

        matches.append({
            "time": time_ist,
            "game": "football",
            "league": league,
            "home_team": home,
            "away_team": away,
            "label": short_label(home, away),
            "home_logo": home_logo or random_logo(),
            "away_logo": away_logo or random_logo(),
            "url": yalla_url
        })
    return matches


# ---------- 3. YallaShooote ----------
def fetch_yallashooote():
    """Scrape yallashooote.online and convert short /beinX links to iframe URLs."""
    load_team_data()
    url = "https://yallashooote.online/"
    headers = {"User-Agent": "Mozilla/5.0"}
    html = requests.get(url, headers=headers, timeout=10).text
    soup = BeautifulSoup(html, "html.parser")

    matches = []
    for div in soup.select("div.m_block.alba_sports_events-event_item"):
        link_tag = div.select_one("a.alba_sports_events_link")
        if not link_tag or "href" not in link_tag.attrs:
            continue

        href = link_tag["href"].strip()
        iframe_url = f"https://yallashooote.online/live/{href.lstrip('/')}.php" if href.startswith("/") else href

        home_tag = div.select_one("div.team-first .alba_sports_events-team_title")
        away_tag = div.select_one("div.team-second .alba_sports_events-team_title")
        home = home_tag.text.strip() if home_tag else ""
        away = away_tag.text.strip() if away_tag else ""

        home_logo = find_team_crest(home)
        away_logo = find_team_crest(away)

        date_tag = div.select_one("div.date[data-start]")
        if date_tag and "data-start" in date_tag.attrs:
            try:
                dt_str = date_tag["data-start"].strip()
                dt = datetime.strptime(dt_str, "%Y/%m/%d %H:%M")
                dt = GMT.localize(dt).astimezone(IST)
                time_ist = dt.strftime("%Y-%m-%d %H:%M IST")
            except Exception:
                time_ist = ""
        else:
            time_ist = ""

        matches.append({
            "time": time_ist,
            "game": "football",
            "league": "",
            "home_team": home,
            "away_team": away,
            "label": short_label(home, away) if home and away else "yalla-stream",
            "home_logo": home_logo,
            "away_logo": away_logo,
            "url": iframe_url
        })

    return matches


# ---------- 4. LiveKora ----------
def fetch_livekora():
    """Scrape livekora.vip and extract both home and away logos."""
    load_team_data()
    url = "https://www.livekora.vip/"
    headers = {"User-Agent": "Mozilla/5.0"}
    html = requests.get(url, headers=headers, timeout=10).text
    soup = BeautifulSoup(html, "html.parser")

    matches = []
    for a_tag in soup.select("div.benacer-matches-container a[href]"):
        href = a_tag["href"].strip()
        slug = href.rstrip("/").split("/")[-1]
        albaplayer_url = f"https://pl.yalashoot.xyz/albaplayer/{slug}/?serv=0"

        home_tag = a_tag.select_one("div.right-team .team-name")
        away_tag = a_tag.select_one("div.left-team .team-name")
        home = home_tag.text.strip() if home_tag else ""
        away = away_tag.text.strip() if away_tag else ""

        home_logo = find_team_crest(home)
        away_logo = find_team_crest(away)

        time_tag = a_tag.select_one("div.match-container span.date")
        if time_tag and time_tag.has_attr("data-start"):
            try:
                dt_str = time_tag["data-start"].strip()
                dt = datetime.fromisoformat(dt_str)
                dt_ist = dt.astimezone(IST)
                time_ist = dt_ist.strftime("%Y-%m-%d %H:%M IST")
            except Exception:
                time_ist = ""
        else:
            time_ist = ""

        matches.append({
            "time": time_ist,
            "game": "football",
            "league": "",
            "home_team": home,
            "away_team": away,
            "label": short_label(home, away) if home and away else "livekora-stream",
            "home_logo": home_logo,
            "away_logo": away_logo,
            "url": albaplayer_url
        })

    return matches


# === Save JSONs ===
JSON_FOLDER = "json"
os.makedirs(JSON_FOLDER, exist_ok=True)

if __name__ == "__main__":
    sources = {
        "sportsonline.json": fetch_sportzonline,
        "hesgoal.json": fetch_hesgoal,
        "yallashooote.json": fetch_yallashooote,
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
