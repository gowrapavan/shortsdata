import os
import time
import json
import requests
from datetime import datetime

# ⚙️ CONFIG
API_KEY = os.getenv("API_KEY", "7e19076a67c6447e987830a06717c4ac")
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
    url = f"{BASE_URL}/{endpoint}"
    for attempt in range(5):
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 429:
            time.sleep(60)
        elif resp.status_code == 403:
            return None
        else:
            return None
    return None

def save_league_json(league_code, filename):
    print(f"🔍 Processing {league_code}...")
    team_data = fetch_data(f"competitions/{league_code}/teams")
    if not team_data or "teams" not in team_data: return

    teams = team_data["teams"]
    scorer_data = fetch_data(f"competitions/{league_code}/scorers")
    
    scorers_map = {}
    if scorer_data and "scorers" in scorer_data:
        for entry in scorer_data["scorers"]:
            t_id = entry["team"]["id"]
            if t_id not in scorers_map: scorers_map[t_id] = []
            scorers_map[t_id].append({"player_name": entry["player"]["name"], "goals": entry["goals"], "assists": entry["assists"]})

    # Add timestamp and data
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    for team in teams:
        team["last_updated"] = current_time # This forces a change every time
        team["top_scorers"] = scorers_map.get(team["id"], [])

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
        json.dump(teams, f, ensure_ascii=False, indent=2)

def main():
    for code, filename in LEAGUES.items():
        save_league_json(code, filename)
        time.sleep(10) 

if __name__ == "__main__":
    main()
