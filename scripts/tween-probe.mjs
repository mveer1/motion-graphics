#!/usr/bin/env node
// tween-probe.mjs: dump every GSAP tween in a HyperFrames composition as JSON, without rendering a frame.
//
//   node scripts/tween-probe.mjs <index.html> [--width 720 --height 1280]
//
// Loads the page the same way dom-probe.mjs does (puppeteer-core inside the global `hyperframes` install and the
// Chrome it caches), reads window.__timelines[<id>] (the paused GSAP timeline), walks nested timelines and
// stagger groups, and reports for each tween: start and duration in film seconds, ease, kind (to, from, fromTo,
// set), the animated properties and their from/to values, a stable id for the target element, and whether the
// target covers the frame (a scene container, i.e. a transition rather than an element entrance).
// Stdout: JSON {file, duration, size, tweens:[...]}. Exit 2 when the browser or page cannot be started.
// Analysis lives in src/pipeline/tweens.py. Run it through `session-guard.py run render -- node ...` (it is a browser).
import { createRequire } from 'node:module';
import { execSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const args = process.argv.slice(2);
const opt = (n, d) => { const i = args.indexOf('--' + n); return i >= 0 ? args[i + 1] : d; };
const file = args.find((a, i) => !a.startsWith('--') && (i === 0 || !args[i - 1].startsWith('--')));
if (!file || !fs.existsSync(file)) { console.error('usage: tween-probe.mjs <index.html> [--width W --height H]'); process.exit(2); }

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

// Runs inside the page. Everything it returns must be JSON-safe.
const collect = () => {
  const RESERVED = new Set(['duration', 'ease', 'delay', 'stagger', 'immediateRender', 'overwrite', 'startAt', 'runBackwards', 'yoyo',
    'yoyoEase', 'repeat', 'repeatDelay', 'repeatRefresh', 'paused', 'data', 'id', 'lazy', 'keyframes', 'onComplete', 'onStart',
    'onUpdate', 'onRepeat', 'onReverseComplete', 'callbackScope', 'inherit', 'defaults', 'scrollTrigger', 'parent', 'reversed',
    'onCompleteParams', 'onStartParams', 'onUpdateParams', 'easeParams', 'motionPath', 'transformOrigin', 'force3D', 'svgOrigin']);
  const tl = Object.values(window.__timelines)[0];
  const root = document.getElementById('root') || document.querySelector('[data-composition-id]');
  const rootArea = (root.offsetWidth || 1) * (root.offsetHeight || 1);
  const ids = new WeakMap();
  let nextId = 0;
  const val = (x) => (typeof x === 'number' || typeof x === 'string' || typeof x === 'boolean') ? x : (x === null || x === undefined ? null : 'fn');
  const pick = (o) => { const out = {}; if (!o) return out; for (const k of Object.keys(o)) if (!RESERVED.has(k)) out[k] = val(o[k]); return out; };
  const label = (el) => {
    if (el.id) return '#' + el.id;
    const cls = typeof el.className === 'string' && el.className.trim() ? '.' + el.className.trim().split(/\s+/).slice(0, 2).join('.') : '';
    return el.tagName.toLowerCase() + cls;
  };
  const out = [];
  const describe = (tw, start, scale) => {
    const v = tw.vars || {};
    const dur = tw.duration() * scale;
    const target = (tw.targets() || [])[0];
    const isEl = !!target && target.nodeType === 1;
    if (isEl && !ids.has(target)) ids.set(target, ++nextId);
    const kind = v.runBackwards ? 'from' : v.startAt ? 'fromTo' : dur === 0 ? 'set' : 'to';
    const rep = typeof v.repeat === 'number' ? v.repeat : 0;
    return {
      t0: +start.toFixed(3), dur: +dur.toFixed(3), kind,
      ease: typeof v.ease === 'string' ? v.ease : v.ease ? 'custom' : null,
      props: pick(v), from: pick(v.startAt),
      target: isEl ? ids.get(target) : 0, label: isEl ? label(target) : 'object',
      cover: isEl ? ((target.offsetWidth || 0) * (target.offsetHeight || 0)) >= 0.8 * rootArea : false,
      stagger: typeof v.stagger === 'number' ? v.stagger : v.stagger ? (v.stagger.each ?? v.stagger.amount ?? 'obj') : null,
      repeat: rep, yoyo: !!v.yoyo,
    };
  };
  const walk = (timeline, offset, scale) => {
    for (const ch of timeline.getChildren(false, true, true)) {
      const start = offset + ch.startTime() * scale;
      if (typeof ch.getChildren === 'function') walk(ch, start, scale / (ch.timeScale() || 1));
      else out.push(describe(ch, start, scale));
    }
  };
  walk(tl, 0, 1);
  return { duration: tl.duration(), size: [root.offsetWidth, root.offsetHeight], tweens: out };
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
  const result = await page.evaluate(collect);
  console.log(JSON.stringify({ file, errors, ...result }));
} catch (e) {
  console.error('tween-probe failed: ' + (e && e.message || e));
  process.exitCode = 2;
} finally {
  if (browser) await browser.close();
}
