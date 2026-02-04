import requests
import json
import re
import unicodedata
from difflib import SequenceMatcher
import os

# ---------------- CONFIG ---------------- #

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HIGHLIGHT_URL = "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/Highlights/hoofoot.json"
OUTPUT_FILE = os.path.join(BASE_DIR, "Highlight.json")

MATCH_URLS = {
    "EPL": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/matches/EPL.json",
    "ESP": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/matches/ESP.json",
    "FRL1": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/matches/FRL1.json",
    "ITSA": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/matches/ITSA.json",
    "DEB": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/matches/DEB.json",
    "UCL": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/matches/UCL.json",
    "WC": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/matches/WC.json",
    "MLS": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/matches/MLS.json",
    "DED": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/matches/DED.json",
}

TEAM_URLS = {
    "EPL": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/EPL.json",
    "ESP": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/ESP.json",
    "FRL1": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/FRL1.json",
    "ITSA": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/ITSA.json",
    "DEB": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/DEB.json",
    "UCL": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/UCL.json",
    "WC": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/WC.json",
    "MLS": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/MLS.json",
    "DED": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/DED.json",
}

DEFAULT_LEAGUE = "Goal4u - Undefined"
DEFAULT_LOGO = "https://raw.githubusercontent.com/gowrapavan/Goal4u/main/public/assets/img/tv-logo/aves.png"

MATCH_THRESHOLD = 0.6
LOGO_THRESHOLD = 0.85  # 🔥 higher threshold for logos (prevents wrong logos)

# ---------------- HELPERS ---------------- #

def fetch_json(url):
    try:
        return requests.get(url, timeout=20).json()
    except Exception:
        return []

def normalize(text):
    if not text:
        return ""
    text = text.lower()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"\b(fc|cf|ac|ssc|sv|tsg|club|football|club de)\b", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return text.strip()

def similarity(a, b):
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()

def split_title(title):
    parts = re.split(r"\s+v\s+|\s+vs\s+", title, flags=re.I)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return None, None

# ---------------- LOAD DATA ---------------- #

highlights = fetch_json(HIGHLIGHT_URL)
matches_by_league = {k: fetch_json(v) for k, v in MATCH_URLS.items()}
teams_by_league = {k: fetch_json(v) for k, v in TEAM_URLS.items()}

# ---------------- GLOBAL TEAM INDEX ---------------- #

TEAM_INDEX = {}

def add_team_to_index(team):
    names = [
        team.get("name"),
        team.get("shortName"),
    ]
    logo = team.get("crest") or DEFAULT_LOGO

    for n in names:
        if n:
            TEAM_INDEX[normalize(n)] = logo

for teams in teams_by_league.values():
    for team in teams:
        add_team_to_index(team)

# ---------------- TEAM ALIASES (IMPORTANT) ---------------- #

TEAM_ALIASES = {
    "marseille": "olympique marseille",
    "rennes": "stade rennes",
    "inter": "inter milan",
    "man utd": "manchester united",
    "man city": "manchester city",
    "psg": "paris saint germain",
    "ac milan": "milan",
    "bayern": "bayern munich",
    "barca": "barcelona",
}

def resolve_alias(name):
    n = normalize(name)
    return TEAM_ALIASES.get(n, n)

# ---------------- EXISTING OUTPUT ---------------- #

existing_items = []
existing_keys = set()

if os.path.exists(OUTPUT_FILE):
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            existing_items = json.load(f)
            for item in existing_items:
                hid = item.get("highlight_id")
                date = item.get("date")
                if hid and date:
                    existing_keys.add((hid, date))
    except Exception:
        pass

# ---------------- MATCH FINDER ---------------- #

def find_match(date, home, away):
    best_match = None
    best_league = None
    best_score = 0

    for league, matches in matches_by_league.items():
        for m in matches:
            if m.get("Date") != date:
                continue

            score_home = similarity(home, m.get("HomeTeamName")) + similarity(home, m.get("HomeTeamKey"))
            score_away = similarity(away, m.get("AwayTeamName")) + similarity(away, m.get("AwayTeamKey"))
            score = (score_home + score_away) / 4

            if score > best_score:
                best_match = m
                best_league = league
                best_score = score

    if best_score >= MATCH_THRESHOLD:
        return best_league, best_match

    return None, None

# ---------------- SMART LOGO FINDER ---------------- #

def find_logo(team_name):
    if not team_name:
        return DEFAULT_LOGO

    name = resolve_alias(team_name)
    norm = normalize(name)

    # 1️⃣ Exact match
    if norm in TEAM_INDEX:
        return TEAM_INDEX[norm]

    # 2️⃣ Strong fuzzy match
    best_logo = None
    best_score = 0

    for team_norm, logo in TEAM_INDEX.items():
        s = similarity(norm, team_norm)
        if s > best_score:
            best_score = s
            best_logo = logo

    if best_score >= LOGO_THRESHOLD:
        return best_logo

    # 3️⃣ Final fallback
    return DEFAULT_LOGO

# ---------------- BUILD OUTPUT ---------------- #

new_items = []
seen_in_run = set()

for h in highlights:
    highlight_id = h.get("id")
    if not highlight_id:
        continue

    home, away = split_title(h.get("title", ""))
    date = h.get("match_date", "").replace("_", "-")

    unique_key = (highlight_id, date)

    if unique_key in existing_keys or unique_key in seen_in_run:
        continue

    league, match = find_match(date, home, away)

    if not match:
        match = {
            "GameId": None,
            "RoundName": None,
            "Season": None,
            "Date": date,
            "DateTime": None,
            "Status": "Finished",
            "HomeTeamName": home,
            "AwayTeamName": away,
        }
        league = DEFAULT_LEAGUE

    item = {
        "highlight_id": highlight_id,
        "game_id": match.get("GameId"),
        "league": league or DEFAULT_LEAGUE,
        "round": match.get("RoundName"),
        "season": match.get("Season"),
        "date": match.get("Date") or date,
        "datetime": match.get("DateTime") or f"{date}T00:00:00",
        "status": match.get("Status") or "Finished",

        "home_team": {
            "name": match.get("HomeTeamName") or home,
            "logo": match.get("HomeTeamLogo") or find_logo(home),
            "score": match.get("HomeTeamScore"),
        },
        "away_team": {
            "name": match.get("AwayTeamName") or away,
            "logo": match.get("AwayTeamLogo") or find_logo(away),
            "score": match.get("AwayTeamScore"),
        },

        "title": h.get("title"),
        "highlight_url": h.get("match_url"),
        "embed_url": h.get("embed_url"),

        "match_type": "official" if match.get("GameId") else "fallback",
        "source": "hoofoot",
    }

    new_items.append(item)
    seen_in_run.add(unique_key)

# ---------------- SAVE ---------------- #

final_output = existing_items + new_items

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(final_output, f, ensure_ascii=False, indent=2)

print(f"✅ Added {len(new_items)} new highlights | Skipped duplicates: {len(seen_in_run)}")
