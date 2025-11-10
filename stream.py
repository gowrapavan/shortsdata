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
    now = datetime.now()
    dt = datetime.strptime(timestr, "%H:%M")
    dt = dt.replace(year=now.year, month=now.month, day=now.day)
    dt = src_tz.localize(dt).astimezone(IST)
    return dt.strftime("%Y-%m-%d %H:%M IST")


def short_label(home, away):
    h = re.sub(r'[^a-z]', '', home.lower())[:3] or home.lower()[:3]
    a = re.sub(r'[^a-z]', '', away.lower())[:3] or away.lower()[:3]
    return f"{h}-{a}"


# === Load Team Data from GitHub ===
TEAM_SOURCES = {
    "EPL": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/EPL.json",
    "ESP": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/ESP.json",
    "FRL1": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/FRL1.json",
    "ITSA": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/ITSA.json",
    "DED": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/DED.json",
    "WC": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/WC.json",
    "DEB": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/DEB.json",
}

TEAM_DATA = []

def load_team_data():
    global TEAM_DATA
    if TEAM_DATA:
        return TEAM_DATA
    for name, url in TEAM_SOURCES.items():
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list):
                    TEAM_DATA.extend(data)
                elif isinstance(data, dict) and "teams" in data:
                    TEAM_DATA.extend(data["teams"])
        except Exception as e:
            print(f"⚠️ Failed loading {name}: {e}")
    print(f"✅ Loaded {len(TEAM_DATA)} teams total.")
    return TEAM_DATA


def find_team_crest(team_name):
    if not TEAM_DATA:
        load_team_data()
    name = team_name.lower().strip()
    for team in TEAM_DATA:
        if "name" in team and name in team["name"].lower():
            return team.get("crest") or team.get("logo") or random_logo()
    return random_logo()


# ---------- 1. SportsOnline ----------
def fetch_sportzonline():
    load_team_data()
    url = "https://sportsonline.pk/prog.txt"
    text = requests.get(url, timeout=10).text

    today = datetime.now(IST).strftime("%A").upper()
    m = re.search(rf"{today}\n(.*?)(?=\n[A-Z]+\n|$)", text, re.S)
    if not m:
        return []
    block = m.group(1)
    matches = []

    for line in block.splitlines():
        m = re.match(r"(\d{2}:\d{2})\s+(.+?)\s+x\s+(.+?) \| (http.+)", line)
        if m:
            time_str, home, away, link = m.groups()
            matches.append({
                "time": convert_time(time_str, GMT),
                "game": "football",
                "league": "",
                "home_team": home.strip(),
                "away_team": away.strip(),
                "label": short_label(home, away),
                "home_logo": find_team_crest(home),
                "away_logo": find_team_crest(away),
                "url": link.strip()
            })
    return matches


# ---------- 2. Hesgoal ----------
def fetch_hesgoal():
    load_team_data()
    url = "https://hesgoal.im/today-matches/"
    soup = BeautifulSoup(requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).text, "html.parser")

    matches = []
    for e in soup.select("div.EventBox"):
        teams = e.select("div.EventTeamName")
        if len(teams) < 2:
            continue
        home, away = teams[1].text.strip(), teams[0].text.strip()
        league = e.select_one("ul.EventFooter li:nth-child(3)")
        league = league.text.strip() if league else ""

        link_tag = e.select_one("a#EventLink")
        if not link_tag or "href" not in link_tag.attrs:
            continue
        href = link_tag["href"].strip()
        slug = href.rstrip("/").split("/")[-1]
        stream_url = f"https://yallashoot.mobi/albaplayer/{slug}/"

        date_tag = e.select_one("span.EventDate[data-start]")
        if date_tag:
            dt = datetime.fromisoformat(date_tag["data-start"]).astimezone(IST)
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
            "home_logo": find_team_crest(home),
            "away_logo": find_team_crest(away),
            "url": stream_url
        })
    return matches


# ---------- 3. YallaShooote ----------
def fetch_yallashooote():
    """Scrape yallashooote.online and use crest lookup."""
    load_team_data()
    soup = BeautifulSoup(requests.get("https://yallashooote.online/", headers={"User-Agent": "Mozilla/5.0"}).text, "html.parser")

    matches = []
    for div in soup.select("div.m_block.alba_sports_events-event_item"):
        link = div.select_one("a.alba_sports_events_link")
        if not link or "href" not in link.attrs:
            continue
        href = link["href"].strip()
        iframe_url = f"https://yallashooote.online/live/{href.lstrip('/')}.php" if href.startswith("/") else href

        home_tag = div.select_one(".team-first .alba_sports_events-team_title")
        away_tag = div.select_one(".team-second .alba_sports_events-team_title")
        home = home_tag.text.strip() if home_tag else ""
        away = away_tag.text.strip() if away_tag else ""

        date_tag = div.select_one("div.date[data-start]")
        if date_tag:
            try:
                dt = datetime.strptime(date_tag["data-start"], "%Y/%m/%d %H:%M")
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
            "label": short_label(home, away),
            "home_logo": find_team_crest(home),
            "away_logo": find_team_crest(away),
            "url": iframe_url
        })
    return matches


# ---------- 4. LiveKora ----------
def fetch_livekora():
    load_team_data()
    soup = BeautifulSoup(requests.get("https://www.livekora.vip/", headers={"User-Agent": "Mozilla/5.0"}).text, "html.parser")

    matches = []
    for tag in soup.select("div.benacer-matches-container a[href]"):
        href = tag["href"].strip()
        slug = href.rstrip("/").split("/")[-1]
        stream_url = f"https://pl.yalashoot.xyz/albaplayer/{slug}/?serv=0"

        home_tag = tag.select_one(".right-team .team-name")
        away_tag = tag.select_one(".left-team .team-name")
        home = home_tag.text.strip() if home_tag else ""
        away = away_tag.text.strip() if away_tag else ""

        date_tag = tag.select_one("span.date[data-start]")
        if date_tag:
            try:
                dt = datetime.fromisoformat(date_tag["data-start"]).astimezone(IST)
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
            "label": short_label(home, away),
            "home_logo": find_team_crest(home),
            "away_logo": find_team_crest(away),
            "url": stream_url
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
        "livekora.json": fetch_livekora,
    }

    for fname, func in sources.items():
        try:
            data = func()
            with open(os.path.join(JSON_FOLDER, fname), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✅ Saved {fname} with {len(data)} entries")
        except Exception as e:
            print(f"❌ Failed to fetch {fname}: {e}")
            with open(os.path.join(JSON_FOLDER, fname), "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)
