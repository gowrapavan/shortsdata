const fs = require("fs");
const path = require("path");
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

  // Extract matches
  let matches = await page.$$eval(".card", (cards) =>
    cards.map((card) => {
      const league = card.querySelector(".league")?.innerText.trim() || "";
      const home =
        card.querySelector(".teams .team:first-child .name")?.innerText.trim() || "";
      const away =
        card.querySelector(".teams .team:last-child .name")?.innerText.trim() || "";
      const time = card.querySelector(".meta")?.innerText.trim() || "";
      const link =
        card.querySelector("a.watch-link")?.getAttribute("data-url") || "";

      // Create label (first 3 chars of home + "-" + first 3 chars of away)
      const makeLabel = (h, a) => {
        const normalize = (str) =>
          str.replace(/\s+/g, "").substring(0, 3).toLowerCase();
        return `${normalize(h)}-${normalize(a)}`;
      };

      const label = makeLabel(home, away);

      return { league, home, away, time, url: link, label };
    })
  );

  // Remove duplicates by url
  const seen = new Set();
  matches = matches.filter((m) => {
    if (!m.url || seen.has(m.url)) return false;
    seen.add(m.url);
    return true;
  });

  // Ensure /json directory exists
  const outputDir = path.join(__dirname, "json");
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  // Save JSON to /json/shahidkoora.json
  const outputPath = path.join(outputDir, "shahidkoora.json");
  fs.writeFileSync(outputPath, JSON.stringify(matches, null, 2), "utf-8");

  console.log(`✅ Scraped ${matches.length} unique matches → ${outputPath}`);
  await browser.close();
})();
