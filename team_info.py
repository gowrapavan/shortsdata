import os
import time
import json
import requests

# ⚙️ CONFIG
# Best Practice: Set FOOTBALL_API_KEY in your GitHub Secrets
API_KEY = os.getenv("API_KEY", "18eaa48000cb4abc9db7dfea5e219828")
BASE_URL = "https://api.football-data.org/v4"
OUTPUT_DIR = "teams"

# Note: Remove leagues that return 403 Forbidden based on your plan
LEAGUES = {
    "PL": "EPL.json", 
    "PD": "ESP.json", 
    "BL1": "DEB.json",
    "SA": "ITSA.json", 
    "FL1": "FRL1.json"
    # "DED": "DED.json", "BSA": "BSA.json", "ELC": "ELC.json", 
    # "PPL": "POR.json", "CL": "UCL.json", "EC": "EC.json", 
    # "WC": "WC.json", "MLS": "MLS.json"
}

headers = {"X-Auth-Token": API_KEY}

def fetch_data(endpoint):
    """Fetch from API with retry logic for 429 errors."""
    url = f"{BASE_URL}/{endpoint}"
    for attempt in range(3):
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 429:
            print(f"⚠️ Rate limited on {endpoint}. Waiting 60s...")
            time.sleep(60)
        else:
            print(f"❌ Failed {endpoint}: {resp.status_code}")
            return None
    return None

def save_league_json(league_code, filename):
    print(f"🔍 Processing {league_code}...")

    team_data = fetch_data(f"competitions/{league_code}/teams")
    if not team_data or "teams" not in team_data:
        return

    teams = team_data["teams"]
    scorer_data = fetch_data(f"competitions/{league_code}/scorers")
    
    scorers_map = {}
    if scorer_data and "scorers" in scorer_data:
        for entry in scorer_data["scorers"]:
            t_id = entry["team"]["id"]
            if t_id not in scorers_map:
                scorers_map[t_id] = []
            scorers_map[t_id].append({
                "player_name": entry["player"]["name"],
                "goals": entry["goals"],
                "assists": entry["assists"]
            })

    for team in teams:
        team["top_scorers"] = scorers_map.get(team["id"], [])

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(teams, f, ensure_ascii=False, indent=2)

    print(f"✅ Saved {len(teams)} teams → {path}")

def main():
    print("⚽ Fetching teams and top scorers...\n")
    for code, filename in LEAGUES.items():
        save_league_json(code, filename)
        time.sleep(15)  # Respect the 10 req/min limit
    print("\n🎉 Done!")

if __name__ == "__main__":
    main()
