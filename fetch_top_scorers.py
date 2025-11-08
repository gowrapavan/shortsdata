#!/usr/bin/env python3
import requests
import json
import time
from datetime import datetime

# ======================
# ⚙️ CONFIGURATION
# ======================
API_KEY = "18eaa48000cb4abc9db7dfea5e219828"   # <-- replace with your Football-Data.org API key
BASE_URL = "https://api.football-data.org/v4/competitions"

# Competitions to fetch
COMPETITIONS = {
    "PL": "Premier League",
    "PD": "La Liga",
    "SA": "Serie A",
    "BL1": "Bundesliga",
    "FL1": "Ligue 1",
    "DED": "Eredivisie",
    "CL": "Champions League"
}

HEADERS = {"X-Auth-Token": API_KEY}

OUTPUT_FILE = "top_scorers.json"


# ======================
# 🏃 FETCH FUNCTION
# ======================
def fetch_top_scorers(competition_code):
    """Fetch top scorers for a given competition."""
    url = f"{BASE_URL}/{competition_code}/scorers"
    try:
        res = requests.get(url, headers=HEADERS)
        res.raise_for_status()
        data = res.json()

        scorers_list = []
        for s in data.get("scorers", []):
            player = s.get("player", {})
            team = s.get("team", {})
            scorers_list.append({
                "player_name": player.get("name"),
                "team_name": team.get("name"),
                "team_crest": team.get("crest"),
                "goals": s.get("goals", 0),
                "assists": s.get("assists"),
                "penalties": s.get("penalties"),
                "nationality": player.get("nationality")
            })

        return {
            "competition": data.get("competition", {}).get("name", competition_code),
            "code": competition_code,
            "count": data.get("count", len(scorers_list)),
            "scorers": scorers_list
        }

    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching {competition_code}: {e}")
        return {
            "competition": competition_code,
            "error": str(e),
            "scorers": []
        }


# ======================
# 💾 MAIN EXECUTION
# ======================
def main():
    all_data = {
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "leagues": {}
    }

    for code, name in COMPETITIONS.items():
        print(f"⚽ Fetching {name} ({code})...")
        league_data = fetch_top_scorers(code)
        all_data["leagues"][code] = league_data
        time.sleep(6)  # API rate limit safety (10 requests/minute)

    # Save to JSON
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=4, ensure_ascii=False)

    print(f"\n✅ Top scorers saved to {OUTPUT_FILE}")
    print("Leagues fetched:", ", ".join(COMPETITIONS.keys()))


if __name__ == "__main__":
    main()
