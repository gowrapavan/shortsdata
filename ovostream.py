import requests
import re
import json
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import random
import os
from urllib.parse import urlparse, parse_qs


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


def short_label(home, away):
    """Generate short label like bri-man."""
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
    "DEB": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/DEB.json",
}

TEAM_DATA = []


def load_team_data():
    global TEAM_DATA
    if TEAM_DATA:
        return TEAM_DATA

    for name, url in TEAM_SOURCES.items():
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                TEAM_DATA.extend(resp.json())
        except Exception as e:
            print(f"⚠️ Failed loading {name}: {e}")

    return TEAM_DATA


def find_team_crest(team_name):
    """Find crest URL for given team name."""
    team_name_low = team_name.lower()

    for team in TEAM_DATA:
        if team_name_low in team["name"].lower() or team_name_low in team.get("shortName", "").lower():
            return team.get("crest")

    for team in TEAM_DATA:
        if team_name_low.split()[0] in team["name"].lower():
            return team.get("crest")

    return random_logo()


# ---------- Ovogoal Scraper ----------
def fetch_ovogoal():
    """
    Scrape ovogoal.plus
    - Extract matches from div.stream-row
    - Open each match-updates page
    - Extract iframe src as final stream URL
    """

    load_team_data()

    url = "https://ovogoal.plus/"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        html = requests.get(url, headers=headers, timeout=10).text
    except Exception as e:
        print("❌ Ovogoal homepage fetch failed:", e)
        return []

    soup = BeautifulSoup(html, "html.parser")
    matches = []

    for row in soup.select("div.stream-row"):

        # -----------------------------
        # League (from data-category)
        # -----------------------------
        league = row.get("data-category", "").strip()

        # -----------------------------
        # Time (HH:MM, no timezone info)
        # -----------------------------
        time_tag = row.select_one("div.stream-time")
        time_raw = time_tag.text.strip() if time_tag else ""
        time_ist = time_raw

        # -----------------------------
        # Teams
        # -----------------------------
        info_tag = row.select_one("div.stream-info")
        teams_text = info_tag.get_text(" ", strip=True) if info_tag else ""

        home = ""
        away = ""

        if re.search(r"\bvs\b", teams_text, flags=re.I):
            parts = re.split(r"\s+vs\s+", teams_text, flags=re.I)
            if len(parts) == 2:
                home = parts[0].strip()
                away = parts[1].strip()

        # -----------------------------
        # Logos (from crest DB)
        # -----------------------------
        home_logo = find_team_crest(home) if home else random_logo()
        away_logo = find_team_crest(away) if away else random_logo()

        # -----------------------------
        # Match page URL (from onclick)
        # -----------------------------
        btn = row.select_one("button.watch-btn[onclick]")
        match_page_url = ""

        if btn:
            onclick = btn.get("onclick", "")
            m = re.search(r"window\.location\.href='([^']+)'", onclick)
            if m:
                match_page_url = m.group(1).strip()

        # -----------------------------
        # 🔥 Open match page → extract iframe src
        # -----------------------------
        final_stream_url = ""

        if match_page_url:
            try:
                match_html = requests.get(match_page_url, headers=headers, timeout=10).text
                match_soup = BeautifulSoup(match_html, "html.parser")

                iframe = match_soup.select_one("iframe")
                if iframe and iframe.has_attr("src"):
                    final_stream_url = iframe["src"].strip()

            except Exception as e:
                print("⚠️ Ovogoal iframe fetch failed:", e)

        # -----------------------------
        # Append match
        # -----------------------------
        matches.append({
            "time": time_ist,
            "game": "football",
            "league": league,
            "home_team": home,
            "away_team": away,
            "label": short_label(home, away) if home and away else "ovogoal",
            "home_logo": home_logo or random_logo(),
            "away_logo": away_logo or random_logo(),
            "url": final_stream_url
        })

    return matches


# ---------- Save JSON ----------
JSON_FOLDER = "json"
os.makedirs(JSON_FOLDER, exist_ok=True)


if __name__ == "__main__":
    try:
        data = fetch_ovogoal()
        with open(os.path.join(JSON_FOLDER, "ovogoal.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"✅ Saved ovogoal.json with {len(data)} entries")

    except Exception as e:
        print(f"❌ Failed to fetch ovogoal.json: {e}")
        with open(os.path.join(JSON_FOLDER, "ovogoal.json"), "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
