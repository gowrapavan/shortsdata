import requests
import json
import os
import unicodedata
import re
from datetime import datetime, timedelta
from difflib import SequenceMatcher

# ---------------- CONFIG ---------------- #
API_KEY = "4c67514f5388361ab34343e62c8e13df"
BASE_URL = "https://v3.football.api-sports.io/fixtures"
HEADERS = {"x-apisports-key": API_KEY}

LEAGUES = {
    "DEB": 78,
    "EPL": 39,
    "ESP": 140,
    "FRL1": 61,
    "ITSA": 135
}

# Use GitHub raw URLs for schedules
SCHEDULE_URLS = {
    "DEB": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/matches/DEB.json",
    "EPL": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/matches/EPL.json",
    "ESP": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/matches/ESP.json",
    "FRL1": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/matches/FRL1.json",
    "ITSA": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/matches/ITSA.json"
}

TIMEZONE = "Europe/London"
OUTPUT_DIR = "stats"
FUZZY_THRESHOLD = 0.6
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------------- HELPERS ---------------- #
def format_date(date):
    return date.strftime("%Y-%m-%d")

def fetch_json(url, params=None):
    """Fetch JSON from API or GitHub."""
    headers = HEADERS if "api-sports.io" in url else None
    res = requests.get(url, headers=headers, params=params)
    res.raise_for_status()
    return res.json()

def fetch_matches_by_date(date_str):
    url = f"{BASE_URL}?date={date_str}&timezone={TIMEZONE}"
    data = fetch_json(url)
    return data.get("response", [])

def fetch_fixture_data(fixture_id, data_type):
    url = f"{BASE_URL}/{data_type}?fixture={fixture_id}"
    data = fetch_json(url)
    return data.get("response", [])

def fetch_head_to_head(team1_id, team2_id):
    url = f"{BASE_URL}/headtohead?h2h={team1_id}-{team2_id}"
    data = fetch_json(url)
    return data.get("response", [])

def normalize_name(name: str) -> str:
    if not name:
        return ""
    name = name.lower()
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("utf-8")
    name = re.sub(r"\b(fc|cf|real|deportivo|club|atletico|athletic|ud|cd)\b", "", name)
    name = re.sub(r"[^a-z0-9]+", " ", name)
    return name.strip()

def string_similarity(a, b):
    return SequenceMatcher(None, normalize_name(a), normalize_name(b)).ratio()

def find_game_id(league_name, match_date, home_team, away_team):
    url = SCHEDULE_URLS.get(league_name)
    if not url:
        return None

    try:
        schedule_data = fetch_json(url)
    except requests.HTTPError:
        print(f"⚠️ Could not fetch schedule for {league_name} from GitHub")
        return None

    best_match = None
    best_score = 0.0

    for match in schedule_data:
        sched_date = match.get("Date", "")[:10]
        if sched_date != match_date:
            continue

        sched_home_names = [
            match.get("HomeTeamName", ""),
            match.get("HomeTeamKey", ""),
            match.get("HomeTeam", "")
        ]
        sched_away_names = [
            match.get("AwayTeamName", ""),
            match.get("AwayTeamKey", ""),
            match.get("AwayTeam", "")
        ]

        home_sim = max(string_similarity(home_team, n) for n in sched_home_names if n)
        away_sim = max(string_similarity(away_team, n) for n in sched_away_names if n)
        score = (home_sim + away_sim) / 2

        if score > best_score:
            best_score = score
            best_match = match

    if best_match and best_score >= FUZZY_THRESHOLD:
        return best_match.get("GameId")

    return None

# ---------------- MAIN ---------------- #
def main():
    # Only yesterday, today, tomorrow (API limitation)
    for delta_days in [1, 0, -1]:
        target_date = datetime.utcnow() - timedelta(days=delta_days)
        date_str = format_date(target_date)
        print(f"\nFetching matches for {date_str}...")

        all_fixtures = fetch_matches_by_date(date_str)

        for league_name, league_id in LEAGUES.items():
            fixtures = [f for f in all_fixtures if f["league"]["id"] == league_id]

            if not fixtures:
                print(f"No matches found for {league_name} on {date_str}.")
                continue

            output_file = os.path.join(OUTPUT_DIR, f"{league_name}.json")

            # Load existing data
            if os.path.exists(output_file):
                with open(output_file, "r", encoding="utf-8") as f:
                    existing_data_dict = {m["StatsId"]: m for m in json.load(f)}
            else:
                existing_data_dict = {}

            for f in fixtures:
                fixture_id = f["fixture"]["id"]
                match_date = f["fixture"]["date"][:10]
                home_team = f["teams"]["home"]["name"]
                away_team = f["teams"]["away"]["name"]
                home_id = f["teams"]["home"]["id"]
                away_id = f["teams"]["away"]["id"]
                status = f["fixture"]["status"]["short"]

                game_id = find_game_id(league_name, match_date, home_team, away_team)
                if not game_id:
                    print(f"⚠️ No GameId found for {home_team} vs {away_team} on {match_date}, skipping...")
                    continue

                # Skip finished fixtures already stored
                if fixture_id in existing_data_dict and status == "FT":
                    print(f"Skipping finished fixture {fixture_id} ({home_team} vs {away_team})")
                    continue

                match_obj = {
                    "StatsId": fixture_id,
                    "GameId": game_id,
                    "Date": f["fixture"]["date"],
                    "Status": status,
                    "Round": f["league"].get("round"),
                    "HomeTeam": home_team,
                    "AwayTeam": away_team,
                    "Score": {"Home": f["goals"]["home"], "Away": f["goals"]["away"]}
                }

                try:
                    match_obj["Events"] = fetch_fixture_data(fixture_id, "events")
                    match_obj["Lineups"] = fetch_fixture_data(fixture_id, "lineups")
                    match_obj["Statistics"] = fetch_fixture_data(fixture_id, "statistics")
                    match_obj["Players"] = fetch_fixture_data(fixture_id, "players")
                    match_obj["HeadToHead"] = fetch_head_to_head(home_id, away_id)
                except requests.HTTPError as e:
                    print(f"Error fetching details for fixture {fixture_id}: {e}")
                    continue

                # Add new or update existing
                existing_data_dict[fixture_id] = match_obj

            # Save combined data
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(list(existing_data_dict.values()), f, ensure_ascii=False, indent=2)

            print(f"Saved {len(existing_data_dict)} total matches to {output_file}")

if __name__ == "__main__":
    main()
