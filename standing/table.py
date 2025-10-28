import os
import time
import json
import requests

# ⚙️ CONFIG
API_KEY = "18eaa48000cb4abc9db7dfea5e219828"  # Read key from GitHub Secrets
BASE_URL = "https://api.football-data.org/v4"
OUTPUT_DIR = "standing"

# 🏆 Leagues mapping (API code → your desired filename)
LEAGUES = {
    "PL": "EPL.json",      # Premier League
    "PD": "ESP.json",      # La Liga
    "BL1": "DEB.json",     # Bundesliga
    "DED": "DED.json",     # Eredivisie
    "SA": "ITSA.json",     # Serie A
    "FL1": "FRL1.json",    # Ligue 1
    "BSA": "BSA.json",     # Brasileiro Série A
    "ELC": "ELC.json",     # Championship
    "PPL": "POR.json",     # Primeira Liga
    "CL": "UCL.json",      # Champions League
    "EC": "EC.json",       # Euro Cup
    "WC": "WC.json",       # World Cup
    "MLS": "MLS.json"      # Major League Soccer
}

headers = {"X-Auth-Token": API_KEY}


def fetch_standing(league_code):
    """Fetch current standings for a competition"""
    url = f"{BASE_URL}/competitions/{league_code}/standings"
    resp = requests.get(url, headers=headers)

    if resp.status_code != 200:
        print(f"❌ Failed to fetch {league_code}: {resp.status_code}")
        return None

    data = resp.json()
    return data


def save_standing_json(league_code, filename):
    """Fetch and save league standings"""
    standings = fetch_standing(league_code)
    if not standings:
        print(f"⚠️ No standings found for {league_code}")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(standings, f, ensure_ascii=False, indent=2)

    print(f"✅ Saved standings for {league_code} → {path}")


def main():
    print("📊 Fetching football standings...\n")
    for code, filename in LEAGUES.items():
        save_standing_json(code, filename)
        time.sleep(2)  # Respect API rate limits
    print("\n🎯 Done! All standings saved in 'standing/' folder.")


if __name__ == "__main__":
    main()
