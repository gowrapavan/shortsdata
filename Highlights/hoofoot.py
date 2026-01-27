import asyncio
import json
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async 

BASE_URL = "https://hoofoot.com/"
OUTPUT_FILE = "Highlights/hoofoot.json"

async def fetch_hoofoot():
    results = []

    async with async_playwright() as p:
        # Launch with automation-hiding flags
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled"
            ]
        )

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )

        page = await context.new_page()
        
        # Apply stealth to mask Playwright fingerprints
        await stealth_async(page)

        print("🌐 Opening home page and waiting for Cloudflare...")
        try:
            # Go to the site and wait for the initial load
            await page.goto(BASE_URL + "?home", wait_until="domcontentloaded", timeout=90000)
            
            # CRITICAL: Wait 10 seconds for the Cloudflare "Checking browser" screen to pass
            await page.wait_for_timeout(10000)

            home_html = await page.content()
            soup = BeautifulSoup(home_html, "html.parser")

            matches = []
            for a in soup.select('a[href*="?match="]'):
                title_tag = a.find("h2")
                if not title_tag: continue
                
                matches.append({
                    "title": title_tag.get_text(strip=True),
                    "match_url": urljoin(BASE_URL, a.get("href"))
                })

            print(f"✅ Found {len(matches)} matches")

            for i, m in enumerate(matches[:15], 1): # Limit to 15 to avoid long runtimes
                print(f"[{i}/{len(matches)}] Fetching: {m['title']}")
                try:
                    await page.goto(m["match_url"], wait_until="domcontentloaded", timeout=60000)
                    await page.wait_for_timeout(3000) # Wait for JS content

                    match_html = await page.content()
                    match_soup = BeautifulSoup(match_html, "html.parser")

                    embed_url = ""
                    player = match_soup.find("div", id="player")
                    if player:
                        a_tag = player.find("a", href=True)
                        if a_tag:
                            embed_url = a_tag["href"]

                    results.append({
                        "title": m["title"],
                        "match_url": m["match_url"],
                        "embed_url": embed_url
                    })
                except Exception as e:
                    print(f"❌ Failed: {m['title']} - {e}")

        except Exception as e:
            print(f"❌ Main page load failed: {e}")

        await browser.close()

    return results

if __name__ == "__main__":
    os.makedirs("Highlights", exist_ok=True)
    data = asyncio.run(fetch_hoofoot())
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Saved {len(data)} matches to {OUTPUT_FILE}")
