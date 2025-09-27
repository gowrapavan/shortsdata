import requests
import re
import json
import os
from html import unescape
from datetime import datetime
from time import sleep

# ---------------- CONFIG ---------------- #
LEAGUE_FILES = {
    "EPL": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/matches/EPL.json",
    "ESP": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/matches/ESP.json",
    # Add more leagues if needed
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
}

OUTPUT_DIR = "images"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------------- HELPER FUNCTION ---------------- #
def fetch_images_for_query(query, limit=15):
    """Fetch Getty image URLs for a search query, limited to N results."""
    url = f"https://www.gettyimages.in/search/2/image?family=editorial&phrase={query.replace(' ', '%20')}&sort=newest&phraseprocessing=excludenaturallanguage"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        html = response.text
    except Exception as e:
        print(f"Failed to fetch images for {query}: {e}")
        return []

    # Extract src or srcSet from <source> or <img> tags
    pattern = r'<(?:source|img)[^>]+(?:srcSet|src)="([^"]+)"'
    matches = re.findall(pattern, html)
    image_urls = [unescape(url) for url in matches]

    # Filter only Getty image URLs
    filtered_urls = [
        url for url in image_urls
        if url.startswith("http") and "/id/" in url and "/photo/" in url
    ]

    # Remove duplicates
    unique_urls = list(dict.fromkeys(filtered_urls))

    # Limit results
    return unique_urls[:limit]

# ---------------- PROCESS EACH LEAGUE ---------------- #
today_str = datetime.utcnow().strftime("%Y-%m-%d")  # use UTC for consistency

for league, json_url in LEAGUE_FILES.items():
    print(f"\nProcessing {league}...")
    try:
        resp = requests.get(json_url, timeout=10)
        games = resp.json()
    except Exception as e:
        print(f"Failed to fetch {league} JSON: {e}")
        continue

    league_images = []

    # Filter only today's matches
    todays_games = [g for g in games if g.get("Date") == today_str]

    if not todays_games:
        print(f"No matches today for {league}")
        continue

    for game in todays_games:
        game_id = game.get("GameId")
        home_team = game.get("HomeTeamName")
        away_team = game.get("AwayTeamName")
        if not home_team or not away_team:
            continue

        print(f"Fetching images for: {home_team} and {away_team}")

        # Fetch images separately for both teams
        home_images = fetch_images_for_query(home_team, limit=15)
        sleep(1)  # avoid rate limiting
        away_images = fetch_images_for_query(away_team, limit=15)
        sleep(1)

        league_images.append({
            "GameId": game_id,
            "HomeTeam": home_team,
            "AwayTeam": away_team,
            "HomeTeamImages": home_images,
            "AwayTeamImages": away_images
        })

    # Save league JSON
    output_file = os.path.join(OUTPUT_DIR, f"{league}.json")
    with open(output_file, "w") as f:
        json.dump(league_images, f, indent=2)

    print(f"{league} images saved to {output_file}")
