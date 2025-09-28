import requests
import re
import json
import os
from html import unescape
from datetime import datetime, timezone, timedelta
from time import sleep

# ---------------- CONFIG ---------------- #
LEAGUE_FILES = {
    "EPL": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/matches/EPL.json",
    "ESP": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/matches/ESP.json",
    "FRL1": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/matches/FRL1.json",
    "ITSA": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/matches/ITSA.json",
    "DEB": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/matches/DEB.json",

}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
}

OUTPUT_DIR = "images"
os.makedirs(OUTPUT_DIR, exist_ok=True)
HOME_LIMIT = 20
AWAY_LIMIT = 20
FETCH_LIMIT = 60  # fetch more to ensure uniqueness

# ---------------- HELPER FUNCTION ---------------- #
def fetch_images_for_query(query, limit=FETCH_LIMIT):
    """Fetch Getty image URLs for a search query."""
    query_encoded = query.replace(" ", "%20")
    url = f"https://www.gettyimages.in/search/2/image?family=editorial&phrase={query_encoded}&sort=newest&phraseprocessing=excludenaturallanguage"

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        html = response.text
    except Exception as e:
        print(f"❌ Failed to fetch images for '{query}': {e}")
        return []

    # Extract <img> and <source> URLs from HTML
    pattern = r'<(?:source|img)[^>]+(?:srcSet|src)="([^"]+)"'
    matches = re.findall(pattern, html)
    image_urls = [unescape(u) for u in matches if "gettyimages" in u]

    # Deduplicate and limit
    return list(dict.fromkeys(image_urls))[:limit]

# ---------------- PROCESS EACH LEAGUE ---------------- #
IST = timezone(timedelta(hours=5, minutes=30))
now_ist = datetime.now(IST)

today_str = now_ist.strftime("%Y-%m-%d")
yesterday_str = (now_ist - timedelta(days=1)).strftime("%Y-%m-%d")
TARGET_DATES = {yesterday_str, today_str}

for league, json_url in LEAGUE_FILES.items():
    print(f"\n🔵 Processing {league}...")
    try:
        resp = requests.get(json_url, timeout=10)
        games = resp.json()
    except Exception as e:
        print(f"❌ Failed to fetch {league} JSON: {e}")
        continue

    output_file = os.path.join(OUTPUT_DIR, f"{league}.json")
    if os.path.exists(output_file):
        with open(output_file, "r") as f:
            existing = {str(g["GameId"]): g for g in json.load(f)}
    else:
        existing = {}

    target_games = [g for g in games if g.get("Date") in TARGET_DATES]

    if not target_games:
        print(f"⚠️ No matches for yesterday or today in {league}")
        continue

    for game in target_games:
        game_id = str(game.get("GameId"))
        game_dt_str = game.get("DateTime")
        if not game_dt_str:
            continue

        try:
            dt_utc = datetime.fromisoformat(game_dt_str.replace("Z", "+00:00"))
            dt_ist = dt_utc.astimezone(IST)
        except Exception as e:
            print(f"⚠️ Failed to parse DateTime for Game {game_id}: {e}")
            continue

        if now_ist <= dt_ist:
            print(f"⏳ Skipping {game.get('HomeTeamName')} vs {game.get('AwayTeamName')} (not started yet)")
            continue

        home_team = game.get("HomeTeamName")
        away_team = game.get("AwayTeamName")
        if not home_team or not away_team:
            continue

        print(f"📸 Fetching images for: {home_team} vs {away_team}")

        # Fetch images
        home_images_all = fetch_images_for_query(home_team)
        home_images = home_images_all[:HOME_LIMIT]

        away_images_all = fetch_images_for_query(away_team)
        # Remove duplicates with home images
        away_images_unique = [img for img in away_images_all if img not in home_images]
        away_images = away_images_unique[:AWAY_LIMIT]

        # If not enough images, warn
        if len(away_images) < AWAY_LIMIT:
            print(f"⚠️ Only {len(away_images)} unique away images found for {away_team}")

        # Add to existing
        existing[game_id] = {
            "GameId": int(game_id),
            "HomeTeam": home_team,
            "AwayTeam": away_team,
            "HomeTeamImages": home_images,
            "AwayTeamImages": away_images,
            "MatchDateTime": game_dt_str,
            "MatchDateTime_IST": dt_ist.isoformat()
        }
        sleep(1)

    with open(output_file, "w") as f:
        json.dump(list(existing.values()), f, indent=2)

    print(f"✅ {league} images updated → {output_file}")
