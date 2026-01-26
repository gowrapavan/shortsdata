import asyncio
import json
import os
import random
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from playwright.async_api import async_playwright

BASE_URL = "https://hoofoot.com/"

# This ensures it finds the JSON file inside the /highlights/ folder
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FILENAME = os.path.join(SCRIPT_DIR, "hoofoot_leagues.json")

LEAGUE_IDS = {
    "EPL": 58, "ESP": 59, "DEB": 55, "ITSA": 150,
    "FRL1": 136, "UCL": 78, "DED": 63
}

async def fetch_hoofoot():
    existing_data = []
    existing_urls = set()

    # Load existing data from the specific folder
    if os.path.exists(FILENAME):
        try:
            with open(FILENAME, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                existing_urls = {m["match_url"] for m in existing_data}
            print(f"📖 Loaded {len(existing_urls)} matches from {FILENAME}")
        except Exception as e:
            print(f"⚠️ Error loading JSON: {e}")

    results = existing_data

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        new_links = []
        for name, idp in LEAGUE_IDS.items():
            try:
                print(f"⚽ Checking {name}...")
                await page.goto(f"{BASE_URL}?idp={idp}", timeout=60000)
                await asyncio.sleep(5) # Delay to prevent connection reset
                
                soup = BeautifulSoup(await page.content(), "html.parser")
                for a in soup.select('a[href*="?match="]'):
                    url = urljoin(BASE_URL, a.get("href"))
                    if url not in existing_urls:
                        title = a.find("h2").get_text(strip=True) if a.find("h2") else "Unknown"
                        new_links.append({"league": name, "title": title, "match_url": url})
            except Exception as e:
                print(f"❌ Connection error on {name}: {e}")

        print(f"🆕 Found {len(new_links)} new matches.")

        for i, m in enumerate(new_links, 1):
            try:
                print(f"[{i}/{len(new_links)}] Fetching: {m['title']}")
                await page.goto(m["match_url"], timeout=60000)
                await asyncio.sleep(random.randint(6, 10)) # Stealth delay
                
                soup = BeautifulSoup(await page.content(), "html.parser")
                player = soup.find("div", id="player")
                embed_url = ""
                if player:
                    a_tag = player.find("a", href=True)
                    iframe = player.find("iframe", src=True)
                    if a_tag: embed_url = a_tag["href"]
                    elif iframe: embed_url = iframe["src"]

                if embed_url:
                    results.append({**m, "embed_url": embed_url})
                    # Progressive save to JSON
                    with open(FILENAME, "w", encoding="utf-8") as f:
                        json.dump(results, f, indent=2, ensure_ascii=False)
            except:
                continue

        await browser.close()

if __name__ == "__main__":
    asyncio.run(fetch_hoofoot())
