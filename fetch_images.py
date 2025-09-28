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
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
}

PROXY_URL = "https://tv-stream-proxy.onrender.com/proxy?url="

OUTPUT_DIR = "images"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------------- HELPER FUNCTION ---------------- #
def fetch_images_for_query(query, limit=15):
    """Fetch Getty image URLs for a search query via proxy."""
    target_url = (
        f"https://www.gettyimages.in/search/2/image?family=editorial"
        f"&phrase={query.replace(' ', '%20')}&sort=newest&phraseprocessing=excludenaturallanguage"
    )
    proxy_request_url = PROXY_URL + target_url

    try:
        response = requests.get(proxy_request_url, headers=HEADERS, timeout=15)
        html = response.text
    except Exception as e:
        print(f"❌ Failed to fetch images for {query} via proxy: {e}")
        return []

    image_urls = []

    # -------- Try extracting from inline JSON -------- #
    try:
        json_match = re.search(r'{"search":.*?,"gallery":{.*}}', html)
        if json_match:
            data = json.loads(unescape(json_match.group(0)))
            gallery = data.get("gallery", {})
            items = gallery.get("items", [])
            for item in items:
                sizes = item.get("display_sizes", [])
                for s in sizes:
                    link = s.get("uri")
                    if link and link.startswith("http"):
                        image_urls.append(link)
            image_urls = list(dict.fromkeys(image_urls))  # dedupe
    except Exception as e:
        print(f"⚠️ JSON parse fallback for {query}: {e}")

    # -------- Fallback: regex on <img>/<source> tags -------- #
    if not image_urls:
        pattern = r'<(?:source|img)[^>]+(?:srcSet|src)="([^"]+)"'
        matches = re.findall(pattern, html)
        image_urls = [unescape(u) for u in matches if "gettyimages" in u]

    return image_urls[:limit]

# ---------------- PROCESS EACH LEAGUE ---------------- #
IST = timezone(timedelta(hours=5, minutes=30))  # UTC+5:30
now_ist = datetime.now(IST)
today_str = now_ist.strftime("%Y-%m-%d")
yesterday_str = (now_ist - timedelta(days=1)).strftime("%Y-%m-%d")

for league, json_url in LEAGUE_FILES.items():
    print(f"\n🔵 Processing {league}...")
    try:
        resp = requests.get(json_url, timeout=10)
        games = resp.json()
    except Exception as e:
        print(f"❌ Failed to fetch {league} JSON: {e}")
        continue

    # Load existing file if available
    output_file = os.path.join(OUTPUT_DIR, f"{league}.json")
    if os.path.exists(output_file):
        with open(output_file, "r") as f:
            existing = {str(g["GameId"]): g for g in json.load(f)}
    else:
        existing = {}

    # Filter only yesterday's and today's matches
    target_games = [g for g in games if g.get("Date") in (today_str, yesterday_str)]

    if not target_games:
        print(f"⚠️ No matches for today or yesterday in {league}")
        continue

    for game in target_games:
        game_id = str(game.get("GameId"))
        game_dt_str = game.get("DateTime")
        if not game_dt_str:
            continue

        # Convert DateTime (UTC from JSON) to IST
        try:
            dt_utc = datetime.fromisoformat(game_dt_str.replace("Z", "+00:00"))
            dt_ist = dt_utc.astimezone(IST)
        except Exception as e:
            print(f"⚠️ Failed to parse DateTime for Game {game_id}: {e}")
            continue

        # Only proceed if scheduled time has already passed in IST
        if now_ist <= dt_ist:
            print(f"⏳ Skipping {game['HomeTeamName']} vs {game['AwayTeamName']} (not started yet)")
            continue

        home_team = game.get("HomeTeamName")
        away_team = game.get("AwayTeamName")
        if not home_team or not away_team:
            continue

        print(f"📸 Fetching images for: {home_team} vs {away_team}")

        home_images = fetch_images_for_query(home_team, limit=15)
        sleep(1)
        away_images = fetch_images_for_query(away_team, limit=15)
        sleep(1)

        # Replace existing images if re-run or add new match
        existing[game_id] = {
            "GameId": int(game_id),
            "HomeTeam": home_team,
            "AwayTeam": away_team,
            "HomeTeamImages": home_images,
            "AwayTeamImages": away_images
        }

    # Save merged results
    with open(output_file, "w") as f:
        json.dump(list(existing.values()), f, indent=2)

    print(f"✅ {league} images updated → {output_file}")
