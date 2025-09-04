const fs = require("fs");
const puppeteer = require("puppeteer");

(async () => {
  const browser = await puppeteer.launch({
    headless: "new",
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });

  const page = await browser.newPage();

  // Spoof UA to avoid blocking
  await page.setUserAgent(
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " +
      "AppleWebKit/537.36 (KHTML, like Gecko) " +
      "Chrome/124.0.0.0 Safari/537.36"
  );

  // Go to site
  await page.goto("https://shahid-koora.com/", {
    waitUntil: "networkidle2",
    timeout: 60000,
  });

  // Save raw HTML for debugging
  const html = await page.content();
  fs.writeFileSync("debug.html", html, "utf-8");

  // Extract matches
  const matches = await page.$$eval(".card", (cards) =>
    cards.map((card) => {
      const league =
        card.querySelector(".league")?.innerText.trim() || "";
      const home =
        card.querySelector(".teams .team:first-child .name")?.innerText.trim() || "";
      const away =
        card.querySelector(".teams .team:last-child .name")?.innerText.trim() || "";
      const time =
        card.querySelector(".meta")?.innerText.trim() || "";
      const link =
        card.querySelector("a.watch-link")?.getAttribute("data-url") || "";
      return { league, home, away, time, url: link };
    })
  );

  // Save JSON
  fs.writeFileSync("dataurls.json", JSON.stringify(matches, null, 2), "utf-8");

  console.log(`✅ Scraped ${matches.length} matches`);
  await browser.close();
})();
