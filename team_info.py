import os
import time
import json
import requests

# ⚙️ CONFIG
API_KEY = "18eaa48000cb4abc9db7dfea5e219828"  # 🔑 replace with your real Football-Data.org key
BASE_URL = "https://api.football-data.org/v4"
OUTPUT_DIR = "teams"

# 🏆 Leagues mapping (API code → your desired filename)
LEAGUES = {
    "PL": "EPL.json",      # Premier League
    "PD": "ESP.json",      # Primera Division (La Liga)
    "BL1": "DEB.json",     # Bundesliga
    "DED": "DED.json",     # Eredivisie
    "SA": "ITSA.json",     # Serie A
    "FL1": "FRL1.json",    # Ligue 1
    "BSA": "BSA.json",     # Campeonato Brasileiro Série A
    "ELC": "ELC.json",     # Championship
    "PPL": "POR.json",     # Primeira Liga
    "CL": "UCL.json",      # UEFA Champions League
    "EC": "EC.json",       # European Championship
    "WC": "WC.json",       # FIFA World Cup
    "MLS": "MLS.json"      # Major League Soccer (optional)
}

headers = {"X-Auth-Token": API_KEY}


def fetch_league_teams(league_code):
    """Fetch team data for a given league"""
    url = f"{BASE_URL}/competitions/{league_code}/teams"
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print(f"❌ Failed to fetch {league_code}: {resp.status_code}")
        return []
    data = resp.json()
    return data.get("teams", [])


def save_league_json(league_code, filename):
    """Fetch and save one league’s teams to a JSON file"""
    teams = fetch_league_teams(league_code)
    if not teams:
        print(f"⚠️ No data for {league_code}")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(teams, f, ensure_ascii=False, indent=2)

    print(f"✅ Saved {len(teams)} teams → {path}")


def main():
    print("⚽ Fetching teams by league...\n")
    for code, filename in LEAGUES.items():
        save_league_json(code, filename)
        time.sleep(2)  # polite delay (10 requests/min limit)
    print("\n🎉 Done! All files saved in 'teams/' folder.")


if __name__ == "__main__":
    main()
