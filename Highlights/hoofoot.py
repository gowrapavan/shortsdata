import asyncio
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from playwright.async_api import async_playwright

BASE_URL = "https://hoofoot.com/"

# The specific leagues you requested
LEAGUE_IDS = {
    "EPL": 58,
    "ESP": 59,
    "DEB": 55,
    "ITSA": 150,
    "FRL1": 136,
    "UCL": 78,
    "DED": 63
}

async def fetch_hoofoot():
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()

        all_match_links = []

        # --- STEP 1: CRAWL LEAGUE PAGES ---
        for name, idp in LEAGUE_IDS.items():
            league_url = f"{BASE_URL}?idp={idp}"
            print(f"⚽ Accessing League: {name} ({league_url})")
            
            try:
                await page.goto(league_url, timeout=60000)
                await page.wait_for_timeout(2000) # Small wait for content
                
                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")

                # Find all match links on this specific league page
                found_in_league = 0
                for a in soup.select('a[href*="?match="]'):
                    title_tag = a.find("h2")
                    if title_tag:
                        title = title_tag.get_text(strip=True)
                        match_url = urljoin(BASE_URL, a.get("href"))
                        
                        # Avoid duplicates if a match appears in multiple sections
                        if not any(m['match_url'] == match_url for m in all_match_links):
                            all_match_links.append({
                                "league": name,
                                "title": title,
                                "match_url": match_url
                            })
                            found_in_league += 1
                
                print(f"   📊 Found {found_in_league} new matches in {name}")

            except Exception as e:
                print(f"   ❌ Error loading league {name}: {e}")

        # --- STEP 2: FETCH EMBED URLS FOR EACH MATCH ---
        total_matches = len(all_match_links)
        print(f"\n🚀 Total matches to process: {total_matches}")

        for i, m in enumerate(all_match_links, 1):
            print(f"[{i}/{total_matches}] Extracting video: {m['title']}")

            try:
                await page.goto(m["match_url"], timeout=60000)
                await page.wait_for_timeout(3000) # Wait for player to load

                match_html = await page.content()
                match_soup = BeautifulSoup(match_html, "html.parser")

                embed_url = ""
                player = match_soup.find("div", id="player")
                if player:
                    a_tag = player.find("a", href=True)
                    if a_tag:
                        embed_url = a_tag["href"]

                results.append({
                    "league": m["league"],
                    "title": m["title"],
                    "match_url": m["match_url"],
                    "embed_url": embed_url
                })

            except Exception as e:
                print(f"   ❌ Failed to get video for: {m['title']}")

        await browser.close()

    return results

if __name__ == "__main__":
    data = asyncio.run(fetch_hoofoot())

    with open("hoofoot_leagues.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Done! Saved {len(data)} matches to hoofoot_leagues.json")
