// Render build/out/book.html to build/out/raw.pdf with Paged.js in Chromium.
import { chromium } from "playwright-core";
import { fileURLToPath } from "url";
import path from "path";
import fs from "fs";

const here = path.dirname(fileURLToPath(import.meta.url));
const html = path.join(here, "out", "book.html");
const out = path.join(here, "out", "raw.pdf");
const exe = process.env.CHROMIUM_PATH ||
  fs.readdirSync("/opt/pw-browsers").filter(d => d.startsWith("chromium-"))
    .map(d => `/opt/pw-browsers/${d}/chrome-linux/chrome`).find(fs.existsSync);

const browser = await chromium.launch({ executablePath: exe, args: ["--allow-file-access-from-files"] });
const page = await browser.newPage();
page.on("console", m => { if (m.type() === "error" || m.type() === "warning") console.log("[page]", m.text()); });
await page.goto("file://" + html, { waitUntil: "load" });
await page.evaluate(() => document.fonts.ready);
await page.addScriptTag({ content: "window.PagedConfig = { auto: false };" });
await page.addScriptTag({ path: path.join(here, "node_modules/pagedjs/dist/paged.polyfill.js") });
const pages = await page.evaluate(async () => {
  const flow = await window.PagedPolyfill.preview();
  return flow.total;
});
console.log("pages:", pages);
// Folio 1 = first page of the Introduction; fill TOC page numbers to match.
await page.evaluate(() => {
  const pageOf = el => el.closest(".pagedjs_page");
  const all = [...document.querySelectorAll(".pagedjs_page")];
  const intro = pageOf(document.getElementById("ch-intro"));
  const first = all.indexOf(intro);
  all.forEach((p, i) => { if (i >= first) p.style.counterReset = `page ${i - first}`; });
  document.querySelectorAll(".toc-list a").forEach(a => {
    const target = document.getElementById(a.getAttribute("href").slice(1));
    a.querySelector(".toc-pg").textContent = all.indexOf(pageOf(target)) - first + 1;
  });
});
// Record which pages are full-page inserts so finalize_pdf.py can drop the vector PDFs in.
const inserts = await page.evaluate(() =>
  [...document.querySelectorAll(".pagedjs_page")].map((p, i) => {
    const s = p.querySelector("section[data-insert]");
    return s ? { index: i, file: s.dataset.insert } : null;
  }).filter(Boolean));
fs.writeFileSync(path.join(here, "out", "inserts.json"), JSON.stringify(inserts, null, 1));
await page.pdf({ path: out, preferCSSPageSize: true, printBackground: true });
await browser.close();
console.log("wrote", out);
