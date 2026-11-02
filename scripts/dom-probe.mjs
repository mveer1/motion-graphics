#!/usr/bin/env node
// dom-probe.mjs: dump what is visible in a HyperFrames composition at given timeline times, as JSON.
//
//   node scripts/dom-probe.mjs <index.html> --times 0.5,2,4.2 [--width 1280 --height 720]
//
// Uses the puppeteer-core that ships inside the global `hyperframes` install and the Chrome it caches
// (no new dependency). Seeks window.__timelines[<composition id>] (paused GSAP), then reports every visible
// text block and shape with its box in #root pixels, computed font size, colour, opacity and scene.
// Stdout: JSON {format, samples:[{t, items:[...]}]}. Exit 2 when the browser or page cannot be started.
// One browser, closed before exit. Run it through `session-guard.py run render -- node ...` (it is a browser).
import { createRequire } from 'node:module';
import { execSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const args = process.argv.slice(2);
const opt = (n, d) => { const i = args.indexOf('--' + n); return i >= 0 ? args[i + 1] : d; };
const file = args.find((a, i) => !a.startsWith('--') && (i === 0 || !args[i - 1].startsWith('--')));
if (!file || !fs.existsSync(file)) { console.error('usage: dom-probe.mjs <index.html> --times a,b,c'); process.exit(2); }
const times = (opt('times', '1') || '1').split(',').map(Number).filter(Number.isFinite);

function findPuppeteer() {
  const root = execSync('npm root -g', { encoding: 'utf8' }).trim();
  const p = path.join(root, 'hyperframes', 'node_modules', 'puppeteer-core');
  if (!fs.existsSync(p)) throw new Error('puppeteer-core not found inside the global hyperframes install: ' + p);
  return createRequire(import.meta.url)(p);
}
function findChrome() {
  const base = path.join(os.homedir(), '.cache', 'puppeteer');
  for (const [dir, rel] of [['chrome-headless-shell', ['chrome-headless-shell-mac-arm64', 'chrome-headless-shell']], ['chrome', ['chrome-mac-arm64', 'Google Chrome for Testing.app', 'Contents', 'MacOS', 'Google Chrome for Testing']]]) {
    const d = path.join(base, dir);
    if (!fs.existsSync(d)) continue;
    for (const v of fs.readdirSync(d).sort().reverse()) { const exe = path.join(d, v, ...rel); if (fs.existsSync(exe)) return exe; }
  }
  throw new Error('no cached Chrome under ' + base);
}

const collect = () => {
  const root = document.getElementById('root') || document.querySelector('[data-composition-id]');
  const rr = root.getBoundingClientRect();
  const out = [];
  const eff = (el) => { let o = 1; for (let e = el; e && e !== document.documentElement; e = e.parentElement) { o *= parseFloat(getComputedStyle(e).opacity); } return o; };
  const vis = (el) => { for (let e = el; e && e !== document.documentElement; e = e.parentElement) { const s = getComputedStyle(e); if (s.display === 'none' || s.visibility === 'hidden') return false; } return true; };
  const scene = (el) => { const s = el.closest('.st-scene,[data-scene],section[id]'); return s ? (s.id || s.getAttribute('data-scene') || 'scene') : null; };
  { // the root's own background is the page colour: text contrast is judged against it when nothing else sits underneath
    const rcs = getComputedStyle(root);
    if (rcs.backgroundColor && rcs.backgroundColor !== 'rgba(0, 0, 0, 0)') out.push({ k: 'shape', tag: 'root', x: 0, y: 0, w: rr.width, h: rr.height, bg: rcs.backgroundColor, gradient: /gradient/.test(rcs.backgroundImage), radius: 0, shadow: false, border: false, op: 1, scene: null, cls: 'root' });
  }
  for (const el of root.querySelectorAll('*')) {
    if (el.closest('svg') && el.tagName.toLowerCase() !== 'svg') continue;
    if (!vis(el)) continue;
    const o = eff(el);
    if (o < 0.08) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) continue;
    if (r.right < rr.left || r.left > rr.right || r.bottom < rr.top || r.top > rr.bottom) continue;
    const cs = getComputedStyle(el);
    let box = { x: r.left - rr.left, y: r.top - rr.top, w: r.width, h: r.height };
    const own = Array.from(el.childNodes).filter((n) => n.nodeType === 3).map((n) => n.textContent).join('').replace(/\s+/g, ' ').trim();
    if (own) {
      // glyph box: union of the text nodes' client rects (a block's own box can be much wider than its text)
      const rg = document.createRange(); let u = null;
      for (const n of el.childNodes) { if (n.nodeType !== 3 || !n.textContent.trim()) continue; rg.selectNodeContents(n); for (const q of rg.getClientRects()) { if (q.width < 1) continue; u = u ? { l: Math.min(u.l, q.left), t: Math.min(u.t, q.top), r: Math.max(u.r, q.right), b: Math.max(u.b, q.bottom) } : { l: q.left, t: q.top, r: q.right, b: q.bottom }; } }
      if (u) box = { x: u.l - rr.left, y: u.t - rr.top, w: u.r - u.l, h: u.b - u.t };
      out.push({ k: 'text', text: own, ...box, fs: parseFloat(cs.fontSize), fw: cs.fontWeight, color: cs.color, ls: parseFloat(cs.letterSpacing) || 0,
        upper: cs.textTransform === 'uppercase' || (own.length > 2 && own === own.toUpperCase() && /[A-Z]/.test(own)), mono: /mono|courier/i.test(cs.fontFamily),
        family: cs.fontFamily.split(',')[0].replace(/["']/g, ''), op: +o.toFixed(2), scene: scene(el), tag: el.tagName.toLowerCase(), cls: el.className && el.className.baseVal === undefined ? String(el.className) : '' });
    } else {
      const tag = el.tagName.toLowerCase();
      const media = ['svg', 'img', 'video', 'canvas'].includes(tag);
      const bg = cs.backgroundColor, bgi = cs.backgroundImage;
      const painted = (bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent') || (bgi && bgi !== 'none');
      if (!media && !painted) continue;
      out.push({ k: media ? 'media' : 'shape', tag, ...box, bg, gradient: /gradient/.test(bgi), radius: parseFloat(cs.borderTopLeftRadius) || 0,
        shadow: cs.boxShadow !== 'none', border: parseFloat(cs.borderTopWidth) > 0, op: +o.toFixed(2), scene: scene(el), cls: el.className && el.className.baseVal === undefined ? String(el.className) : '' });
    }
  }
  return { w: rr.width, h: rr.height, items: out, fmt: root.getAttribute('data-format') };
};

let browser;
try {
  const puppeteer = findPuppeteer();
  browser = await puppeteer.launch({ executablePath: findChrome(), headless: true, args: ['--no-sandbox', '--disable-gpu', '--hide-scrollbars'] });
  const page = await browser.newPage();
  const W = Number(opt('width', 0)), H = Number(opt('height', 0));
  await page.setViewport({ width: W || 1280, height: H || 720, deviceScaleFactor: 1 });
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e).slice(0, 200)));
  await page.goto(pathToFileURL(path.resolve(file)).href, { waitUntil: 'load', timeout: 60000 });
  await page.waitForFunction(() => window.__timelines && Object.keys(window.__timelines).length > 0, { timeout: 20000 });
  await page.evaluate(() => document.fonts && document.fonts.ready);
  const result = { file, samples: [], errors };
  for (const t of times) {
    await page.evaluate((tt) => { const tl = Object.values(window.__timelines)[0]; tl.pause(); tl.seek(tt, false); }, t);
    await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));
    const d = await page.evaluate(collect);
    result.format = d.fmt; result.size = [d.w, d.h];
    result.samples.push({ t, items: d.items });
  }
  result.duration = await page.evaluate(() => Object.values(window.__timelines)[0].duration());
  console.log(JSON.stringify(result));
} catch (e) {
  console.error('dom-probe failed: ' + (e && e.message || e));
  process.exitCode = 2;
} finally {
  if (browser) await browser.close();
}
