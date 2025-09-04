const fs = require("fs");
const path = require("path");
const puppeteer = require("puppeteer");

// --- Random logos (from your GitHub) ---
const LOGOS = [
  "https://raw.githubusercontent.com/gowrapavan/Goal4u/main/public/assets/img/tv-logo/aves.png",
  "https://raw.githubusercontent.com/gowrapavan/Goal4u/main/public/assets/img/tv-logo/benfica.png",
  "https://raw.githubusercontent.com/gowrapavan/Goal4u/main/public/assets/img/tv-logo/braga.png",
  "https://raw.githubusercontent.com/gowrapavan/Goal4u/main/public/assets/img/tv-logo/fcboavista.png",
  "https://raw.githubusercontent.com/gowrapavan/Goal4u/main/public/assets/img/tv-logo/maritimo.png",
  "https://raw.githubusercontent.com/gowrapavan/Goal4u/main/public/assets/img/tv-logo/porto.png",
  "https://raw.githubusercontent.com/gowrapavan/Goal4u/main/public/assets/img/tv-logo/sporting.png",
  "https://raw.githubusercontent.com/gowrapavan/Goal4u/main/public/assets/img/tv-logo/valencia.png",
];

const randomLogo = () => LOGOS[Math.floor(Math.random() * LOGOS.length)];

const makeLabel = (home, away) => {
  const normalize = (str) => str.replace(/\s+/g, "").substring(0, 3).toLowerCase();
  return `${normalize(home)}-${normalize(away)}`;
};

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
  let matches = await page.$$eval(".card", (cards, logos) =>
    cards.map((card) => {
      const league = card.querySelector(".league")?.innerText.trim() || "";
      const home = card.querySelector(".teams .team:first-child .name")?.innerText.trim() || "";
      const away = card.querySelector(".teams .team:last-child .name")?.innerText.trim() || "";
      const time = card.querySelector(".meta")?.innerText.trim() || "";
      const url = card.querySelector("a.watch-link")?.getAttribute("data-url") || "";

      const normalize = (str) => str.replace(/\s+/g, "").substring(0, 3).toLowerCase();
      const label = `${normalize(home)}-${normalize(away)}`;

      // Random logo
      const Logo = logos[Math.floor(Math.random() * logos.length)];

      return { league, home, away, time, url, label, Logo };
    }),
    LOGOS
  );

  // Remove duplicates by URL
  const seen = new Set();
  matches = matches.filter((m) => {
    if (!m.url || seen.has(m.url)) return false;
    seen.add(m.url);
    return true;
  });

  // Ensure /json directory exists
  const outputDir = path.join(__dirname, "json");
  if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir, { recursive: true });

  // Save JSON
  const outputPath = path.join(outputDir, "shahidkoora.json");
  fs.writeFileSync(outputPath, JSON.stringify(matches, null, 2), "utf-8");

  console.log(`✅ Scraped ${matches.length} unique matches with logos → ${outputPath}`);
  await browser.close();
})();
