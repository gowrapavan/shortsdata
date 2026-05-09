import requests
import re
import json
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import random
import os
from urllib.parse import urlparse, parse_qs


# === Random logo placeholders ===
LOGOS = [
    "https://raw.githubusercontent.com/gowrapavan/Goal4u/main/public/assets/img/tv-logo/aves.png",
    "https://raw.githubusercontent.com/gowrapavan/Goal4u/main/public/assets/img/tv-logo/benfica.png",
    "https://raw.githubusercontent.com/gowrapavan/Goal4u/main/public/assets/img/tv-logo/braga.png",
    "https://raw.githubusercontent.com/gowrapavan/Goal4u/main/public/assets/img/tv-logo/fcboavista.png",
    "https://raw.githubusercontent.com/gowrapavan/Goal4u/main/public/assets/img/tv-logo/maritimo.png",
    "https://raw.githubusercontent.com/gowrapavan/Goal4u/main/public/assets/img/tv-logo/porto.png",
    "https://raw.githubusercontent.com/gowrapavan/Goal4u/main/public/assets/img/tv-logo/sporting.png",
    "https://raw.githubusercontent.com/gowrapavan/Goal4u/main/public/assets/img/tv-logo/valencia.png",
]

def random_logo():
    return random.choice(LOGOS)


# === Timezones ===
IST = pytz.timezone("Asia/Kolkata")
GMT = pytz.timezone("GMT")

def convert_time(timestr, src_tz):
    """Convert HH:MM string from src timezone to IST with today's date."""
    now = datetime.now()
    dt = datetime.strptime(timestr, "%H:%M")
    dt = dt.replace(year=now.year, month=now.month, day=now.day)
    dt = src_tz.localize(dt).astimezone(IST)
    return dt.strftime("%Y-%m-%d %H:%M IST")


def short_label(home, away):
    """Generate short label like bri-man."""
    h = re.sub(r'[^a-z]', '', home.lower())[:3] or home.lower()[:3]
    a = re.sub(r'[^a-z]', '', away.lower())[:3] or away.lower()[:3]
    return f"{h}-{a}"


# === Load Team Data from GitHub ===
TEAM_SOURCES = {
    "EPL": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/EPL.json",
    "ESP": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/ESP.json",
    "FRL1": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/FRL1.json",
    "ITSA": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/ITSA.json",
    "DED": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/DED.json",
    "DEB": "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/DEB.json",
}

TEAM_DATA = []

def load_team_data():
    global TEAM_DATA
    if TEAM_DATA:
        return TEAM_DATA
    for name, url in TEAM_SOURCES.items():
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                TEAM_DATA.extend(resp.json())
        except Exception as e:
            print(f"⚠️ Failed loading {name}: {e}")
    return TEAM_DATA

def find_team_crest(team_name):
    """Find crest URL for given team name."""
    team_name_low = team_name.lower()
    for team in TEAM_DATA:
        if team_name_low in team["name"].lower() or team_name_low in team.get("shortName", "").lower():
            return team.get("crest")
    for team in TEAM_DATA:
        if team_name_low.split()[0] in team["name"].lower():
            return team.get("crest")
    return random_logo()


# ---------- 1. SportsOnline ----------
def fetch_sportzonline():
    load_team_data()
    url = "https://sportsonline.st/prog.txt"
    text = requests.get(url, timeout=10).text

    today = datetime.now(IST).strftime("%A").upper()
    pattern = rf"{today}\n(.*?)(?=\n[A-Z]+\n|$)"
    m = re.search(pattern, text, re.S)
    if not m:
        return []

    block = m.group(1)
    matches = []

    for line in block.splitlines():
        m = re.match(r"(\d{2}:\d{2})\s+(.+?)\s+x\s+(.+?) \| (http.+)", line)
        if m:
            time_str, home, away, url = m.groups()
            time_ist = convert_time(time_str, GMT)
            home_logo = find_team_crest(home.strip())
            away_logo = find_team_crest(away.strip())

            matches.append({
                "time": time_ist,
                "game": "football",
                "league": "",
                "home_team": home.strip(),
                "away_team": away.strip(),
                "label": short_label(home, away),
                "home_logo": home_logo,
                "away_logo": away_logo,
                "url": url.strip()
            })
    return matches


# ---------- 2. Hesgoal ----------
def fetch_hesgoal():
    load_team_data()
    url = "https://hesgoal.im/today-matches/"
    headers = {"User-Agent": "Mozilla/5.0"}
    html = requests.get(url, headers=headers, timeout=10).text
    soup = BeautifulSoup(html, "html.parser")

    matches = []

    for event in soup.select("div.EventBox"):
        teams = event.select("div.EventTeamName")
        if len(teams) < 2:
            continue

        # Teams
        home = teams[1].text.strip()
        away = teams[0].text.strip()

        # League
        league_tag = event.select_one("ul.EventFooter li:nth-child(3)")
        league = league_tag.text.strip() if league_tag else ""

        # Link
        link_tag = event.select_one("a#EventLink")
        raw_link = ""
        if link_tag and "href" in link_tag.attrs:
            raw_link = link_tag["href"].strip()

        # --------------------------
        # 🔥 FIX: GENERATE URL IF href="#" OR EMPTY
        # --------------------------
       # --------------------------
        # 🔥 FIX: GENERATE URL IF href="#" OR EMPTY
        # --------------------------
        if raw_link in ("", "#"):
            # Hesgoal format is ALWAYS: away-vs-home
            away_slug = away.lower().replace(" ", "-")
            home_slug = home.lower().replace(" ", "-")
            slug = f"{away_slug}-vs-{home_slug}"
            raw_link = f"https://hesgoal.im/{slug}"


        event_link = raw_link

        # Time
        date_tag = event.select_one("span.EventDate")
        if date_tag and "data-start" in date_tag.attrs:
            dt = datetime.fromisoformat(date_tag["data-start"].strip())
            dt_ist = dt.astimezone(IST)
            time_ist = dt_ist.strftime("%Y-%m-%d %H:%M IST")
        else:
            time_ist = ""

        # Logos
        imgs = event.select("img")
        home_logo = imgs[1]["data-img"] if len(imgs) > 1 and imgs[1].has_attr("data-img") else find_team_crest(home)
        away_logo = imgs[0]["data-img"] if imgs and imgs[0].has_attr("data-img") else find_team_crest(away)

        # --------------------------
        # CHECK IF EXTERNAL PAGE
        # --------------------------
        parsed = urlparse(event_link)
        is_external = parsed.netloc not in ("hesgoal.im", "www.hesgoal.im")

        servers = []
        final_url = ""

        # --------------------------
        # 🌐 EXTERNAL PAGE
        # --------------------------
        if is_external:
            try:
                ext_html = requests.get(event_link, headers=headers, timeout=10).text
                ext_soup = BeautifulSoup(ext_html, "html.parser")

                # MAIN iframe
                iframe = ext_soup.select_one("iframe")
                if iframe and iframe.has_attr("src"):
                    raw = iframe["src"]
                    p = urlparse(raw)
                    qs = parse_qs(p.query)
                    final_url = qs.get("src", [""])[0] or raw

                # ONLY <a target="search_iframe">
                for a in ext_soup.select('a[target="search_iframe"]'):
                    if not a.has_attr("href"):
                        continue

                    name = a.text.strip() or "Server"
                    href = a["href"]

                    p = urlparse(href)
                    qs = parse_qs(p.query)
                    clean = qs.get("src", [""])[0] or href

                    if clean.startswith("http"):
                        servers.append({
                            "name": name,
                            "url": clean
                        })

            except Exception as e:
                print("⚠️ External match parse failed:", e)

        else:
            # INTERNAL normal Hesgoal
            slug = event_link.rstrip("/").split("/")[-1]
            final_url = f"https://yallashoot.cfd/albaplayer/{slug}/"

        # --------------------------
        # FINAL MATCH
        # --------------------------
        matches.append({
            "time": time_ist,
            "game": "football",
            "league": league,
            "home_team": home,
            "away_team": away,
            "label": short_label(home, away),
            "home_logo": home_logo or random_logo(),
            "away_logo": away_logo or random_logo(),
            "url": final_url,
            "servers": servers
        })

    return matches

    
    
# ---------- 3. Yallashooote ----------
def fetch_yallashooote():
    """Scrape YallaShooote with full internal/external link resolving."""

    BASE_NEW = "https://goal-koora.com"
    BASE_NEW_LIVE = "https://goal-koora.com/live/"

    url = "https://yallashooote.online/"
    headers = {"User-Agent": "Mozilla/5.0"}
    html = requests.get(url, headers=headers, timeout=10).text
    soup = BeautifulSoup(html, "html.parser")

    matches = []

    for div in soup.select("div.m_block.alba_sports_events-event_item"):

        # -----------------------------------------------
        # 1️⃣ Extract match link (href)
        # -----------------------------------------------
        link_tag = div.select_one("a.alba_sports_events_link")
        if not link_tag or "href" not in link_tag.attrs:
            continue

        raw_href = link_tag["href"].strip()

        # -----------------------------------------------
        # 2️⃣ INTERNAL LINK ( /bein1 , /hd2 etc.)
        # -----------------------------------------------
        if raw_href.startswith("/"):

            slug = raw_href.lstrip("/")  # remove leading /
            # build final URL (using goal-koora)
            iframe_url = f"{BASE_NEW_LIVE}{slug}.php"

        # -----------------------------------------------
        # 3️⃣ EXTERNAL LINK → Fetch & extract iframe
        # -----------------------------------------------
        else:
            iframe_url = None

            try:
                ext_html = requests.get(raw_href, headers=headers, timeout=10).text
                ext_soup = BeautifulSoup(ext_html, "html.parser")

                # The iframe is inside <div id='post_middle'>
                iframe_tag = ext_soup.select_one("#post_middle iframe")
                if iframe_tag and "src" in iframe_tag.attrs:
                    extracted_src = iframe_tag["src"].strip()

                    # ALWAYS replace yallashooote domain inside iframe src
                    extracted_src = extracted_src.replace("https://yallashooote.online", BASE_NEW)
                    extracted_src = extracted_src.replace("https://yallashooote.online/live", BASE_NEW_LIVE)

                    # Always convert base domain to goal-koora
                    # Example: https://goal-koora.com/live/bein1.php
                    iframe_url = extracted_src

            except Exception as e:
                print("⚠️ External link fetch failed:", raw_href, e)

            if not iframe_url:
                # fallback → keep raw external link
                iframe_url = raw_href

        # ------------------------------------------------
        # 4️⃣ Extract TEAMS
        # ------------------------------------------------
        home_tag = div.select_one("div.team-first .alba_sports_events-team_title, div.team-first .h2.alba_sports_events-team_title")
        away_tag = div.select_one("div.team-second .alba_sports_events-team_title, div.team-second .h2.alba_sports_events-team_title")
        home = home_tag.text.strip() if home_tag else ""
        away = away_tag.text.strip() if away_tag else ""

        # ------------------------------------------------
        # 5️⃣ Extract LOGOS
        # ------------------------------------------------
        home_logo_tag = div.select_one("div.team-first .alba-team_logo img")
        away_logo_tag = div.select_one("div.team-second .alba-team_logo img")

        home_logo = home_logo_tag["src"].strip() if home_logo_tag and "src" in home_logo_tag.attrs else random_logo()
        away_logo = away_logo_tag["src"].strip() if away_logo_tag and "src" in away_logo_tag.attrs else random_logo()

        # ------------------------------------------------
        # 6️⃣ Extract & convert TIME → IST
        # ------------------------------------------------
        date_tag = div.select_one("div.date[data-start]")
        if date_tag and "data-start" in date_tag.attrs:
            try:
                dt_str = date_tag["data-start"].strip()
                dt = datetime.strptime(dt_str, "%Y/%m/%d %H:%M")
                dt = GMT.localize(dt).astimezone(IST)
                time_ist = dt.strftime("%Y-%m-%d %H:%M IST")
            except Exception:
                time_ist = ""
        else:
            time_ist = ""

        # ------------------------------------------------
        # 7️⃣ Append match object
        # ------------------------------------------------
        matches.append({
            "time": time_ist,
            "game": "football",
            "league": "",
            "home_team": home,
            "away_team": away,
            "label": short_label(home, away) if home and away else "yalla",
            "home_logo": home_logo,
            "away_logo": away_logo,
            "url": iframe_url  # FINAL FIXED STREAM URL
        })

    return matches

def fetch_livekora():
    """
    Updated LiveKora logic:
    - Go to livekora.vip
    - Collect match hrefs
    - Open each href page
    - Extract iframe#streamFrame src as final URL
    """

    url = "https://www.livekora.vip/"
    headers = {"User-Agent": "Mozilla/5.0"}
    html = requests.get(url, headers=headers, timeout=10).text
    soup = BeautifulSoup(html, "html.parser")

    matches = []

    for a_tag in soup.select("div.benacer-matches-container a[href]"):
        match_href = a_tag["href"].strip()

        # Ensure absolute URL
        if match_href.startswith("/"):
            match_url = f"https://www.livekora.vip{match_href}"
        else:
            match_url = match_href

        # -----------------------------
        # Extract teams
        # -----------------------------
        right_team = a_tag.select_one("div.right-team .team-name")
        left_team = a_tag.select_one("div.left-team .team-name")

        home = right_team.text.strip() if right_team else ""
        away = left_team.text.strip() if left_team else ""

        # -----------------------------
        # Extract logos
        # -----------------------------
        home_logo_tag = a_tag.select_one("div.right-team .team-logo img")
        away_logo_tag = a_tag.select_one("div.left-team .team-logo img")

        home_logo = home_logo_tag["src"].strip() if home_logo_tag and home_logo_tag.has_attr("src") else random_logo()
        away_logo = away_logo_tag["src"].strip() if away_logo_tag and away_logo_tag.has_attr("src") else random_logo()

        # -----------------------------
        # Extract & convert time
        # -----------------------------
        time_tag = a_tag.select_one("span.date[data-start]")
        if time_tag:
            try:
                dt = datetime.fromisoformat(time_tag["data-start"])
                time_ist = dt.astimezone(IST).strftime("%Y-%m-%d %H:%M IST")
            except Exception:
                time_ist = ""
        else:
            time_ist = ""

        # -----------------------------
        # 🔥 OPEN MATCH PAGE → FIND IFRAME
        # -----------------------------
        final_stream_url = ""
        try:
            match_html = requests.get(match_url, headers=headers, timeout=10).text
            match_soup = BeautifulSoup(match_html, "html.parser")

            iframe = match_soup.select_one("iframe#streamFrame")
            if iframe and iframe.has_attr("src"):
                final_stream_url = iframe["src"].strip()

        except Exception as e:
            print("⚠️ LiveKora iframe fetch failed:", e)

        # -----------------------------
        # Append match
        # -----------------------------
        matches.append({
            "time": time_ist,
            "game": "football",
            "league": "",
            "home_team": home,
            "away_team": away,
            "label": short_label(home, away) if home and away else "livekora",
            "home_logo": home_logo,
            "away_logo": away_logo,
            "url": final_stream_url
        })

    return matches


def fetch_siiir():
    """
    Scrape www.siir-tv.live
    - Extract matches from the main page
    - Open match page (e.g. romi.vip-gx.online/...)
    - Extract iframe src and prepend corsproxy.io
    """
    load_team_data()
    
    url = "https://www.siir-tv.live/"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        html = requests.get(url, headers=headers, timeout=10).text
        soup = BeautifulSoup(html, "html.parser")
    except Exception as e:
        print(f"⚠️ Failed to fetch Sir TV main page: {e}")
        return []

    matches = []
    
    # Sir TV uses Egypt/Saudi time (UTC+3)
    SAUDI_TZ = pytz.timezone("Asia/Riyadh")

    for match_div in soup.select("div.match-container"):
        
        # -----------------------------
        # 1. Teams
        # -----------------------------
        home_tag = match_div.select_one(".right-team .team-name")
        away_tag = match_div.select_one(".left-team .team-name")

        home = home_tag.text.strip() if home_tag else ""
        away = away_tag.text.strip() if away_tag else ""

        if not home or not away:
            continue

        # -----------------------------
        # 2. Logos (Handle Lazy Loading)
        # -----------------------------
        home_img = match_div.select_one(".right-team .team-logo img")
        away_img = match_div.select_one(".left-team .team-logo img")

        home_logo = home_img.get("data-src") or home_img.get("src") if home_img else None
        away_logo = away_img.get("data-src") or away_img.get("src") if away_img else None

        # Fallback if image is a base64 lazy-load gif
        if not home_logo or "data:image" in home_logo:
            home_logo = find_team_crest(home)
        if not away_logo or "data:image" in away_logo:
            away_logo = find_team_crest(away)

        # -----------------------------
        # 3. League
        # -----------------------------
        league = ""
        info_items = match_div.select(".match-info ul li span")
        if len(info_items) >= 3:
            league = info_items[2].text.strip()

        # -----------------------------
        # 4. Time -> Convert to IST
        # -----------------------------
        time_ist = ""
        time_tag = match_div.select_one(".match-time")
        
        if time_tag:
            time_str = time_tag.text.strip()  # Example format: "2:30 PM"
            try:
                now = datetime.now()
                # Parse 12-hour AM/PM time
                dt = datetime.strptime(time_str, "%I:%M %p")
                dt = dt.replace(year=now.year, month=now.month, day=now.day)
                
                # Convert Saudi Time (UTC+3) to IST (UTC+5:30)
                dt_saudi = SAUDI_TZ.localize(dt)
                dt_ist = dt_saudi.astimezone(IST)
                time_ist = dt_ist.strftime("%Y-%m-%d %H:%M IST")
            except Exception:
                # Fallback to original text if parsing fails
                time_ist = time_str

        # -----------------------------
        # 5. Extract Match Page Link
        # -----------------------------
        a_tag = match_div.select_one("a.ahmed")
        if not a_tag or not a_tag.has_attr("href"):
            continue
            
        match_url = a_tag["href"].strip()

        # -----------------------------
        # 6. Open match page -> extract iframe
        # -----------------------------
        final_stream_url = ""
        
        try:
            match_html = requests.get(match_url, headers=headers, timeout=10).text
            match_soup = BeautifulSoup(match_html, "html.parser")
            
            # The streaming iframe is inside the .entry-content div
            iframe = match_soup.select_one(".entry-content iframe")
            if iframe and iframe.has_attr("src"):
                raw_src = iframe["src"].strip()
                # 🔥 APPEND CORSPROXY TO THE RAW URL
                final_stream_url = f"https://corsproxy.io/?{raw_src}"
                
        except Exception as e:
            print(f"⚠️ siiir iframe fetch failed for {home} vs {away}: {e}")

        # -----------------------------
        # 7. Append match
        # -----------------------------
        matches.append({
            "time": time_ist,
            "game": "football",
            "league": league,
            "home_team": home,
            "away_team": away,
            "label": short_label(home, away),
            "home_logo": home_logo or random_logo(),
            "away_logo": away_logo or random_logo(),
            "url": final_stream_url
        })

    return matches
    
    def fetch_livesoccerhd():
    """
    Scrape livesoccerhd.info
    - Extract matches from div.AY_Match
    - Open each href page
    - Extract iframe src as final stream URL
    """

    load_team_data()

    url = "https://www.livesoccerhd.info/"
    headers = {"User-Agent": "Mozilla/5.0"}
    html = requests.get(url, headers=headers, timeout=10).text
    soup = BeautifulSoup(html, "html.parser")

    matches = []

    for match_div in soup.select("div.AY_Match"):

        # -----------------------------
        # Teams
        # -----------------------------
        home_tag = match_div.select_one(".TM1 .TM_Name")
        away_tag = match_div.select_one(".TM2 .TM_Name")

        home = home_tag.text.strip() if home_tag else ""
        away = away_tag.text.strip() if away_tag else ""

        # -----------------------------
        # Logos (use data-src, not src)
        # -----------------------------
        home_logo_tag = match_div.select_one(".TM1 .TM_Logo img")
        away_logo_tag = match_div.select_one(".TM2 .TM_Logo img")

        home_logo = home_logo_tag.get("data-src") if home_logo_tag else None
        away_logo = away_logo_tag.get("data-src") if away_logo_tag else None

        if not home_logo:
            home_logo = find_team_crest(home)
        if not away_logo:
            away_logo = find_team_crest(away)

        # -----------------------------
        # League
        # -----------------------------
        league = ""
        info_items = match_div.select(".MT_Info ul li span")
        if len(info_items) >= 3:
            league = info_items[2].text.strip()

        # -----------------------------
        # Time (only HH:MM AM/PM, no date)
        # We'll keep raw for now
        # -----------------------------
        time_tag = match_div.select_one(".MT_Time")
        time_raw = time_tag.text.strip() if time_tag else ""
        time_ist = time_raw  # site does not give timezone safely

        # -----------------------------
        # Match page href
        # -----------------------------
        a_tag = match_div.select_one("a[href]")
        if not a_tag:
            continue

        match_url = a_tag["href"].strip()

        # -----------------------------
        # 🔥 Open match page → extract iframe src
        # -----------------------------
        final_stream_url = ""

        try:
            match_html = requests.get(match_url, headers=headers, timeout=10).text
            match_soup = BeautifulSoup(match_html, "html.parser")

            iframe = match_soup.select_one("iframe")
            if iframe and iframe.has_attr("src"):
                final_stream_url = iframe["src"].strip()

        except Exception as e:
            print("⚠️ livesoccerhd iframe fetch failed:", e)

        # -----------------------------
        # Append match
        # -----------------------------
        matches.append({
            "time": time_ist,
            "game": "football",
            "league": league,
            "home_team": home,
            "away_team": away,
            "label": short_label(home, away) if home and away else "livesoccerhd",
            "home_logo": home_logo or random_logo(),
            "away_logo": away_logo or random_logo(),
            "url": final_stream_url
        })

    return matches

def fetch_streamfree():
    """
    Scrapes streamfree.app using their internal JSON API.
    Returns all live and upcoming soccer matches.
    """
    load_team_data()
    
    url = "https://streamfree.app/streams"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json",
        "Referer": "https://streamfree.app/"
    }
    
    matches = []
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            print(f"⚠️ StreamFree returned status code {resp.status_code}")
            return []
            
        data = resp.json()
        
        # Grab only the soccer matches (you can change this to grab basketball, etc.)
        soccer_streams = data.get("streams", {}).get("soccer", [])
        
        for match in soccer_streams:
            # 1. Extract Name & Teams
            name = match.get("name", "")
            home = match.get("home_team", "")
            away = match.get("away_team", "")
            
            # If the API didn't separate home/away, try to split the name string manually
            if not home and "vs" in name.lower():
                parts = re.split(r'\s+vs\.?\s+', name, flags=re.IGNORECASE)
                if len(parts) >= 2:
                    home = parts[0].strip()
                    away = parts[1].strip()
            
            if not home:
                home = name
            if not away:
                away = "Away"

            # 2. Extract Category, League, and Keys
            category = match.get("category", "soccer")
            league = match.get("league", "")
            stream_key = match.get("stream_key", "")
            
            # 3. Time Conversion (Unix Timestamp -> IST)
            time_ist = ""
            ts = match.get("match_timestamp")
            if ts:
                # API uses Unix Epoch timestamps
                dt = datetime.fromtimestamp(ts, pytz.utc)
                dt_ist = dt.astimezone(IST)
                time_ist = dt_ist.strftime("%Y-%m-%d %H:%M IST")

            # 4. Extract Logos (Use your crest finder, fallback to their thumbnail)
            home_logo = find_team_crest(home)
            away_logo = find_team_crest(away)
            
            # If find_team_crest fails, try to use the stream's thumbnail image
            if home_logo in LOGOS: # meaning it fell back to random
                thumb = match.get("thumbnail_url", "")
                if thumb:
                    home_logo = f"https://streamfree.app{thumb}" if thumb.startswith("/") else thumb

            # 5. Build Final URL with Corsproxy
            # The player page source code revealed the iframe path is /embed/{category}/{stream_key}
            raw_iframe_src = f"https://streamfree.app/embed/{category}/{stream_key}?quality=720p&category={category}"
            final_stream_url = f"https://corsproxy.io/?{raw_iframe_src}"

            # 6. Append
            matches.append({
                "time": time_ist,
                "game": "football",
                "league": league,
                "home_team": home,
                "away_team": away,
                "label": short_label(home, away) if home != name else "streamfree",
                "home_logo": home_logo or random_logo(),
                "away_logo": away_logo or random_logo(),
                "url": final_stream_url
            })
            
    except Exception as e:
        print(f"⚠️ Failed to fetch StreamFree API: {e}")
        
    return matches

# === Save JSONs ===
JSON_FOLDER = "json"
os.makedirs(JSON_FOLDER, exist_ok=True)

if __name__ == "__main__":
    sources = {
        "sportsonline.json": fetch_sportzonline,
        "hesgoal.json": fetch_hesgoal,
        "yallashooote.json": fetch_yallashooote,
        "livekora.json": fetch_livekora,
        "siiir.json": fetch_siiir,      # 👈 ADD THIS
        "soccerhd.json": fetch_livesoccerhd,
        "streamfree.json": fetch_streamfree  # 👈 ADD THIS LINE



    }

    for filename, func in sources.items():
        try:
            data = func()
            with open(os.path.join(JSON_FOLDER, filename), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✅ Saved {filename} with {len(data)} entries")
        except Exception as e:
            print(f"❌ Failed to fetch {filename}: {e}")
            with open(os.path.join(JSON_FOLDER, filename), "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)
