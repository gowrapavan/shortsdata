import os
import time
import json
import requests

# ⚙️ CONFIG 
API_KEY = "18eaa48000cb4abc9db7dfea5e219828" 
BASE_URL = "https://api.football-data.org/v4"
OUTPUT_DIR = "teams"

LEAGUES = {
    "PL": "EPL.json", "PD": "ESP.json", "BL1": "DEB.json",
    "DED": "DED.json", "SA": "ITSA.json", "FL1": "FRL1.json",
    "BSA": "BSA.json", "ELC": "ELC.json", "PPL": "POR.json",
    "CL": "UCL.json", "EC": "EC.json", "WC": "WC.json", "MLS": "MLS.json"
}

headers = {"X-Auth-Token": API_KEY}

def fetch_data(endpoint):
    """Helper to fetch from API with basic error handling"""
    url = f"{BASE_URL}/{endpoint}"
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        return resp.json()
    print(f"❌ Failed {endpoint}: {resp.status_code}")
    return None

def save_league_json(league_code, filename):
    """Fetch teams and top scorers, then merge them."""
    print(f"🔍 Processing {league_code}...")

    # 1. Fetch Teams
    team_data = fetch_data(f"competitions/{league_code}/teams")
    if not team_data or "teams" not in team_data:
        return
    teams = team_data["teams"]

    # 2. Fetch Top Scorers for the league
    scorer_data = fetch_data(f"competitions/{league_code}/scorers")
    
    # Create a map: team_id -> [list of top scorers]
    scorers_map = {}
    if scorer_data and "scorers" in scorer_data:
        for entry in scorer_data["scorers"]:
            t_id = entry["team"]["id"]
            if t_id not in scorers_map:
                scorers_map[t_id] = []
            
            # Add simplified scorer info
            scorers_map[t_id].append({
                "player_name": entry["player"]["name"],
                "goals": entry["goals"],
                "assists": entry["assists"]
            })

    # 3. Inject top_scorers attribute into team objects
    for team in teams:
        team_id = team["id"]
        # Default to empty list if no top scorers found for this team
        team["top_scorers"] = scorers_map.get(team_id, [])

    # 4. Save to file
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(teams, f, ensure_ascii=False, indent=2)

    print(f"✅ Saved {len(teams)} teams (with scorers) → {path}")

# In team_info.py
def main():
    print("⚽ Fetching teams and top scorers by league...\n")
    for code, filename in LEAGUES.items():
        save_league_json(code, filename)
        time.sleep(12)  # Increased to 12s to stay safer under the rate limit  # Increased delay to 6s to stay under 10 requests/min
    print("\n🎉 Done! All files saved in 'teams/' folder.")

if __name__ == "__main__":
    main()
