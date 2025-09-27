import requests
import json
import os
import time
from datetime import datetime, timedelta

# ------------------ CONFIG ------------------ #
API_TOKEN = os.getenv("API_KEY")  # Use GitHub Actions secret
HEADERS = {"X-Auth-Token": API_TOKEN}
BASE_URL = "https://api.football-data.org/v4/competitions"

COMPETITIONS = {
    "DEB": "BL1",
    "ELC": "ELC",
    "EPL": "PL",
    "ESP": "PD",
    "FRL1": "FL1",
    "ITSA": "SA",
    "MLS": "MLS",
    "UCL": "CL",
    "UEL": "ELC",
    "WC": "WC",
    "DED": "DED",
    "BSA": "BSA",
    "EC": "EC"
}

SAVE_DIR = "./matches"
os.makedirs(SAVE_DIR, exist_ok=True)

# ------------------ UTILITIES ------------------ #
def load_existing(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"⚠️ Malformed JSON in {file_path}, starting fresh")
    return []

def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def fetch_all_matches(league_code, season):
    url = f"{BASE_URL}/{league_code}/matches?season={season}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        if res.status_code == 200:
            return res.json().get("matches", [])
        else:
            print(f"❌ HTTP {res.status_code} for {league_code}")
    except requests.RequestException as e:
        print(f"❌ Request error for {league_code}: {e}")
    return []

def process_match(match):
    home = match.get("homeTeam") or {"id": 0, "name": "TBD", "shortName": "TBD", "crest": None}
    away = match.get("awayTeam") or {"id": 0, "name": "TBD", "shortName": "TBD", "crest": None}
    score = match.get("score", {}).get("fullTime", {})
    status = match.get("status", "SCHEDULED")

    home_score = score.get("home")
    away_score = score.get("away")
    result = None
    points = {str(home["id"]): 0, str(away["id"]): 0}

    if status == "FINISHED":
        if home_score > away_score:
            result = home["id"]
            points[str(home["id"])] = 3
        elif away_score > home_score:
            result = away["id"]
            points[str(away["id"])] = 3
        else:
            points[str(home["id"])] = 1
            points[str(away["id"])] = 1

    return {
        "GameId": match.get("id", 0),
        "RoundId": match.get("season", {}).get("currentMatchday", 0),
        "RoundName": match.get("competition", {}).get("name", "Regular Season"),
        "Date": match.get("utcDate", "").split("T")[0],
        "DateTime": match.get("utcDate"),
        "Status": "Final" if status == "FINISHED" else "Scheduled",
        "Week": None,
        "VenueType": "Home Away",
        "HomeTeamId": home.get("id", 0),
        "AwayTeamId": away.get("id", 0),
        "HomeTeamKey": home.get("shortName") or (home.get("name")[:3] if home.get("name") else "TBD"),
        "AwayTeamKey": away.get("shortName") or (away.get("name")[:3] if away.get("name") else "TBD"),
        "HomeTeamName": home.get("name", "TBD"),
        "AwayTeamName": away.get("name", "TBD"),
        "HomeTeamLogo": home.get("crest"),
        "AwayTeamLogo": away.get("crest"),
        "HomeTeamScore": home_score,
        "AwayTeamScore": away_score,
        "Result": result,
        "Points": points,
        "Goals": []
    }

# ------------------ MAIN ------------------ #
def main():
    today = datetime.utcnow().date()
    past_limit = today - timedelta(days=7)
    future_limit = today + timedelta(days=14)

    for comp_name, league_code in COMPETITIONS.items():
        season = 2026 if league_code == "WC" else 2025
        print(f"\n📦 Fetching matches for {comp_name} ({league_code}) season {season}...")

        file_path = os.path.join(SAVE_DIR, f"{comp_name}.json")
        existing_data = load_existing(file_path)
        match_map = {m["GameId"]: m for m in existing_data}

        matches = fetch_all_matches(league_code, season)
        updated_count = 0

        for m in matches:
            match_id = m.get("id")
            status = m.get("status")
            match_date = None

            if m.get("utcDate"):
                try:
                    match_date = datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00")).date()
                except ValueError:
                    pass

            # ✅ Skip matches outside update window
            if match_date:
                if status == "FINISHED" and match_date < past_limit:
                    continue
                if status != "FINISHED" and match_date > future_limit:
                    continue

            # ✅ Skip finished matches already stored
            if status == "FINISHED" and match_id in match_map:
                existing = match_map[match_id]
                if existing["Status"] == "Final" and existing["HomeTeamScore"] is not None:
                    continue

            processed = process_match(m)
            match_map[processed["GameId"]] = processed
            updated_count += 1
            print(f"🔄 {processed['HomeTeamName']} vs {processed['AwayTeamName']} ({processed['Status']})")
            time.sleep(0.1)

        final_list = sorted(list(match_map.values()), key=lambda x: x["GameId"])
        save_json(file_path, final_list)
        print(f"✅ Updated {updated_count} matches for {comp_name} → {file_path}")

if __name__ == "__main__":
    main()
