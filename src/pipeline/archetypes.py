"""Composition archetypes for the style bake-off.

An archetype is a *structure*: where the hero sits, what is layered, how it moves. It is not a
colour scheme. Every archetype consumes the same beat (headline, message, key figure, supporting
lines, optional data series) and the style system's CSS tokens (--c-*, --font-*), and returns
HTML + CSS + a GSAP timeline body for a self-contained HyperFrames composition.

Each composition is deterministic (seeded PRNG only, `fromTo` tweens, one paused timeline through
Studio.build) so a still at time t is reproducible. Add an archetype by writing a function with the
same signature and registering it in ARCHETYPES; no other code changes.
"""
from __future__ import annotations

import html
import json
import math
import random
from typing import Any, Callable, Dict, List, Tuple

W, H = 1280, 720
Result = Dict[str, str]  # css, html, js


def esc(s: Any) -> str:
    return html.escape(str(s), quote=True)


def fig(beat: Dict[str, Any]) -> Tuple[str, str]:
    k = beat.get("key_figure") or {}
    return str(k.get("value", "")), str(k.get("label", ""))


def support(beat: Dict[str, Any], n: int = 3) -> List[str]:
    s = list(beat.get("supporting", []))[:n]
    return s + [""] * (n - len(s))


def words(text: str) -> List[str]:
    return text.split()


def rng(seed: int) -> random.Random:
    return random.Random(seed)


def ridge(seed: int, base: float, amp: float, n: int = 14, w: int = W) -> str:
    r = rng(seed)
    pts = [(i * w / (n - 1), base + r.uniform(-amp, amp)) for i in range(n)]
    d = f"M0,{H} L{pts[0][0]:.1f},{pts[0][1]:.1f} "
    for i in range(1, n):
        cx = (pts[i - 1][0] + pts[i][0]) / 2
        d += f"Q{pts[i - 1][0]:.1f},{pts[i - 1][1]:.1f} {cx:.1f},{(pts[i - 1][1] + pts[i][1]) / 2:.1f} "
    return d + f"L{w},{pts[-1][1]:.1f} L{w},{H} Z"


# --------------------------------------------------------------------------- 1. collage stack
def collage_stack(b: Dict[str, Any]) -> Result:
    v, lab = fig(b)
    s1, s2, s3 = support(b)
    css = """
.bo-halftone{position:absolute;inset:0;background-image:radial-gradient(circle,var(--c-ink) 1.6px,transparent 2.2px);background-size:14px 14px;opacity:.14;mix-blend-mode:multiply}
.bo-sheet{position:absolute;left:54px;top:70px;width:690px;height:560px;background:var(--c-accent);transform:rotate(-3deg);box-shadow:14px 16px 0 var(--c-shadow,rgba(0,0,0,.22));filter:url(#bo-rough)}
.bo-fig{position:absolute;left:92px;top:210px;width:620px;font-family:var(--font-display);font-size:150px;line-height:.9;color:var(--c-paper);transform:rotate(-3deg);letter-spacing:var(--track-display)}
.bo-lab{position:absolute;left:100px;top:410px;width:560px;font-family:var(--font-text);font-weight:800;font-size:38px;color:var(--c-paper);transform:rotate(-3deg);text-transform:uppercase;letter-spacing:.04em}
.bo-tape{position:absolute;right:44px;top:56px;width:560px;padding:22px 30px;background:var(--c-ink);color:var(--c-paper);font-family:var(--font-display);font-size:58px;line-height:1.02;text-transform:uppercase;transform:rotate(2.2deg);box-shadow:10px 12px 0 var(--c-shadow,rgba(0,0,0,.22))}
.bo-note{position:absolute;width:330px;padding:18px 22px;background:var(--c-paper-2);color:var(--c-ink);font-weight:800;font-size:26px;line-height:1.15;box-shadow:8px 9px 0 var(--c-shadow,rgba(0,0,0,.22))}
.bo-n1{right:70px;top:330px;transform:rotate(-2deg)}.bo-n2{right:110px;top:452px;transform:rotate(3deg);background:var(--c-accent-3)}.bo-n3{right:40px;top:580px;transform:rotate(-1.5deg);background:var(--c-accent-2);color:var(--c-paper)}
.bo-sticker{position:absolute;left:560px;top:548px;width:150px;height:150px;border-radius:50%;background:var(--c-accent-3);display:flex;align-items:center;justify-content:center;font-family:var(--font-display);font-size:34px;text-align:center;color:var(--c-ink);transform:rotate(12deg);box-shadow:6px 7px 0 var(--c-shadow,rgba(0,0,0,.22))}
"""
    body = f"""
<svg width="0" height="0" style="position:absolute"><filter id="bo-rough"><feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed="4"/><feDisplacementMap in="SourceGraphic" scale="14"/></filter></svg>
<div class="bo-halftone"></div>
<div class="bo-sheet" id="sheet"></div><div class="bo-fig" id="fig">{esc(v)}</div><div class="bo-lab" id="lab">{esc(lab)}</div>
<div class="bo-tape" id="tape">{esc(b['headline'])}</div>
<div class="bo-note bo-n1" id="n1">{esc(s1)}</div><div class="bo-note bo-n2" id="n2">{esc(s2)}</div><div class="bo-note bo-n3" id="n3">{esc(s3)}</div>
<div class="bo-sticker" id="stk">{esc(b.get('mood', 'story'))}</div>"""
    js = """
tl.fromTo('#sheet',{x:-900,rotation:-12},{x:0,rotation:-3,duration:.7,ease:'back.out(1.2)',immediateRender:true},0.1);
tl.fromTo(['#fig','#lab'],{x:-900,opacity:0},{x:0,opacity:1,duration:.6,ease:'power3.out',stagger:.08,immediateRender:true},0.35);
tl.fromTo('#tape',{x:900,rotation:9},{x:0,rotation:2.2,duration:.6,ease:'back.out(1.1)',immediateRender:true},0.5);
tl.fromTo(['#n1','#n2','#n3'],{y:260,opacity:0,rotation:6},{y:0,opacity:1,rotation:function(i){return [-2,3,-1.5][i]},duration:.5,ease:'back.out(1.4)',stagger:.16,immediateRender:true},0.9);
tl.fromTo('#stk',{scale:0,rotation:-60},{scale:1,rotation:12,duration:.5,ease:'back.out(2)',immediateRender:true},1.5);
tl.to('#sheet',{y:-8,duration:2.4,ease:'sine.inOut'},1.0);"""
    return {"css": css, "html": body, "js": js}


# --------------------------------------------------------------------------- 2. swiss grid
def swiss_grid(b: Dict[str, Any]) -> Result:
    v, lab = fig(b)
    s1, s2, s3 = support(b)
    fs = int(min(250, 1500 / max(len(v), 1)))  # keep the numeral clear of the right-hand column whatever its length
    css = """
.bo-rule{position:absolute;left:64px;top:64px;width:1152px;height:3px;background:var(--c-ink);transform-origin:left}
.bo-h{position:absolute;left:64px;top:92px;width:440px;font-family:var(--font-display);font-weight:var(--fw-display,700);font-size:36px;line-height:1.08;letter-spacing:-.01em}
.bo-fig{position:absolute;left:56px;top:330px;font-family:var(--font-display);font-weight:800;font-size:__FS__px;line-height:.82;letter-spacing:-.05em}
.bo-lab{position:absolute;left:64px;top:590px;font-size:26px;font-weight:600}
.bo-col{position:absolute;left:900px;top:92px;width:316px;font-size:24px;line-height:1.3}
.bo-col p{margin:0 0 22px}.bo-col .m{font-family:var(--font-mono);font-size:21px;color:var(--c-ink-2);border-top:1.5px solid var(--c-ink);padding-top:10px}
.bo-dot{position:absolute;left:1148px;top:580px;width:68px;height:68px;border-radius:50%;background:var(--c-accent)}
.ln{display:block;overflow:hidden}.ln>span{display:block}
"""
    body = f"""
<div class="bo-rule" id="rule"></div>
<div class="bo-h" id="h">{''.join(f'<span class="ln"><span>{esc(l)}</span></span>' for l in _lines(b['headline'], 2))}</div>
<div class="bo-fig" id="fig">{esc(v)}</div><div class="bo-lab" id="lab">{esc(lab)}</div>
<div class="bo-col" id="col"><p>{esc(b['message'])}</p><p class="m">{esc(s1)}</p><p class="m">{esc(s2)}</p><p class="m">{esc(s3)}</p></div>
<div class="bo-dot" id="dot"></div>"""
    css = css.replace('__FS__', str(fs))
    js = """
tl.fromTo('#rule',{scaleX:0},{scaleX:1,duration:.7,ease:'power3.inOut',immediateRender:true},0);
tl.fromTo('#h .ln>span',{yPercent:110},{yPercent:0,duration:.6,ease:'power3.out',stagger:.09,immediateRender:true},0.3);
tl.fromTo('#fig',{yPercent:30,opacity:0},{yPercent:0,opacity:1,duration:.8,ease:'power3.out',immediateRender:true},0.55);
tl.fromTo('#lab',{opacity:0,x:-16},{opacity:1,x:0,duration:.4,ease:'power2.out',immediateRender:true},1.05);
tl.fromTo('#col > *',{opacity:0,y:18},{opacity:1,y:0,duration:.45,ease:'power2.out',stagger:.12,immediateRender:true},0.9);
tl.fromTo('#dot',{scale:0},{scale:1,duration:.4,ease:'power3.out',immediateRender:true},1.4);"""
    return {"css": css, "html": body, "js": js}


def _lines(text: str, n: int) -> List[str]:
    w = words(text)
    if len(w) <= n:
        return [text]
    k = math.ceil(len(w) / n)
    return [" ".join(w[i:i + k]) for i in range(0, len(w), k)]


# --------------------------------------------------------------------------- 3. cinematic depth
def cinematic_depth(b: Dict[str, Any]) -> Result:
    v, lab = fig(b)
    r = rng(11)
    parts = "".join(f'<circle cx="{r.uniform(0, W):.0f}" cy="{r.uniform(40, 560):.0f}" r="{r.uniform(1, 2.6):.1f}" fill="var(--c-ink)" opacity="{r.uniform(.15, .5):.2f}"/>' for _ in range(46))
    css = """
#stage{position:absolute;inset:0;transform-origin:62% 55%}
.bo-sky{position:absolute;inset:-40px;background:linear-gradient(180deg,#0a1218 0%,#1b2a38 55%,#3a4a52 100%)}
.bo-shaft{position:absolute;left:520px;top:-120px;width:360px;height:900px;background:linear-gradient(180deg,rgba(212,162,76,.38),rgba(212,162,76,0));transform:rotate(14deg);filter:blur(22px);mix-blend-mode:screen}
.layer{position:absolute;left:-60px;top:0;width:1400px;height:720px}
.bo-t{position:absolute;left:84px;bottom:92px;font-family:var(--font-display);font-weight:var(--fw-display,600);font-size:30px;letter-spacing:.34em;text-transform:uppercase;color:var(--c-ink)}
.bo-bar{position:absolute;left:84px;bottom:150px;width:56px;height:3px;background:var(--c-accent)}
.bo-fig{position:absolute;right:92px;top:78px;text-align:right;font-family:var(--font-text);color:var(--c-ink)}
.bo-fig b{display:block;font-family:var(--font-display);font-weight:500;font-size:96px;letter-spacing:.02em;line-height:1}
.bo-fig span{font-size:22px;letter-spacing:.28em;text-transform:uppercase;color:var(--c-ink-2)}
.bo-grain{position:absolute;inset:0;opacity:.16;mix-blend-mode:screen;background-image:radial-gradient(rgba(255,255,255,.7) .6px,transparent .7px);background-size:5px 5px}
.bo-vig{position:absolute;inset:0;background:radial-gradient(ellipse at 55% 50%,transparent 45%,rgba(0,0,0,.65) 100%)}
"""
    body = f"""
<div id="stage"><div class="bo-sky"></div><div class="bo-shaft" id="shaft"></div>
<svg class="layer" id="L1" viewBox="0 0 {W} {H}"><path d="{ridge(3, 380, 40)}" fill="#26343f"/></svg>
<svg class="layer" id="L2" viewBox="0 0 {W} {H}"><path d="{ridge(5, 450, 50)}" fill="#18242d"/></svg>
<svg class="layer" id="L3" viewBox="0 0 {W} {H}"><path d="{ridge(8, 540, 46)}" fill="#0d151b"/></svg>
<svg class="layer" id="P" viewBox="0 0 {W} {H}">{parts}</svg></div>
<div class="bo-vig"></div><div class="bo-grain"></div>
<div class="bo-bar" id="bar"></div><div class="bo-t" id="t">{esc(b['headline'])}</div>
<div class="bo-fig" id="fig"><b>{esc(v)}</b><span>{esc(lab)}</span></div>"""
    js = """
tl.fromTo('#stage',{scale:1},{scale:1.07,duration:4,ease:'sine.inOut',immediateRender:true},0);
tl.fromTo('#L1',{x:0},{x:-18,duration:4,ease:'none',immediateRender:true},0);
tl.fromTo('#L2',{x:0},{x:-42,duration:4,ease:'none',immediateRender:true},0);
tl.fromTo('#L3',{x:0},{x:-86,duration:4,ease:'none',immediateRender:true},0);
tl.fromTo('#P',{y:0},{y:-30,duration:4,ease:'none',immediateRender:true},0);
tl.fromTo('#shaft',{opacity:0},{opacity:1,duration:1.6,ease:'sine.inOut',immediateRender:true},0.3);
tl.fromTo('#bar',{scaleX:0,transformOrigin:'left'},{scaleX:1,duration:.8,ease:'power2.out',immediateRender:true},1.0);
tl.fromTo('#t',{opacity:0,y:14},{opacity:1,y:0,duration:1.1,ease:'power2.out',immediateRender:true},1.2);
tl.fromTo('#fig',{opacity:0},{opacity:1,duration:1.2,ease:'power2.out',immediateRender:true},1.8);"""
    return {"css": css, "html": body, "js": js}


# --------------------------------------------------------------------------- 4. chart hero
def chart_hero(b: Dict[str, Any]) -> Result:
    v, lab = fig(b)
    illustrative = not b.get("series")  # no data supplied: draw a schematic ramp and SAY so on the frame
    s = list(b.get("series") or [0, 0, 1, 3, 9, 22, 48, 74, 92, 100])
    lo, hi = min(s), max(s)
    x0, y0, cw, ch = 96, 250, 1088, 360
    pts = [(x0 + i * cw / (len(s) - 1), y0 + ch - (val - lo) / ((hi - lo) or 1) * ch) for i, val in enumerate(s)]
    path = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = path + f" L{pts[-1][0]:.1f},{y0 + ch} L{pts[0][0]:.1f},{y0 + ch} Z"
    grid = "".join(f'<line x1="{x0}" x2="{x0 + cw}" y1="{y0 + ch * i / 4:.0f}" y2="{y0 + ch * i / 4:.0f}" stroke="var(--c-rule)" stroke-width="1.5"/>' for i in range(5))
    lx, ly = pts[-1]
    css = """
.bo-h{position:absolute;left:96px;top:54px;width:900px;font-family:var(--font-display);font-weight:700;font-size:58px;line-height:1.04;letter-spacing:-.01em}
.bo-sub{position:absolute;left:96px;top:178px;width:740px;font-size:25px;color:var(--c-ink-2)}
svg.ch{position:absolute;left:0;top:0;width:1280px;height:720px}
.bo-src{position:absolute;left:96px;bottom:34px;font-family:var(--font-mono);font-size:19px;color:var(--c-ink-2)}
.bo-call{position:absolute;padding:12px 20px;background:var(--c-ink);color:var(--c-paper);font-family:var(--font-display);font-size:50px;line-height:1;white-space:nowrap}
.bo-call small{display:block;font-family:var(--font-text);font-size:21px;font-weight:600;margin-top:6px;opacity:.9}
"""
    body = f"""
<div class="bo-h" id="h">{esc(b['headline'])}</div><div class="bo-sub" id="sub">{esc(b['message'])}</div>
<svg class="ch" viewBox="0 0 {W} {H}">{grid}
<path id="area" d="{area}" fill="var(--c-accent)" opacity=".12"/>
<path id="line" d="{path}" fill="none" stroke="var(--c-ink)" stroke-width="5" stroke-linejoin="round" stroke-linecap="round"/>
<circle id="mk" cx="{lx:.1f}" cy="{ly:.1f}" r="13" fill="var(--c-accent)" stroke="var(--c-paper)" stroke-width="4"/></svg>
<div class="bo-call" id="call" style="right:96px;top:{max(40, min(ly - 150, 150)):.0f}px">{esc(v)}<small>{esc(lab)}</small></div>
<div class="bo-src" id="src">{esc('Illustrative shape: no data is plotted' if illustrative else (support(b)[0] or 'Source: see research dossier'))}</div>"""
    js = f"""
var L=document.getElementById('line'),len=L.getTotalLength();
tl.fromTo('#h',{{opacity:0,y:20}},{{opacity:1,y:0,duration:.5,ease:'power3.out',immediateRender:true}},0);
tl.fromTo('#sub',{{opacity:0}},{{opacity:1,duration:.5,ease:'power2.out',immediateRender:true}},.25);
tl.fromTo('#line',{{strokeDasharray:len,strokeDashoffset:len}},{{strokeDashoffset:0,duration:1.8,ease:'none',immediateRender:true}},.5);
tl.fromTo('#area',{{opacity:0}},{{opacity:.12,duration:.8,ease:'none',immediateRender:true}},1.5);
tl.fromTo('#mk',{{scale:0,transformOrigin:'center'}},{{scale:1,duration:.35,ease:'back.out(2)',immediateRender:true}},2.3);
tl.fromTo('#call',{{opacity:0,y:14}},{{opacity:1,y:0,duration:.4,ease:'power3.out',immediateRender:true}},2.45);
tl.fromTo('#src',{{opacity:0}},{{opacity:1,duration:.4,ease:'none',immediateRender:true}},1.0);"""
    return {"css": css, "html": body, "js": js}


# --------------------------------------------------------------------------- 5. geometric field
def geometric_field(b: Dict[str, Any]) -> Result:
    v, lab = fig(b)
    w0 = next((w for w in words(b["headline"]) if len(w.strip(".,:;!?")) >= 4), (words(b["headline"]) or [""])[0]).strip(".,:;!?")
    s1, s2, _ = support(b)
    css = """
.bo-c{position:absolute;left:640px;top:-80px;width:760px;height:760px;border-radius:50%;background:var(--c-accent)}
.bo-sq{position:absolute;left:380px;top:300px;width:300px;height:300px;background:var(--c-accent-2);transform:rotate(12deg)}
.bo-tri{position:absolute;left:380px;top:50px;width:260px;height:230px;background:var(--c-accent-3);clip-path:polygon(50% 0,0 100%,100% 100%)}
.bo-bar1{position:absolute;left:0;top:560px;width:1280px;height:26px;background:var(--c-ink)}
.bo-word{position:absolute;left:-30px;top:340px;font-family:var(--font-display);font-size:330px;line-height:.82;letter-spacing:-.03em;color:var(--c-ink);mix-blend-mode:multiply;white-space:nowrap}
.bo-fig{position:absolute;left:830px;top:190px;width:380px;text-align:center;font-family:var(--font-display);font-size:120px;line-height:.95;color:var(--c-paper)}
.bo-fig small{display:block;font-family:var(--font-text);font-weight:700;font-size:28px;margin-top:10px}
.bo-m{position:absolute;left:96px;top:100px;width:240px;font-family:var(--font-mono);font-size:20px;line-height:1.4}
.bo-m2{position:absolute;right:60px;bottom:70px;font-family:var(--font-mono);font-size:22px;text-align:right;width:420px}
"""
    body = f"""
<div class="bo-c" id="c"></div><div class="bo-sq" id="sq"></div><div class="bo-tri" id="tri"></div><div class="bo-bar1" id="bar"></div>
<div class="bo-word" id="word">{esc(w0.upper())}</div>
<div class="bo-fig" id="fig">{esc(v)}<small>{esc(lab)}</small></div>
<div class="bo-m" id="m1">{esc(s1)}<br><br>{esc(s2)}</div>"""
    js = """
tl.fromTo('#c',{scale:0,transformOrigin:'center'},{scale:1,duration:.7,ease:'expo.out',immediateRender:true},0);
tl.fromTo('#sq',{rotation:-80,scale:0},{rotation:12,scale:1,duration:.6,ease:'back.out(1.4)',immediateRender:true},.25);
tl.fromTo('#tri',{y:-300,rotation:40},{y:0,rotation:0,duration:.55,ease:'power4.out',immediateRender:true},.45);
tl.fromTo('#bar',{scaleX:0,transformOrigin:'left'},{scaleX:1,duration:.5,ease:'power4.inOut',immediateRender:true},.65);
tl.fromTo('#word',{x:-700},{x:0,duration:.7,ease:'power4.out',immediateRender:true},.8);
tl.fromTo('#fig',{scale:.6,opacity:0},{scale:1,opacity:1,duration:.4,ease:'back.out(1.6)',immediateRender:true},1.15);
tl.fromTo('#m1',{opacity:0},{opacity:1,duration:.3,immediateRender:true},1.5);
tl.to('#c',{rotation:8,duration:2.2,ease:'sine.inOut'},1.2);"""
    return {"css": css, "html": body, "js": js}


# --------------------------------------------------------------------------- 6. diagram stage
def diagram_stage(b: Dict[str, Any]) -> Result:
    v, lab = fig(b)
    labs = support(b)
    nodes = [(250, 420, "var(--c-accent-2)"), (640, 330, "var(--c-accent)"), (1020, 450, "var(--c-accent-3)")]
    conn = "".join(f'<path class="cn" d="M{nodes[i][0]},{nodes[i][1]} Q{(nodes[i][0] + nodes[i + 1][0]) / 2},{min(nodes[i][1], nodes[i + 1][1]) - 110} {nodes[i + 1][0]},{nodes[i + 1][1]}" fill="none" stroke="var(--c-ink)" stroke-width="5" stroke-linecap="round"/>' for i in range(2))
    circles = "".join(f'<g class="nd" id="nd{i}"><circle cx="{x}" cy="{y}" r="{92 if i == 1 else 74}" fill="{c}" stroke="var(--c-ink)" stroke-width="5"/></g>' for i, (x, y, c) in enumerate(nodes))
    lbl = "".join(f'<div class="bo-l" id="lb{i}" style="left:{x - 150}px;top:{y + (112 if i == 1 else 96)}px">{esc(labs[i])}</div>' for i, (x, y, _) in enumerate(nodes))
    css = """
.bo-h{position:absolute;left:0;width:1280px;top:44px;text-align:center;font-family:var(--font-display);font-size:64px;line-height:1.04}
svg.dg{position:absolute;left:0;top:0;width:1280px;height:720px}
.bo-l{position:absolute;width:300px;text-align:center;font-size:27px;font-weight:700;line-height:1.15}
.bo-fig{position:absolute;left:490px;top:300px;width:300px;text-align:center;font-family:var(--font-display);font-size:64px;color:var(--c-paper);line-height:1}
.bo-fig small{display:block;font-family:var(--font-text);font-size:19px;font-weight:700;margin-top:4px}
.bo-msg{position:absolute;left:0;width:1280px;bottom:42px;text-align:center;font-size:27px;color:var(--c-ink-2)}
"""
    body = f"""
<div class="bo-h" id="h">{esc(b['headline'])}</div>
<svg class="dg" viewBox="0 0 {W} {H}">{conn}{circles}<circle id="pk" r="13" fill="var(--c-ink)"/></svg>
<div class="bo-fig" id="fig">{esc(v)}<small>{esc(lab)}</small></div>{lbl}
<div class="bo-msg" id="msg">{esc(b['message'])}</div>"""
    js = f"""
var P={json.dumps([[x, y] for x, y, _ in nodes])};
tl.fromTo('#h',{{opacity:0,y:-20}},{{opacity:1,y:0,duration:.5,ease:'power3.out',immediateRender:true}},0);
document.querySelectorAll('.cn').forEach(function(p,i){{var l=p.getTotalLength();tl.fromTo(p,{{strokeDasharray:l,strokeDashoffset:l}},{{strokeDashoffset:0,duration:.8,ease:'power2.inOut',immediateRender:true}},.5+i*.55);}});
tl.fromTo('.nd',{{scale:0,transformOrigin:'center'}},{{scale:1,duration:.45,ease:'back.out(1.6)',stagger:.35,immediateRender:true,transformOrigin:'center center'}},.3);
tl.fromTo(['#lb0','#lb1','#lb2'],{{opacity:0,y:10}},{{opacity:1,y:0,duration:.4,stagger:.35,immediateRender:true}},.7);
tl.fromTo('#fig',{{opacity:0}},{{opacity:1,duration:.4,immediateRender:true}},1.0);
tl.fromTo('#pk',{{attr:{{cx:P[0][0],cy:P[0][1]}},opacity:0}},{{attr:{{cx:P[1][0],cy:P[1][1]-60}},opacity:1,duration:.9,ease:'power2.inOut',immediateRender:true}},1.5);
tl.to('#pk',{{attr:{{cx:P[2][0],cy:P[2][1]}},duration:.9,ease:'power2.inOut'}},2.4);
tl.fromTo('#msg',{{opacity:0}},{{opacity:1,duration:.5,immediateRender:true}},1.8);"""
    return {"css": css, "html": body, "js": js}


# --------------------------------------------------------------------------- 7. spatial lab
def spatial_lab(b: Dict[str, Any]) -> Result:
    v, lab = fig(b)
    labs = support(b)
    cx, cy, a, c = 560, 410, 230, 0.5
    def rhomb(dy: int, i: int) -> str:
        top = f"{cx},{cy - a * c + dy} {cx + a},{cy + dy} {cx},{cy + a * c + dy} {cx - a},{cy + dy}"
        left = f"{cx - a},{cy + dy} {cx},{cy + a * c + dy} {cx},{cy + a * c + dy + 26} {cx - a},{cy + dy + 26}"
        right = f"{cx + a},{cy + dy} {cx},{cy + a * c + dy} {cx},{cy + a * c + dy + 26} {cx + a},{cy + dy + 26}"
        fills = ["var(--c-accent)", "var(--c-accent-3)", "var(--c-accent-2)", "var(--c-ink-2)"]
        return (f'<g class="sl" id="sl{i}"><polygon points="{left}" fill="var(--c-paper-2)" stroke="var(--c-ink)" stroke-width="2"/>'
                f'<polygon points="{right}" fill="var(--c-rule)" stroke="var(--c-ink)" stroke-width="2"/>'
                f'<polygon points="{top}" fill="{fills[i % 4]}" fill-opacity=".85" stroke="var(--c-ink)" stroke-width="2.5"/></g>')
    slabs = "".join(rhomb(-i * 92 + 120, i) for i in range(4))
    leaders = "".join(f'<line class="ld" x1="{cx + a - 20}" y1="{cy - i * 92 + 124}" x2="900" y2="{cy - i * 92 + 124}" stroke="var(--c-accent)" stroke-width="2"/>' for i in range(3))
    tags = "".join(f'<div class="bo-tg" id="tg{i}" style="top:{cy - i * 92 + 106}px">{esc(labs[i].upper())}</div>' for i in range(3))
    grid = "".join(f'<line x1="0" x2="1280" y1="{540 + k * 36}" y2="{540 + k * 36}" stroke="var(--c-rule)" stroke-width="1"/>' for k in range(6))
    css = """
.bo-bg{position:absolute;inset:0;background:radial-gradient(ellipse at 45% 60%,var(--c-paper-2) 0%,var(--c-paper) 70%)}
svg.sp{position:absolute;left:0;top:0;width:1280px;height:720px}
.bo-h{position:absolute;left:64px;top:46px;font-family:var(--font-mono);font-size:21px;letter-spacing:.26em;color:var(--c-accent);text-transform:uppercase;max-width:700px}
.bo-fig{position:absolute;left:64px;top:92px;font-family:var(--font-display);font-weight:600;font-size:110px;line-height:1}
.bo-fig small{display:block;font-family:var(--font-mono);font-size:21px;letter-spacing:.2em;color:var(--c-ink-2);text-transform:uppercase;margin-top:4px}
.bo-tg{position:absolute;left:910px;font-family:var(--font-mono);font-size:21px;letter-spacing:.14em;color:var(--c-ink);width:330px}
"""
    body = f"""
<div class="bo-bg"></div>
<svg class="sp" viewBox="0 0 {W} {H}">{grid}{slabs}{leaders}</svg>
<div class="bo-h" id="h">{esc(b['headline'])}</div><div class="bo-fig" id="fig">{esc(v)}<small>{esc(lab)}</small></div>{tags}"""
    js = """
tl.fromTo('#h',{opacity:0},{opacity:1,duration:.5,immediateRender:true},0);
tl.fromTo('#fig',{opacity:0,y:20},{opacity:1,y:0,duration:.6,ease:'power3.out',immediateRender:true},.2);
[0,1,2,3].forEach(function(i){tl.fromTo('#sl'+i,{y:-60*i,opacity:0},{y:0,opacity:1,duration:.7,ease:'power3.out',immediateRender:true},.4+i*.2);});
tl.fromTo('.ld',{attr:{x2:900-0},opacity:0},{opacity:1,duration:.4,stagger:.2,immediateRender:true},1.6);
tl.fromTo(['#tg0','#tg1','#tg2'],{opacity:0,x:-14},{opacity:1,x:0,duration:.4,stagger:.2,immediateRender:true},1.8);
tl.to('#sl3',{y:-18,duration:2,ease:'sine.inOut'},1.2);"""
    return {"css": css, "html": body, "js": js}


# --------------------------------------------------------------------------- 8. archive document
def archive_document(b: Dict[str, Any]) -> Result:
    v, lab = fig(b)
    s1, s2, s3 = support(b)
    css = """
.bo-tbl{position:absolute;inset:0;background:var(--c-paper-2)}
#stage{position:absolute;inset:0;transform-origin:40% 50%}
.bo-sheet{position:absolute;left:96px;top:56px;width:640px;height:610px;background:var(--c-paper);transform:rotate(-1.6deg);box-shadow:0 14px 38px rgba(40,30,15,.35);padding:42px 52px}
.bo-sheet h1{font-family:var(--font-display);font-size:52px;line-height:1.05;font-weight:500;margin:0 0 20px;border-bottom:2px solid var(--c-ink);padding-bottom:16px}
.bo-sheet p{font-family:var(--font-mono);font-size:22px;line-height:1.45;margin:0 0 14px}
.bo-sheet .f{font-family:var(--font-mono);font-size:64px;color:var(--c-accent);margin:16px 0 0;font-weight:600}
.bo-stamp{position:absolute;left:520px;top:548px;padding:6px 16px;border:5px solid var(--c-accent);color:var(--c-accent);font-family:var(--font-mono);font-size:30px;font-weight:700;transform:rotate(-12deg);letter-spacing:.12em;text-transform:uppercase}
.bo-photo{position:absolute;left:800px;top:120px;width:380px;height:300px;background:linear-gradient(135deg,#9d8f72,#52483a);border:14px solid var(--c-paper);box-shadow:0 10px 26px rgba(40,30,15,.35);transform:rotate(2.4deg)}
.bo-photo i{position:absolute;inset:0;background-image:radial-gradient(circle,rgba(30,20,10,.55) 1.6px,transparent 2.2px);background-size:9px 9px}
.bo-cap{position:absolute;left:800px;top:440px;width:380px;font-family:var(--font-mono);font-size:21px;line-height:1.35;transform:rotate(2.4deg)}
.bo-grain{position:absolute;inset:0;opacity:.18;mix-blend-mode:multiply;background-image:radial-gradient(rgba(60,40,20,.8) .7px,transparent .8px);background-size:4px 4px}
"""
    body = f"""
<div class="bo-tbl"></div><div id="stage">
<div class="bo-sheet" id="sheet"><h1>{esc(b['headline'])}</h1><p>{esc(b['message'])}</p><p>{esc(s1)}</p><p>{esc(s2)}</p><div class="f">{esc(v)}</div><p>{esc(lab)}</p></div>
<div class="bo-stamp" id="stamp">{esc(str(b.get('mood') or 'Recorded').upper()[:14])}</div>
<div class="bo-photo" id="photo"><i></i></div><div class="bo-cap" id="cap">{esc(s3)}</div></div><div class="bo-grain"></div>"""
    js = """
tl.fromTo('#stage',{scale:1},{scale:1.05,duration:4,ease:'sine.inOut',immediateRender:true},0);
tl.fromTo('#sheet',{y:60,opacity:0},{y:0,opacity:1,duration:1.1,ease:'power2.out',immediateRender:true},0);
tl.fromTo('#photo',{x:80,opacity:0},{x:0,opacity:1,duration:1.1,ease:'power2.out',immediateRender:true},.5);
tl.fromTo('#cap',{opacity:0},{opacity:1,duration:.8,immediateRender:true},1.2);
tl.fromTo('#stamp',{scale:2.4,opacity:0,rotation:-24},{scale:1,opacity:1,rotation:-12,duration:.28,ease:'power4.in',immediateRender:true},1.9);"""
    return {"css": css, "html": body, "js": js}


# --------------------------------------------------------------------------- 9. mixed collision
def mixed_collision(b: Dict[str, Any]) -> Result:
    v, lab = fig(b)
    s1, s2, _ = support(b)
    head = esc(b["headline"].upper())
    slices = "".join(f'<div class="sl" id="s{i}" style="clip-path:inset({i * 33.4}% 0 {max(0, 66.6 - i * 33.4)}% 0)"><span>{head}</span></div>' for i in range(3))
    css = """
.bo-head{position:absolute;left:30px;top:70px;width:1220px;height:430px}
.sl{position:absolute;inset:0}
.sl span{display:block;font-family:var(--font-display);font-weight:700;font-size:168px;line-height:.9;letter-spacing:.005em;text-transform:uppercase;color:var(--c-ink);text-shadow:7px 5px 0 var(--c-accent)}
.bo-blk{position:absolute;left:700px;top:430px;width:520px;height:210px;background:var(--c-accent)}
.bo-tp{position:absolute;left:760px;top:455px;padding:10px 22px;background:var(--c-accent-3);color:var(--c-ink);font-family:var(--font-display);font-size:92px;line-height:1;transform:rotate(-2deg)}
.bo-tp small{display:block;font-family:var(--font-mono);font-size:21px;margin-top:4px}
.bo-n{position:absolute;left:60px;top:560px;width:560px;font-family:var(--font-mono);font-size:23px;line-height:1.4}
.bo-ph{position:absolute;left:44px;top:480px;width:150px;height:62px;background:var(--c-accent-2)}
.bo-grain{position:absolute;inset:0;opacity:.2;mix-blend-mode:multiply;background-image:radial-gradient(rgba(0,0,0,.8) .8px,transparent .9px);background-size:4px 4px}
"""
    body = f"""
<div class="bo-head" id="head">{slices}</div><div class="bo-ph" id="ph"></div><div class="bo-blk" id="blk"></div>
<div class="bo-tp" id="tp">{esc(v)}<small>{esc(lab)}</small></div><div class="bo-n" id="n">{esc(s1)}<br>{esc(s2)}</div><div class="bo-grain"></div>"""
    js = """
tl.fromTo('#s0',{x:-900},{x:0,duration:.4,ease:'steps(5)',immediateRender:true},0);
tl.fromTo('#s1',{x:900},{x:0,duration:.4,ease:'steps(5)',immediateRender:true},.12);
tl.fromTo('#s2',{x:-900},{x:0,duration:.4,ease:'steps(5)',immediateRender:true},.24);
tl.fromTo('#blk',{scaleX:0,transformOrigin:'right'},{scaleX:1,duration:.3,ease:'steps(4)',immediateRender:true},.7);
tl.fromTo('#tp',{x:300,opacity:0},{x:0,opacity:1,duration:.3,ease:'steps(4)',immediateRender:true},.9);
tl.fromTo('#ph',{y:60,opacity:0},{y:0,opacity:1,duration:.2,ease:'steps(3)',immediateRender:true},1.1);
tl.fromTo('#n',{opacity:0},{opacity:1,duration:.2,ease:'steps(3)',immediateRender:true},1.3);
tl.to('#s1',{x:14,duration:.1,ease:'steps(2)'},2.0);tl.to('#s1',{x:0,duration:.1,ease:'steps(2)'},2.2);"""
    return {"css": css, "html": body, "js": js}


ARCHETYPES: Dict[str, Callable[[Dict[str, Any]], Result]] = {
    "collage-stack": collage_stack, "swiss-grid": swiss_grid, "cinematic-depth": cinematic_depth,
    "chart-hero": chart_hero, "geometric-field": geometric_field, "diagram-stage": diagram_stage,
    "spatial-lab": spatial_lab, "archive-document": archive_document, "mixed-collision": mixed_collision,
}


def font_stacks(style: str) -> Dict[str, str]:
    """Literal font stacks from the style sheet. HyperFrames only injects a bundled family when a
    `font-family:` declaration naming it appears in the page itself, so var(--font-*) alone leaves the
    page on a system fallback (verified: Archivo Black and Nunito only loaded after this substitution)."""
    import re
    from pathlib import Path
    css = (Path(__file__).resolve().parents[2] / "src" / "studio" / "styles" / f"{style}.css").read_text(encoding="utf-8")
    out = {}
    for k in ("display", "text", "mono"):
        m = re.search(rf"--font-{k}:\s*([^;]+);", css)
        out[k] = m.group(1).strip() if m else "sans-serif"
    return out


def page(archetype: str, beat: Dict[str, Any], style: str, duration: float = 4.0, size: Tuple[int, int] = (W, H)) -> str:
    """Complete composition HTML for one candidate. Needs _studio/studio-core.js, studio-base.css and styles/<style>.css beside it."""
    a = ARCHETYPES[archetype](beat)
    stacks = font_stacks(style)
    for k, v in stacks.items():
        a["css"] = a["css"].replace(f"var(--font-{k})", v)
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>bake-off {esc(archetype)}</title>
<link rel="stylesheet" href="_studio/studio-base.css"><link rel="stylesheet" href="_studio/styles/{esc(style)}.css">
<style id="studio-format">:root{{--w:{size[0]}px;--h:{size[1]}px;--u:{min(size) / 100}px;--safe-top:43px;--safe-right:64px;--safe-bottom:58px;--safe-left:64px;}}
html,body{{margin:0;background:var(--c-paper)}}
#root{{position:relative;width:{size[0]}px;height:{size[1]}px;overflow:hidden;background:var(--c-paper);color:var(--c-ink);font-family:{stacks['text']}}}
#root *{{box-sizing:border-box}}
{a['css']}</style>
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script></head>
<body><div id="root" data-composition-id="root" data-format="landscape" data-width="{size[0]}" data-height="{size[1]}" data-fps="30" data-duration="{duration}">
{a['html']}
</div>
<script src="_studio/studio-core.js"></script>
<script>Studio.build(function(tl,f,S){{
{a['js']}
}});</script></body></html>
"""
