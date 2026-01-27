import asyncio
import json
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from playwright.async_api import async_playwright
# Import the stealth function
from playwright_stealth import stealth

BASE_URL = "https://hoofoot.com"
# Ensure the script runs from the repository root if called by the workflow
OUTPUT_FILE = "Highlights/hoofoot.json"


async def fetch_hoofoot():
    results = []

    async with async_playwright() as p:
        # Use chromium and provide arguments to disable common bot flags
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--window-size=1920,1080",
                "--ignore-certificate-errors",
            ]
        )

        context = await browser.new_context(
            # Use a current, standard User-Agent
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US"
        )

        page = await context.new_page()
        
        # Apply stealth modifications to the page
        await stealth(page)

        print(f"🌐 Opening home page: {BASE_URL}")
        # Navigate and wait for network to be idle, allowing Cloudflare to finish its check
        await page.goto(BASE_URL + "?home", wait_until="networkidle", timeout=90000)

        # CRITICAL: Wait for a few seconds to let Cloudflare's JavaScript challenge run and set cookies
        print("🕒 Waiting for Cloudflare/JS challenges to resolve (10s)...")
        await page.wait_for_timeout(10000) 

        home_html = await page.content()
        soup = BeautifulSoup(home_html, "html.parser")

        matches = []

        # Debugging: Save the output HTML if 0 matches are found
        with open("debug_output.html", "w", encoding="utf-8") as f:
            f.write(home_html)
        print("📄 Saved current page HTML to debug_output.html for review.")


        for a in soup.select('a[href*="?match="]'):
            title_tag = a.find("h2")
            if not title_tag:
                continue

            title = title_tag.get_text(strip=True)
            match_url = urljoin(BASE_URL, a.get("href"))

            matches.append({
                "title": title,
                "match_url": match_url
            })

        print(f"✅ Found {len(matches)} matches")
        
        if len(matches) == 0:
            print("❌ Found 0 matches. The Cloudflare bypass likely failed. Check debug_output.html.")
            await browser.close()
            return [] # Exit early if nothing is found

        for i, m in enumerate(matches, 1):
            print(f"[{i}/{len(matches)}] Fetching details for:", m["title"])

            try:
                # Use domcontentloaded for detail pages as they might load faster
                await page.goto(m["match_url"], wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(4000) # Give a short wait for the embed player JS to render

                match_html = await page.content()
                match_soup = BeautifulSoup(match_html, "html.parser")

                embed_url = ""

                player = match_soup.find("div", id="player")
                if player:
                    a = player.find("a", href=True)
                    if a:
                        embed_url = a["href"]

                results.append({
                    "title": m["title"],
                    "match_url": m["match_url"],
                    "embed_url": embed_url
                })

                await page.wait_for_timeout(2000)

            except Exception as e:
                print("❌ Failed fetching details for:", m["title"], e)

        await browser.close()

    return results


if __name__ == "__main__":
    # Create the directory if it doesn't exist
    os.makedirs("Highlights", exist_ok=True)

    data = asyncio.run(fetch_hoofoot())

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Saved {OUTPUT_FILE} with {len(data)} matches")
