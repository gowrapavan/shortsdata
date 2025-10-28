#!/usr/bin/env python3
import requests
import json
import os
import unicodedata
import re
import time
from datetime import datetime, timedelta
from difflib import SequenceMatcher  # fuzzy string matching
import pytz  # ✅ added for timezone handling

# ---------------- CONFIG ---------------- #
API_KEYS = [
    "dec966a0a00434be718c28d5e39d590f",
    "91fa929380bfaf2825905aa038794cfc"
]
current_key_index = 0

BASE_URL = "https://v3.football.api-sports.io/fixtures"
TIMEZONE = "Europe/London"
OUTPUT_DIR = "stats"
SCHEDULE_DIR = "2026"  # local fallback directory
FUZZY_THRESHOLD = 0.6
PAUSE_SEC = 6
os.makedirs(OUTPUT_DIR, exist_ok=True)

LEAGUES = {
    "DEB": 78,
    "EPL": 39,
    "ESP": 140,
    "FRL1": 61,
    "ITSA": 135
}

SCHEDULE_URLS = {
    "DEB": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/matches/DEB.json",
    "EPL": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/matches/EPL.json",
    "ESP": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/matches/ESP.json",
    "FRL1": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/matches/FRL1.json",
    "ITSA": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/matches/ITSA.json"
}

# ---------------- HELPERS ---------------- #
def get_headers():
    return {"x-apisports-key": API_KEYS[current_key_index]}

def switch_key():
    global current_key_index
    current_key_index = (current_key_index + 1) % len(API_KEYS)
    print(f"🔄 Switched to API key {current_key_index + 1}")

def format_date(date):
    return date.strftime("%Y-%m-%d")

def _is_plan_block_error(data):
    if not isinstance(data, dict):
        return False
    errs = data.get("errors")
    if errs:
        return "Free plans do not have access" in json.dumps(errs)
    return False

def fetch_json(url, params=None):
    """Centralized fetch with retries and key rotation"""
    for _ in range(len(API_KEYS) * 2):
        try:
            res = requests.get(url, headers=get_headers(), params=params, timeout=15)
            try:
                data = res.json()
            except ValueError:
                res.raise_for_status()
                return {}

            if _is_plan_block_error(data):
                print(f"⚠️ Plan restriction on {url}")
                return {"response": []}

            if res.status_code == 429 or "Too many requests" in json.dumps(data):
                print("⚠️ Rate limit hit. Switching key...")
                switch_key()
                time.sleep(10)
                continue

            if isinstance(data, dict) and data.get("errors"):
                print(f"⚠️ API errors: {data.get('errors')} — switching key...")
                switch_key()
                time.sleep(5)
                continue

            res.raise_for_status()
            return data

        except requests.exceptions.RequestException as e:
            print(f"❌ Network error: {e}")
            time.sleep(10)
            continue

    print("❌ All keys exhausted or repeated errors")
    return {"response": []}

def fetch_matches_by_date(date_str):
    url = f"{BASE_URL}?date={date_str}&timezone={TIMEZONE}"
    data = fetch_json(url)
    return data.get("response", [])

def fetch_fixture_data(fixture_id, data_type):
    url = f"https://v3.football.api-sports.io/fixtures/{data_type}?fixture={fixture_id}"
    data = fetch_json(url)
    time.sleep(PAUSE_SEC)
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
    schedule_data = []
    url = SCHEDULE_URLS.get(league_name)
    if url:
        try:
            data = fetch_json(url)
            if isinstance(data, list):
                schedule_data = data
            elif isinstance(data, dict) and "response" in data:
                schedule_data = data["response"]
        except Exception:
            schedule_data = []

    if not schedule_data:
        local_file = os.path.join(SCHEDULE_DIR, f"{league_name}.json")
        if os.path.exists(local_file):
            with open(local_file, "r", encoding="utf-8") as f:
                try:
                    schedule_data = json.load(f)
                except Exception:
                    schedule_data = []

    best_match = None
    best_score = 0.0
    for match in schedule_data:
        sched_date = match.get("Date", "")[:10]
        if sched_date != match_date:
            continue

        home_sim = max((string_similarity(home_team, n) for n in [match.get("HomeTeamName", ""), match.get("HomeTeamKey", ""), match.get("HomeTeam", "")] if n), default=0)
        away_sim = max((string_similarity(away_team, n) for n in [match.get("AwayTeamName", ""), match.get("AwayTeamKey", ""), match.get("AwayTeam", "")] if n), default=0)
        score = (home_sim + away_sim) / 2
        if score > best_score:
            best_score = score
            best_match = match

    if best_match and best_score >= FUZZY_THRESHOLD:
        return best_match.get("GameId")
    return None

# ---------------- MAIN ---------------- #
def main():
    # ✅ Skip runs outside 6 PM – 3 AM IST
    india = pytz.timezone("Asia/Kolkata")
    now = datetime.now(india)
    if not (now.hour >= 18 or now.hour < 3):
        print("⏸️ Skipping — outside 6 PM – 3 AM IST window.")
        return

    # process last 3 days
    deltas = [-2, -1, 0]

    for delta in deltas:
        target_date = datetime.utcnow() + timedelta(days=delta)
        date_str = format_date(target_date)
        print(f"\n📅 Fetching matches for {date_str}...")

        all_fixtures = fetch_matches_by_date(date_str)

        for league_name, league_id in LEAGUES.items():
            fixtures = [fx for fx in all_fixtures if fx.get("league", {}).get("id") == league_id]
            if not fixtures:
                print(f"No matches found for {league_name} on {date_str}.")
                continue

            output_file = os.path.join(OUTPUT_DIR, f"{league_name}.json")

            # Load existing data
            if os.path.exists(output_file):
                with open(output_file, "r", encoding="utf-8") as fh:
                    try:
                        existing_data = {m["StatsId"]: m for m in json.load(fh)}
                    except Exception:
                        existing_data = {}
            else:
                existing_data = {}

            for fx in fixtures:
                fixture_id = fx["fixture"]["id"]
                match_date = fx["fixture"]["date"][:10]
                home_team = fx["teams"]["home"]["name"]
                away_team = fx["teams"]["away"]["name"]
                status = fx["fixture"]["status"]["short"]

                game_id = find_game_id(league_name, match_date, home_team, away_team)
                if not game_id:
                    print(f"⚠️ No GameId found for {home_team} vs {away_team} ({match_date})")
                    continue

                existing = existing_data.get(fixture_id, {})
                match_obj = {
                    "StatsId": fixture_id,
                    "GameId": game_id,
                    "Date": fx["fixture"]["date"],
                    "Status": status,
                    "Round": fx["league"].get("round"),
                    "HomeTeam": home_team,
                    "AwayTeam": away_team,
                    "Score": {"Home": fx.get("goals", {}).get("home"), "Away": fx.get("goals", {}).get("away")},
                    "Events": existing.get("Events", []),
                    "Lineups": existing.get("Lineups", []),
                    "Statistics": existing.get("Statistics", []),
                    "Players": existing.get("Players", []),
                    "HeadToHead": existing.get("HeadToHead", [])
                }

                # ✅ Re-fetch if data missing (even for past fixtures)
                need_refetch = False
                for key in ["Events", "Lineups", "Statistics", "Players"]:
                    if not match_obj[key]:
                        need_refetch = True
                        print(f"  🔁 Missing {key} for {fixture_id}, refetching...")
                        match_obj[key] = fetch_fixture_data(fixture_id, key.lower()) or []

                # always refresh today’s fixtures fully
                if delta == 0:
                    print(f"  ♻️ Today’s match {fixture_id}, refreshing all fields...")
                    for key in ["Events", "Lineups", "Statistics", "Players"]:
                        match_obj[key] = fetch_fixture_data(fixture_id, key.lower()) or []

                existing_data[fixture_id] = match_obj

            # Save updated file
            with open(output_file, "w", encoding="utf-8") as fh:
                json.dump(list(existing_data.values()), fh, ensure_ascii=False, indent=2)

            print(f"💾 Saved {len(existing_data)} total matches to {output_file}")


if __name__ == "__main__":
    main()
