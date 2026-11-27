#!/usr/bin/env node
// render-sheets.mjs: render Sinew brand sheets (assets/fitness/sheets/*.html) to PNG previews and SVG sources.
//
//   node render-sheets.mjs <repo-root> <out-dir> <sheet.html>...
//
// Called by `python scripts/fitness.py sheets`, which holds the host render lock (one headless Chrome at a time).
// Uses puppeteer-core inside the global hyperframes install and the Chrome it caches (as tests/studio-runtime/run-page.mjs).
// Each page sets data-width/height on #root, data-still (seconds to seek before the shot) and optionally
// data-export-svg="<name>" to also write the #stage SVG to assets/fitness/brand/<name>.svg (the editable source).
import { createRequire } from 'node:module';
import { execSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const [root, outDir, ...pages] = process.argv.slice(2);
const npmRoot = execSync('npm root -g', { encoding: 'utf8' }).trim();
const puppeteer = createRequire(import.meta.url)(path.join(npmRoot, 'hyperframes', 'node_modules', 'puppeteer-core'));
function findChrome() {
  if (process.env.CHROME) return process.env.CHROME;
  const base = path.join(os.homedir(), '.cache', 'puppeteer');
  // macOS (the render host) first, then the Windows cache layout of the same Puppeteer downloads
  for (const [dir, rel] of [['chrome-headless-shell', ['chrome-headless-shell-mac-arm64', 'chrome-headless-shell']], ['chrome', ['chrome-mac-arm64', 'Google Chrome for Testing.app', 'Contents', 'MacOS', 'Google Chrome for Testing']],
    ['chrome-headless-shell', ['chrome-headless-shell-win64', 'chrome-headless-shell.exe']], ['chrome', ['chrome-win64', 'chrome.exe']]]) {
    const d = path.join(base, dir);
    if (!fs.existsSync(d)) continue;
    for (const v of fs.readdirSync(d).sort().reverse()) { const exe = path.join(d, v, ...rel); if (fs.existsSync(exe)) return exe; }
  }
  throw new Error('no cached Chrome under ' + base);
}
const browser = await puppeteer.launch({ executablePath: findChrome(), headless: true, args: ['--no-sandbox', '--allow-file-access-from-files'] });
let failed = 0;
for (const file of pages) {
  const page = await browser.newPage();
  const errs = [];
  page.on('pageerror', e => errs.push(e.message));
  page.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  await page.setViewport({ width: 1600, height: 1200 });
  await page.goto(pathToFileURL(file).href, { waitUntil: 'load' });
  await page.waitForFunction(() => document.getElementById('root')?.getAttribute('data-studio-ready') === 'true', { timeout: 20000 }).catch(() => errs.push('timeline never registered'));
  const size = await page.evaluate(() => { const r = document.getElementById('root'); return { w: +r.getAttribute('data-width'), h: +r.getAttribute('data-height') }; });
  await page.setViewport({ width: size.w, height: size.h });
  await page.evaluate(() => document.fonts && document.fonts.ready);
  const info = await page.evaluate(() => {
    const r = document.getElementById('root');
    const still = parseFloat(r.getAttribute('data-still') || '0');
    const tl = window.__timelines && window.__timelines.root;
    if (tl) { tl.seek(0, false); tl.seek(still, false); }
    const st = document.getElementById('stage');
    return { w: +r.getAttribute('data-width'), h: +r.getAttribute('data-height'), svg: r.getAttribute('data-export-svg'), markup: st ? new XMLSerializer().serializeToString(st) : null, t: tl ? tl.time() : -1 };
  });
  const name = path.basename(file, '.html');
  const png = path.join(outDir, name + '.png');
  await page.screenshot({ path: png, clip: { x: 0, y: 0, width: info.w, height: info.h } });
  if (info.svg && info.markup) {
    const svgOut = path.join(root, 'assets', 'fitness', 'brand', info.svg + '.svg');
    fs.writeFileSync(svgOut, '<?xml version="1.0" encoding="UTF-8"?>\n<!-- Generated from assets/fitness/sheets/' + name + '.html by render-sheets.mjs; the kit JS is the master source. Fonts: Outfit, Inter, JetBrains Mono (OFL). -->\n' + info.markup.replace('<svg ', '<svg xmlns="http://www.w3.org/2000/svg" ') + '\n');
  }
  console.log((errs.length ? 'WARN ' : 'ok   ') + name + ' t=' + info.t + (errs.length ? ' ' + errs.join(' | ') : ''));
  if (errs.length) failed++;
  await page.close();
}
await browser.close();
process.exit(failed ? 1 : 0);
