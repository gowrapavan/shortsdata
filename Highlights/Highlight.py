import requests
import json
import re
import unicodedata
from difflib import SequenceMatcher
import os

# ---------------- CONFIG ---------------- #

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Ensure correct folder
HIGHLIGHT_URL = "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/Highlights/hoofoot.json"
OUTPUT_FILE = os.path.join(BASE_DIR, "Highlight.json")  # Absolute path

MATCH_URLS = {
    "EPL": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/matches/EPL.json",
    "ESP": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/matches/ESP.json",
    "FRL1": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/matches/FRL1.json",
    "ITSA": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/matches/ITSA.json",
    "DEB": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/matches/DEB.json",
}

TEAM_URLS = {
    "EPL": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/EPL.json",
    "ESP": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/ESP.json",
    "FRL1": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/FRL1.json",
    "ITSA": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/ITSA.json",
    "DEB": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/DEB.json",
    "UCL": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/UCL.json",
    "WC": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/WC.json",
}

DEFAULT_LEAGUE = "Goal4u - Undefined"
DEFAULT_LOGO = "https://raw.githubusercontent.com/gowrapavan/Goal4u/main/public/assets/img/tv-logo/aves.png"
FUZZY_THRESHOLD = 0.6

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
    text = re.sub(r"\b(fc|cf|ac|ssc|sv|tsg|club)\b", "", text)
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

# ---------------- EXISTING OUTPUT ---------------- #

existing_items = []
existing_ids = set()

if os.path.exists(OUTPUT_FILE):
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            existing_items = json.load(f)
            existing_ids = {item.get("id") for item in existing_items if item.get("id")}
    except Exception:
        existing_items = []
        existing_ids = set()

# ---------------- MATCH / LOGO FINDERS ---------------- #

def find_match(date, home, away):
    best_match = None
    best_league = None
    best_score = 0

    for league, matches in matches_by_league.items():
        for m in matches:
            if m.get("Date") != date:
                continue

            score = (
                similarity(home, m.get("HomeTeamName")) +
                similarity(home, m.get("HomeTeamKey")) +
                similarity(away, m.get("AwayTeamName")) +
                similarity(away, m.get("AwayTeamKey"))
            ) / 4

            if score > best_score:
                best_match = m
                best_league = league
                best_score = score

    if best_score >= FUZZY_THRESHOLD:
        return best_league, best_match

    return None, None

def find_logo(team_name):
    for teams in teams_by_league.values():
        for team in teams:
            if similarity(team_name, team.get("name")) >= FUZZY_THRESHOLD or \
               similarity(team_name, team.get("shortName")) >= FUZZY_THRESHOLD:
                return team.get("crest") or DEFAULT_LOGO
    return DEFAULT_LOGO

# ---------------- BUILD OUTPUT ---------------- #

new_items = []

for h in highlights:
    highlight_id = h.get("id")
    if not highlight_id or highlight_id in existing_ids:
        continue  # ✅ SKIP EXISTING

    home, away = split_title(h.get("title", ""))
    date = h.get("match_date", "").replace("_", "-")

    league, match = find_match(date, home, away)

    # ❌ Skip if no official match found (optional but recommended)
    if not match:
        continue

    item = {
        # 🔑 IDs (CLEAR SEPARATION)
        "highlight_id": highlight_id,           # from hoofoot
        "game_id": match.get("GameId"),          # from match json

        # 🏆 Competition
        "league": league or DEFAULT_LEAGUE,
        "round": match.get("RoundName"),
        "season": match.get("Season", None),

        # 📅 Match timing
        "date": match.get("Date"),
        "datetime": match.get("DateTime"),
        "status": match.get("Status"),

        # 🏟 Teams
        "home_team": {
            "id": match.get("HomeTeamId"),
            "key": match.get("HomeTeamKey"),
            "name": match.get("HomeTeamName"),
            "logo": match.get("HomeTeamLogo") or find_logo(home),
            "score": match.get("HomeTeamScore"),
        },
        "away_team": {
            "id": match.get("AwayTeamId"),
            "key": match.get("AwayTeamKey"),
            "name": match.get("AwayTeamName"),
            "logo": match.get("AwayTeamLogo") or find_logo(away),
            "score": match.get("AwayTeamScore"),
        },

        # ⚽ Match data
        "result": match.get("Result"),
        "points": match.get("Points"),
        "goals": match.get("Goals", []),

        # 🎬 Highlight data (hoofoot)
        "title": h.get("title"),
        "highlight_url": h.get("match_url"),
        "embed_url": h.get("embed_url"),
        "source": "hoofoot",
    }

    new_items.append(item)

# ---------------- SAVE ---------------- #

final_output = existing_items + new_items

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(final_output, f, ensure_ascii=False, indent=2)

print(f"✅ Added {len(new_items)} new highlights (skipped {len(existing_ids)})")
