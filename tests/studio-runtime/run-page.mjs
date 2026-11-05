#!/usr/bin/env node
// run-page.mjs: load a runtime self-test page in headless Chrome and print its results as JSON.
//
//   node tests/studio-runtime/run-page.mjs <url> [--width 720 --height 1280]
//
// The fallback for tests/test-studio-runtime.py on hosts without Python Playwright: it uses puppeteer-core inside
// the global `hyperframes` install and the Chrome it caches, as scripts/tween-probe.mjs does.
// Stdout: JSON {gsap, results, errors}. Exit 2 when the browser cannot be started (the test then skips).
import { createRequire } from 'node:module';
import { execSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const args = process.argv.slice(2);
const opt = (n, d) => { const i = args.indexOf('--' + n); return i >= 0 ? args[i + 1] : d; };
const url = args[0];

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

let browser;
try {
  const puppeteer = findPuppeteer();
  browser = await puppeteer.launch({ executablePath: findChrome(), headless: true, args: ['--no-sandbox'] });
} catch (e) {
  console.error('cannot start Chrome: ' + e.message);
  process.exit(2);
}
const errors = [];
try {
  const page = await browser.newPage();
  await page.setViewport({ width: +opt('width', 720), height: +opt('height', 1280) });
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
  page.on('console', (m) => { if (m.type() === 'error') errors.push('console.error: ' + m.text()); });
  await page.goto(url, { waitUntil: 'load', timeout: 30000 });
  const gsap = await page.evaluate(() => !!window.gsap);
  let results = null;
  if (gsap) {
    await page.waitForFunction(() => window.__studioTestResults !== undefined, { timeout: 20000 });
    results = await page.evaluate(() => window.__studioTestResults);
  }
  process.stdout.write(JSON.stringify({ gsap, results, errors }));
} finally {
  await browser.close();
}
