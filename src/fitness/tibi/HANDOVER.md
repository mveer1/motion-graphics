# HANDOVER: Tibi, "Cobalt Sculpt" character system for Sinew

You are picking up a finished character-design deliverable and continuing it. This file is your brief. Read it fully before touching code. It describes only the current version and the options inside it.

- Owner: Mahavir (mveer.rc@gmail.com, IST)
- Brand: **Sinew**, a fitness-education brand. Tagline: *"See what your body is doing."*
- Product: narrated 2D motion-graphics explainers. The mascot **Tibi** (a male and a female version) shows what muscles do in an exercise.
- Style name: **Cobalt Sculpt**. Flat 2D vector, no outlines, light-plane / shade-plane shading, built so every body part is a separate SVG group that can be rigged and animated later.

---------------------------------------------------------------------------------------------------

## 0. Quick start (do this first)

Bundle root (original cloud workspace path): `/home/claude/out/tibi_handover/`
If you received the zip (`/home/claude/out/tibi_handover.zip`), unzip it anywhere; every script finds its neighbours relative to its own location, so the absolute path does not matter. Below, `<BUNDLE>` means that root.

```bash
cd <BUNDLE>/src
python3 page6.py                       # rebuild the review page -> <BUNDLE>/site/tibi_cobalt_sculpt_v6.html   (stdlib only)
python3 verify3.py                     # static + browser checks (needs: pip install playwright, and a Chrome/Chromium, see section 11)
python3 export_assets.py               # regenerate every standalone SVG + transparent PNG into <BUNDLE>/svg and <BUNDLE>/png
```

Expected baseline after a clean rebuild (use it as your regression check):

- `page6.py` prints `written 1469 KB {'m': 7.66, 'f': 7.55}`
- `verify3.py` prints `ids 3673 dup [] missing [] external []` and, for widths 390 / 820 / 1500, `scrollWidth` equal to the width with `errs []`
- the rebuilt HTML is byte-identical to `<BUNDLE>/site/tibi_cobalt_sculpt_v6.html`

Open `<BUNDLE>/site/tibi_cobalt_sculpt_v6.html` in a browser to see every design, option and control described below. It is one self-contained file (inline SVG, no images, no external libraries).

---------------------------------------------------------------------------------------------------

## 1. What the design is (latest version, with its options)

### 1.1 Characters

| | Male Tibi | Female Tibi |
|---|---|---|
| Height | 7.66 heads | 7.55 heads |
| Shoulder width (rig units, head = 100) | 198 | 168 |
| Waist width | 122 | 94 |
| Hip width (shorts) | 150 | 151 |
| Shoulder : waist | 1.62 : 1 | 1.79 : 1 |
| Waist : hip | 0.81 | 0.62 |
| Leg length | 100 % | 96.5 % (`LS['f'] = 0.965`) |
| Clothing | short charcoal shorts with slim marigold waistband, white trainers, **no shirt** | same shorts and trainers plus a **sports top** |
| Hair | none (smooth hood) | ponytail with marigold tie |
| Signature | marigold flame "spark" on top of the head (both) | same |

Her hips are deliberately wide relative to her waist (shorts 151 wide against a 94 waist, waist : hip 0.62). Her muscle planes are about 10 % smaller, arms and calves about 15 % slimmer; abs, serratus and quads remain visible.

### 1.2 Options that exist in this version (defaults first)

| Choice | Default | Secondary option(s) | Where it is controlled |
|---|---|---|---|
| Face | **Faceless** (smooth hood with a lighter face plane) | **Minimal (A)**: two navy oval eyes with a catch-light and a small smile (hers adds a lash flick). **Ember visor (C)**: dark visor plane, marigold glowing eyes, tiny smile | `face=None | 'A' | 'C'` in `build2.figure()` / `head_only()` |
| Female top | **Sports top** (`chest_sport`, racerback seen from behind) | **Push-up bra** (`chest_push`: padded, straight straps, clasp from behind) | `bra='sport' | 'push'` in `build2.figure()`; global `B.BRA['v']` |
| Hair (female) | **Ponytail** | none | `HAIRSTYLE['v'] = 'pony'` |
| Views | Front, side (faces right), back | | `view` 'F' / 'S' / 'B' |
| Activation colouring | off | on, per pose | `figure(..., act=ACTS[pose])` or `act_fig()` |

Nothing else is optional: one sports-top and one push-up variant, two secondary faces, one hairstyle. Facial expressions/mouth shapes do **not** exist yet (see section 14).

### 1.3 Pose and asset inventory

All poses exist for both genders. "Plain" = the figure; "Activation" = same figure with muscles coloured by role (section 7).

| Pose key | View | What it shows | Plain | Activation |
|---|---|---|---|---|
| `relaxed` | front | standing, arms by sides | yes | no |
| `flex` | front | double biceps | yes | yes |
| `lateral` | front | arms out to the sides (lateral raise) | yes | yes |
| `side` | side | standing profile (= `SIDE_POSES['stand']`) | yes | no |
| `squat` | side | bodyweight squat | yes | yes |
| `calf` | side | calf raise | yes | yes |
| `pushup` | side | push-up | yes | yes |
| `plank` | side | forearm plank | yes | yes |
| `run_strike` | side | running: foot contact | yes | yes |
| `run_mid` | side | running: mid-stance | yes | yes |
| `run_off` | side | running: toe-off | yes | yes |
| `run_fly` | side | running: flight (both feet off ground, `lift=46`) | yes | yes |
| `back_relaxed` | back | standing from behind (activation card title: "Deadlift lockout") | yes | yes |
| `back_flex` | back | rear double biceps | yes | yes |
| `back_lateral` | back | arms out from behind (activation card title: "Reverse fly") | yes | yes |

Extra variants: female push-up-bra versions of `relaxed`, `flex`, `side`, `back_relaxed`, `back_flex`; faces Minimal and Ember visor on `relaxed` for both genders; heads (front + profile, faceless + Minimal + Ember visor, both genders).

---------------------------------------------------------------------------------------------------

## 2. File map (full paths)

Original workspace paths are given first; the same file exists in the bundle at the bundle-relative path.

### 2.1 Documents and the review page

| File | Path |
|---|---|
| This brief | `/home/claude/out/tibi_handover/HANDOVER.md` |
| File list with sizes | `/home/claude/out/tibi_handover/MANIFEST.txt` |
| Review page (the design as a document, 1469 KB, self-contained) | `/home/claude/out/tibi_handover/site/tibi_cobalt_sculpt_v6.html` (also `/home/claude/out/tibi_cobalt_sculpt_v6.html`) |
| Full-page screenshot of it, 1500 px wide | `/home/claude/out/v6_full.png` (not in the bundle; `png/page_sections/` has the same content in pieces) |

### 2.2 Source (generator)

Bundle: `/home/claude/out/tibi_handover/src/`. Original working copy of the same code: `/home/claude/gen/`. (The bundle copies are patched to be location-independent; prefer them.)

| File | Role |
|---|---|
| `src/rig.py` | **Male anatomy data**: front `FRONT`, side `SIDE`, skeletons `SK` / `SK_SIDE`, flame paths `FLAME_OUT/IN`, helpers `R` (rotate), `Sp` (spline), `n`, `blob`, `mx` |
| `src/rig_f.py` | **Female data**: `FRONT_F`, `SIDE_F`, `SK_F`, `SK_SIDE_F`; mostly `morph()` of the male data (x-scaling) plus hand-authored chest, pelvis, ponytail and bra variants |
| `src/rig_back.py` | **Back-view data** for both genders: `BACK`, `BACK_F`, helper `bk(D, **over)` |
| `src/build2.py` | **Builder and painter**: segments, poses, forward kinematics, shading, activations, faces, figure assembly |
| `src/page6.py` + `src/template6.html` | Review page generator and its HTML/CSS/JS shell |
| `src/export_assets.py` | Standalone SVG + transparent PNG exporter |
| `src/verify3.py`, `src/tog3.py` | Browser checks (section 11) |
| `src/lab.py`, `src/lab4.py` | Crop-and-zoom render helpers for inspecting one figure (section 11) |
| `src/shot.py` | Full-page screenshot of any HTML file |
| `src/chrome.py` | Chrome path helper (env `CHROME` overrides) |
| `src/build_v1.py`, `src/rig_v1.py`, `src/v3_defs.txt` | Not part of the character. Only used by `page6.py` for the before/after comparison panels inside review-page sections 1, 3 and 7. Safe to remove together with those panels (section 13). |

### 2.3 SVG assets (standalone: each file has its own `<defs>`, no external references)

Bundle: `/home/claude/out/tibi_handover/svg/`

`svg/figures/<gender>_<pose>.svg`, `<gender>` = `male` | `female`, `<pose>` = every pose key in the table in 1.3 (15 per gender = 30 files)
`svg/figures/<gender>_<pose>_activation.svg` for `pushup plank squat calf lateral flex run_strike run_mid run_off run_fly back_flex back_lateral back_relaxed` (13 per gender = 26 files)
`svg/figures/<gender>_relaxed_face_minimal.svg`, `..._face_ember_visor.svg` (4 files)
`svg/figures/female_<pose>_pushup_bra.svg` for `relaxed flex side back_relaxed back_flex` (5 files)
= 65 figure files.

`svg/heads/<gender>_head_<front|profile>_<faceless|minimal|ember_visor>.svg` = 12 files (viewBox `-100 -160 200 184`, centred on the head pivot).

Rules for standalone SVGs:
- Figure viewBox is `bbox.x-40, bbox.y-100, bbox.w+80, FLOOR+30-(bbox.y-100)`; the figure stands on y = 846 and is centred about x = 300.
- A soft floor ellipse is part of the figure group. Rig joint overlay is included but hidden by `.rig{display:none}` in the file's `<style>`; delete that rule to see the skeleton.
- Run figures read CSS custom properties `--ank-n` (near ankle) and `--ank-f` (far ankle), in degrees, default 0, positive = toes down. Set them on the `<svg>` element, e.g. `style="--ank-n:20;--ank-f:-10"`.
- The marigold spark has class `.spark`; hide it with `.spark{display:none}`.
- Numbered prime-mover badges are NOT in standalone activation SVGs (they are added by the page only, section 7.4).

### 2.4 PNG assets

Bundle: `/home/claude/out/tibi_handover/png/`

- `png/figures/*.png` and `png/heads/*.png`: one PNG per SVG above, same base name, **transparent background**, 2x (figures are 1200 px wide, e.g. `male_relaxed.png` = 1200 x 2740; heads are 480 px wide).
- `png/sheets/` (contact sheets for quick review, opaque background):
  - `male_poses_contact_sheet.png`, `female_poses_contact_sheet.png`
  - `male_activations_contact_sheet.png`, `female_activations_contact_sheet.png`
  - `heads_contact_sheet.png` (faceless, Minimal, Ember visor)
  - `variants_contact_sheet.png` (push-up bra and face variants)
- `png/page_sections/` (1500 px wide screenshots of the review page, one per section):
  `header_and_toolbar.png`, `00_round_summary.png`, `01_shoulder_and_lats.png`, `02_female_tibi.png`, `03_shorts_and_glutes.png`, `04_activations.png`, `05_running_ankle_slider.png`, `06_faces.png`, `07_bra_options.png`, `08_back_views.png`, `09_still_imperfect.png`.
  The contact sheets and section screenshots are reference renders; no script in `src/` regenerates them automatically (use `shot.py` for a full-page screenshot and crop per section id `#r5 #s1 ... #s9`).

Use these first if you only need to *look* at the designs: start with `png/sheets/*.png`, then `png/page_sections/04_activations.png`, `05_running_ankle_slider.png`, `08_back_views.png`.

---------------------------------------------------------------------------------------------------

## 3. Design tokens (do not change without asking)

| Token | Value |
|---|---|
| Canvas | `#F5F3EF` (page), `#FBFBFA` (paper/shoes) |
| Cobalt body | `#2F56E0` |
| Light plane | `#4F75EC` (`LT_`) |
| Shade plane | `#2244B8` (`DK_`) |
| Face plane (faceless / A) | `#3F66E8`; Ember visor plane `#1B338F` |
| Navy (ink, eyes, shadows) | `#18286F` |
| Marigold (spark, waistband, tie, visor eyes) | `#FFB224`; inner glow `#FFE08A` |
| Coral (prime mover) | `#F2553D`, shade `#B3301D`, highlight `#FF9C86` |
| Charcoal (shorts, top) | `#22243A`; bust/cups `#33375C`; back seat planes `#2D3158`; clasp `#454A7C` |
| Hair | `#1C3AA3`, light `#3558CF`, dark `#132A80` |
| Shoes | `#FBFBFA`, details `#B9C2DE`, shade `#CFD4E6` |
| Stabiliser | pale cobalt `#8CAEFA` |
| Light direction | from top-left: `LX, LY = -0.62, -0.78` |

Rules: no outlines (shading is by planes only), no logos anywhere (not on the shoes either), flat fills, slim marigold accents only. Scale: head ~100 units tall, figure stands on `FLOOR = 846`, centre line `CX = 300`.

Shading technique: every muscle plane gets a crescent shade made from an SVG `<mask>` (the shape minus the same shape offset toward the light), amount 5.5 units; highlights use the inverse offset at 2.6 units. Masks are generated on demand by `mask_id()` and cached (`k0, k1, ...`).

---------------------------------------------------------------------------------------------------

## 4. Architecture: how a figure is built

Everything is generated by Python into static inline SVG. There is no runtime layout logic in the SVG itself.

### 4.1 Data

Each body part ("segment") is a dict of splines in **neutral-pose coordinates**, with a pivot `piv`. The builder converts to local coordinates (`local = neutral - pivot`). Keys, per segment dict:

- `piv` pivot (joint) in neutral coordinates
- `base = (points, cornerIndexSet)` silhouette
- `mus [(name, points)]` muscle planes (drawn in order, so later ones cover earlier ones)
- `lines [(name, points)]` open strokes (creases, splits, veins; `vein` is never drawn, `clav notch lace toecap rim seam` have special handling)
- `cloth [(name, points, skip)]` shorts, bra, sole, thumb, tie, mound, clasp, tab
- `hem` optional marigold edge, `sh` fixed shade polygons, `blobs [(x,y,r)]` circles merged into the base path (knee, ankle and elbow caps)
- `bones`, `bone_lines`, `limb`, `sym`, `shoe`: authoring-time guide data and flags that live in the data dicts; the current builder and painter do not read them

Points are `(x, y)` or `(x, y, 'c')`; `'c'` marks a **corner** (the Catmull-Rom spline `Sp` breaks there, everything else is smooth). Viewer-left limbs are authored; viewer-right limbs are mirror-baked (`side='R'`).

Segment keys per view (`DATA[g] = (front, side, back)`; front and back share the same keys):

- Front / back: `head neck chest pelvis thigh shin foot upperArm upperArm_flex upperArm_nd forearm hand fist cap flare`; female also `pony` and chest variants `chest_sport chest_push` (`chest_bralette` exists but is unused)
- Side: `head neck chest pelvis thigh shin foot upperArm forearm hand`; female also `pony` and the same chest variants

`cap` is the deltoid dome (drawn over the arm root when the arm is raised), `flare` is the lat wing (drawn behind the torso when the arm is raised), `upperArm_flex` / `upperArm_nd` are the upper-arm shapes for double-biceps and lateral-raise (`nd` = no deltoid, the cap supplies it), `fist` replaces `hand` in the flex pose.

Muscle names used in `mus`: `pec delt triceps biceps brach flexor abs oblique serratus lat trap quad vastus vmo hams gastro soleus tibant glute hipflex adductor rhomb infra erector extensor scm patella navel face hairplane`. Display names: `build2.NICE` / `LABEL`.

### 4.2 Registration and naming

`mk(g, view, key, side)` converts one segment's data to registered `<path>` defs (cached). Ids:

- shapes: `{g}{view}_{key}_{side}_{b|m#|l#|c#|h|s#}` e.g. `mF_thigh_L_m0` (g = `m`/`f`; view = `F`/`S`/`B`; side = `L` `R` `C`; `b` base, `m#` muscle, `l#` line, `c#` cloth, `h` hem, `s#` shade)
- figures: `fig-{g}-{pose}[-{tag}]`, tag `act` (activation), `faceA`, `faceC`, `push` (push-up bra) e.g. `fig-f-back_flex-act`
- segment groups inside a figure: `fig-...-{key}{side}[-far]`, e.g. `fig-m-relaxed-thighL`; side-view segments use side `C` (no suffix) and far limbs end in `-far`
- heads: `head-{g}-{F|S}-{0|A|C}` (0 = faceless)
- masks: `k0, k1, ...`, defined in `userSpaceOnUse` over x -420..480, y -480..520

Shapes are stored **once** as `<path id>` in a hidden global `<defs>`; figures reference them with `<use>`. This keeps the page at 1.4 MB and is what the standalone exporter's `closure()` walks to build self-contained SVGs.

### 4.3 Segments and poses

`Seg(g, view, key, side, W, th, sx, sy, far, skey)` is one placed segment: world pivot `W`, rotation `th` (deg, clockwise positive), scale `sx, sy`, `far` (dimmed depth copy), `skey` (data key, e.g. `chest_sport`; `key` is the part name). Group transform is `translate(W) rotate(th) scale(sx,sy)`. **Draw order = order in the segment list** (back to front).

- Front/back poses: `front_pose(g, kind, view='F')`, kinds `relaxed` arms (8, 10, 9) deg, `flex` (86, 190, 192), `lateral` (80, 86, 84) as (upper arm, forearm, hand) rotations; thigh tilt 1.5 deg (relaxed) or 3.5 deg. Back poses are `back_<kind>`: identical kinematics with view `'B'`. The back ponytail is drawn **after** the head (it hangs in front of it from behind) with pivot (CX+8, 16), swept to the viewer's right.
- Side poses: `side_fk(g, spec)` generic forward kinematics. Angles are absolute degrees, clockwise-positive (a hanging leg swings forward with a negative angle; an upright torso leans forward with a positive one). Bone lengths: pelvis->hip 58, pelvis->chest 64, chest->neck 118, neck->head 56, thigh 178 x leg factor, shin 166 x leg factor, upper arm 134, forearm 106.
- `settle()` slides the figure so its lowest contact (foot, plus hand for plank/push-up) sits on `FLOOR` (minus `lift` for the flight phase).
- Push-up and plank use a solver (bisection over body angle beta in 64..86 deg) so hands and feet both touch the floor.

Side-pose table (`SIDE_POSES`; `tp tc tn th` = pelvis, chest, neck, head angle; `lo(thigh, shin, foot)`; `ar(upper arm, forearm, hand)`):

| Pose | tp tc tn th | near leg | far leg | near arm | far arm |
|---|---|---|---|---|---|
| stand | 0 0 0 0 | (1, 0, 0) | (-8, 4, 0) | (-4, -18, -20) | (-14, -30, -30) |
| run_strike | 5 9 8 4 | (-30, -14, -6) | (24, 72, 36) | (34, -52, -40) | (-44, -134, -120) |
| run_mid | 6 10 8 4 | (-6, 14, 0) | (-34, 62, 22) | (-6, -92, -92) | (6, -70, -60) |
| run_off | 8 12 10 5 | (30, 36, 62) | (-64, -6, 18) | (-44, -128, -118) | (40, -46, -34) |
| run_fly (lift 46) | 7 11 9 4 | (34, 80, 58) | (-56, -10, 14) | (-36, -120, -110) | (34, -48, -40) |
| squat | 42 48 40 22 | (-84, 24, 0) | (-84, 24, 0) | (-84, -88, -88) | (-88, -92, -92) |
| calf | 0 0 0 0 | (0, 0, 46) | (0, 0, 46) | (-4, -18, -20) | (-12, -28, -28) |

### 4.4 Painter (`p_sculpt`) layer order per segment

base fill -> fixed shade polys -> each muscle plane (`LT_` fill + shade crescent, or activation colour with halo, shade, highlight) -> lines -> cloth (shorts, bra, band, thumb, tie, mound, clasp) -> hem -> ghost overlays (glutes, hip flexors) -> face group (head only) -> far-limb navy overlay. Feet are painted separately (white shoe, crescent, `#B9C2DE` details). Hair (`pony`) is its own painter branch. The female back view draws a `mound` (two raised seat planes) and a `seam` on the shorts.

### 4.5 Rig overlay and animation hooks

- Every figure ends with `<g class="rig">`: dashed navy bones with marigold joint dots, hidden unless `--rig-d:inline`.
- Every segment group has an id and a pivot at its joint, so a downstream tool can animate by rotating the group (the review page does this only for the ankle).
- Ankle: foot segments of `run_*` figures are wrapped in `<g style="transform:rotate(calc(var(--ank-n|--ank-f,0) * 1deg))">`; origin is the ankle because the foot group's local (0,0) is the ankle pivot.
- Spark: `<g class="spark">` inside the head segment, class-toggleable. Face: `<g transform="translate(0,-92)">` inside the head segment, so faces swap without touching the body.

---------------------------------------------------------------------------------------------------

## 5. The options in detail

### 5.1 Faces (`build2.face_front(style, g)`, `face_side(style, g)`)

Faces are small groups in head coordinates (head origin = head pivot, face group at `translate(0,-92)`).
- **None (default):** nothing drawn; the head's `face` plane (`#3F66E8`, with a `DK_` crescent) is the only feature.
- **A, Minimal:** two navy ellipses at x = +/-13.5, y = 59 (rx 4.9, ry 6.4) with a white catch-light, a smile `M-8.5,76 Q0,84 8.5,76`; female adds a small lash flick at each outer eye corner. Side view: one eye at (24, 59) and a smile at x 27..36.
- **C, Ember visor:** the face plane becomes `#1B338F`; marigold eyes (rx 5.4, ry 6.6) with a `#FFE08A` inner glow; a small `#FFE08A` smile; female has a marigold lash tick. Side view mirrors the construction.

`build2.FACE_NAMES` also lists a style `B` ("Soft features") and the code paths for it still exist (`face_front/face_side` else-branches, `HAIR_CAP_*`): it is **not** part of the design. Do not expose it.

### 5.2 Female top (`chest_sport` default, `chest_push` secondary)

- **Sports top (default):** straight upper edge, racerback straps seen from behind (`_racer` in `rig_back.py`), outline defined by `_braS` in `rig_f.py` (neutral-coordinate y 197 at the top edge to y 236 at the bottom edge).
- **Push-up (secondary):** two projecting cup planes (`bust`) with a slim band; straight straps and a `clasp` plane from behind.
- Select with `figure('f', pose, tag='push', bra='push')`. The default build uses `bra='sport'`.

### 5.3 Hair

Ponytail only. `pony` segment: front view pivot (CX+30, 22), drawn **before** the head (behind it); side view pivot at head + R(th, (-30, -68)); back view after the head. Parts: a `HAIR` base, `HAIR_LT` hair plane with a `HAIR_DK` crescent, `tie` in marigold.

### 5.4 Wardrobe notes

Male: no shirt; shorts are one charcoal group (`shorts` + `shortsleg` on each thigh) with a marigold `band`. Glute and hip-flexor planes sit underneath the shorts and show as translucent overlays only when activated (`GHOST`). Female uses the same shorts, a top, and the same trainers (white, no logo).

---------------------------------------------------------------------------------------------------

## 6. Anatomy details worth knowing before you edit

- Neck-to-shoulder slope: male `chest.base` upper edge `cl=[(0,160),(-12,156),(-21,127,'c'),(-37,135),(-57,144),(-76,152),(-90,159),(-99,170)...]` with trapezius polygon `trap=[(-22,131)...]`; female uses the lower-sloping `clf` / `trapf` in `rig_f.py`.
- Joint caps: knee, ankle and elbow are `blobs` merged into the base spline (`FRONT['shin'] blobs=[(-43,566,17),(-46,731,11)]`, `forearm [(-101,298,13)]`, plus side-view equivalents). The blob sub-path sweep flag is matched to the base spline winding (`sw_` in `mk()`); keep that or a white crescent appears for the mirrored side.
- Hand: front `hand` is a single spline outline from `_hand_outline()` in `rig.py` (four separate fingers with rounded tips, corner notches between them, thumb is a separate `cloth` plane). `fist` and the side-view `hand` are still simple shapes.
- Ankle and shoe: wider ankle (`sh_out`/`sh_in`) and a shoe collar so the leg flows into the trainer.
- Back view: trapezius is a narrow kite hugging the medial scapula (`_trap_b`), infraspinatus + teres blobs (`_infra`, `_teres`), lats with their upper edge rising medially (`_lat_b`), erector spinae down the spine, gluteal planes under the shorts, hamstrings (two heads), gastrocnemius (two converging heads) + soleus + Achilles tendon, forearm extensors and the triceps horseshoe on the raised arms. Rhomboids are **not** drawn separately; the trapezius stands in.
- Heel view of the trainer: a `tab` (pull tab), a `collar` line and a single `counter` stitch line. No logo.

---------------------------------------------------------------------------------------------------

## 7. Activation system

Activation = recolouring existing muscle planes. No extra geometry is needed for the front, side and back views.

### 7.1 Levels

| Level | Meaning | Look |
|---|---|---|
| 3 | prime mover | coral `#F2553D` plane, `#B3301D` shade, `#FF9C86` highlight, soft halo stroke (opacity .30) |
| 2 | secondary / assisting | marigold `#FFB224`, shade `#CC7A0A`, highlight `#FFE29A`, halo (.32) |
| 1 | stabiliser | pale cobalt `#8CAEFA`, shade `#2F56E0`, highlight `#C9D9FF`, no halo |
| 0 | idle | normal cobalt light plane |

Suffix `@near` / `@far` on a muscle key targets only the near or far limb (run poses). `glute` and `hipflex` are `GHOST` muscles: when level >= 2 they are drawn as a translucent overlay on top of the shorts at 82 % opacity.

### 7.2 Tables (`build2.ACTS`, exact)

```python
'pushup':  {'pec':3,'delt':3,'triceps':3,'serratus':2,'abs':2,'oblique':1,'quad':1,'vastus':1,'glute':1,'trap':1,'forearm':0}
'plank':   {'abs':3,'oblique':3,'serratus':2,'delt':2,'glute':2,'quad':1,'vastus':1,'pec':1,'trap':1}
'squat':   {'quad':3,'vastus':3,'vmo':3,'glute':3,'hams':2,'soleus':2,'gastro':1,'abs':1,'oblique':1,'tibant':1}
'calf':    {'gastro':3,'soleus':3,'tibant':1,'quad':1,'vastus':1,'abs':1}
'lateral': {'delt':3,'trap':2,'serratus':1,'abs':1,'oblique':1,'brach':1,'flexor':1}
'flex':    {'biceps':3,'brach':2,'delt':2,'flexor':1,'pec':1,'trap':1,'abs':1,'oblique':1}
'run_strike': {'quad@near':3,'vastus@near':3,'vmo@near':3,'tibant@near':3,'glute':2,'abs':1,'oblique':1,
               'hams@far':2,'gastro@far':1,'triceps@near':2,'biceps@far':2,'delt@far':2,'lat@near':1}
'run_mid': {'soleus@near':3,'gastro@near':2,'glute':3,'quad@near':2,'vastus@near':2,'hams@near':1,'abs':2,'oblique':2,
            'hipflex':3,'hams@far':2,'quad@far':1,'biceps@near':1,'delt@near':1,'triceps@far':1}
'run_off': {'glute':3,'gastro@near':3,'soleus@near':3,'quad@near':2,'vastus@near':2,'hipflex':3,'quad@far':3,'abs':2,
            'oblique':1,'biceps@near':2,'delt@near':2,'triceps@far':2,'tibant@far':1}
'run_fly': {'hams@near':3,'gastro@near':1,'glute':2,'hipflex':3,'quad@far':3,'vastus@far':2,'abs':2,'oblique':1,
            'biceps@near':2,'delt@near':2,'triceps@far':2,'tibant@far':1}
'back_flex':    {'lat':3,'trap':3,'infra':2,'delt':2,'triceps':2,'erector':1,'oblique':1,'extensor':1}
'back_lateral': {'delt':3,'infra':3,'trap':2,'triceps':1,'extensor':1,'erector':1,'glute':1,'hams':1}
'back_relaxed': {'glute':3,'hams':3,'erector':3,'trap':2,'lat':2,'infra':1,'oblique':1,'gastro':1,'soleus':1}
```

The three quad keys (`quad vastus vmo`) display as one "Quadriceps" label (`LABEL`).

### 7.3 API

```python
import build2 as B
fid, bbox = B.figure('f', 'run_mid')                  # plain figure -> id 'fig-f-run_mid'
fid, bbox = B.act_fig('m', 'back_flex')               # activated   -> id 'fig-m-back_flex-act'
fid, bbox = B.figure('f', 'relaxed', face='C', tag='faceC')
fid, bbox = B.figure('f', 'flex', tag='push', bra='push')
B.FIGS[fid]['svg']   # the <g id=...> markup;  B.all_defs() = every <path>, <mask> and figure group
B.marker_pts(fid, B.ACTS['flex'])                     # numbered-marker positions for prime/secondary muscles
```

### 7.4 Numbered badges

Page-level only: `page6.marker_svg(markers, vb, box)` draws numbered circular badges for the **prime movers** (level 3), parked in the margin with thin leader lines to a dot on the muscle so the planes stay visible; the same numbers key the muscle list under each figure (`legend_lists`). They are not in the standalone SVGs.

---------------------------------------------------------------------------------------------------

## 8. The review page (`site/tibi_cobalt_sculpt_v6.html`)

Built by `src/page6.py` from `src/template6.html` (placeholders `%%GLOBAL%%` = hidden defs, `%%BODY%%` = sections). Sections, in order:

| id | Section | Contents |
|---|---|---|
| `#r5` | Summary band | short summary band of recent changes (constant `ROUND5`; can be deleted) |
| `#s1` | Shoulder join and lats | double biceps with the deltoid cap and lat wing |
| `#s2` | Female Tibi | both characters x relaxed / double biceps / side, proportions table, swatches |
| `#s3` | Shorts and glutes | waist line, shorter female shorts, softer glutes |
| `#s4` | Activations | six cards: push-up, forearm plank, squat, calf raise, lateral raise, double biceps (`ACARDS`) |
| `#s5` | Running | four phases (`RUN`), prime-mover lists, **ankle-angle slider** |
| `#s6` | Faces | Faceless (default), Minimal, Ember visor (`FACES`) |
| `#s7` | Bra options | Sports top (default), Push-up |
| `#s8` | Back views | turnaround cards (front/back, relaxed and double biceps) + three back activation cards (`BACKCARDS`: rear double biceps, reverse fly, deadlift lockout) |
| `#s9` | Still imperfect | honest list of limitations and open choices |

Sections 1, 3 and 7 also contain before/after comparison panels built from frozen legacy assets (see 2.2); they are not part of the design.

### 8.1 Controls (toolbar and section 5)

- Toolbar: `Show` Both / Male / Female -> `body[data-show]` (`both|m|f`; CSS hides `.g-m` / `.g-f`); `Pose (section 2)` Relaxed / Double biceps / Side / All three -> `body[data-pose]`; `Spark` (`#sparkChk`, class `nospark`); `Muscle numbers` (`#mkChk`, class `nomk`); `Rig joints` (`#rigChk`, class `rigon`).
- CSS custom properties `--spark-d` and `--rig-d` on `body` drive `.spark{display:var(--spark-d)}` and `.rig{display:var(--rig-d)}`. This is deliberate: custom properties inherit into `<use>` shadow trees, whereas ancestor selectors such as `body.nospark .spark` do not reach them. Follow the same pattern for any new toggle that must reach inside a `<use>` instance.
- Section 5 ankle controls: ids `ankN` (near range input), `ankF` (far), `ankLink` (link checkbox), `ankAnim` (animate checkbox), `ankReset`, readouts `ankNo` / `ankFo`. They set `--ank-n` / `--ank-f` on `#s5` (default `#s5{--ank-n:0;--ank-f:0}`). Animate runs a requestAnimationFrame sine, near ankle 5 +/- 22 deg, far in anti-phase unless linked. Positive = toes down.

### 8.2 Responsiveness and quality bar

The page must have no horizontal scroll at 390, 820 and 1500 px wide and no console errors; `verify3.py` checks both.

---------------------------------------------------------------------------------------------------

## 9. Measured facts and numbers you can rely on

- Heads tall: male 7.66, female 7.55 (`page6.heads_tall`). Hip joint (-38, 388), knee (-43, 566), ankle (-46, 732) for him; hers (-36, 388), (-42, 566), (-45, 732), shoulder (-86, 162) vs his (-100, 162).
- Figure bounding boxes (relaxed, front): male x 140..460, y 64..846; female x 156..444, y 76..846.
- Arms in the front poses are authored for the viewer's left and mirror-baked for the right, so asymmetry is only introduced by pose angles, not by data.
- Far limbs in side poses are the same shapes drawn behind and dimmed (navy overlay at 22 to 25 % opacity); this is intentional depth cueing, not a separate drawing.

---------------------------------------------------------------------------------------------------

## 10. Recipes

**Add a new front/back pose** (e.g. overhead press): add a kind to the `arms` dict in `front_pose()` (three angles), add its `ACTS` entry, pick `upperArm_*` / `hand|fist` keys, call `B.figure(g, 'press')` (and `back_press` automatically uses view 'B'), then add the name to `PLAIN` / `ACT` in `export_assets.py` and a card in `page6.py`.

**Add a new side pose:** add `SIDE_POSES['name'] = dict(tp=..,tc=..,tn=..,th=..,near=dict(leg=lo(..),arm=ar(..)),far=dict(..),contacts=('foot',))`, optionally `lift`; `figure(g,'name')` then works. Use `python3 lab.py out.png name m,f x0 y0 x1 y1 2` to check it.

**Edit a muscle shape:** change its point list in `rig.py` (male) or `rig_f.py` (female; check whether it is a `morph()` of the male one, in which case edit the male source and the morph follows) or `rig_back.py` (back). Keep corner flags. Rebuild, then inspect with `lab.py`. Muscle planes stack in list order.

**Add a new face:** add a style key to `face_front` / `face_side` (return SVG for the head's `translate(0,-92)` group), then pass `face='X'` to `figure()` and `head_only()`; add it to `FACES` in `page6.py` and to the face loops in `page6.py` and `export_assets.py`.

**Add a new female top:** add a `chest_<name>` key to `FRONT_F`, `SIDE_F` and `BACK_F`, then call with `bra='<name>'`.

**Animate the ankle in a real animation tool:** import a `run_*` standalone SVG, set `--ank-n` / `--ank-f` (degrees) on the root element; or rotate the foot group directly around its local origin.

**Rig for After Effects / Rive / Lottie later:** each segment is already a `<g id="fig-{g}-{pose}-{key}{side}">` with its pivot at the joint (translate = world pivot, local origin = joint). Split the figure at those ids; draw order is the order in the file.

---------------------------------------------------------------------------------------------------

## 11. Commands and environment

```bash
cd <BUNDLE>/src

python3 page6.py                              # build the page; env TIBI_OUT=/some/dir changes the output folder (default ../site)
python3 verify3.py [page.html]                # duplicate ids, missing refs, external refs, scrollWidth @390/820/1500, console errors, toolbar list
python3 tog3.py [page.html]                   # smoke test of the Show / Pose / Muscle-numbers toggles (prints image hashes; a changed hash = the toggle did something, it asserts nothing)
python3 lab.py out.png pose[,pose] g[,g] x0 y0 x1 y1 [scale]   # crop-render figures in world coordinates; accepts any pose key incl. back_* and run_*; env HAIR=pony
python3 lab4.py out.png "pose:hair:bra,pose:hair:bra" x0 y0 x1 y1 scale   # female variants, e.g. "relaxed:pony:push"
python3 shot.py /abs/path/page.html out.png [width]            # full-page screenshot (default width 1500)
python3 export_assets.py [OUTDIR]             # all standalone SVGs + transparent PNGs; default OUTDIR = bundle root
```

Examples: `python3 lab.py /tmp/back.png back_flex m,f 130 60 470 480 2` and `python3 lab.py /tmp/run.png run_mid m 170 0 560 880 1.5`.

- Python 3 standard library only for `page6.py` and `build2.py`. Playwright for Python is needed for verify, tog, lab, shot and the PNG half of export (`pip install playwright`). If Playwright cannot download a browser, point it at a local one: `export CHROME=/usr/bin/google-chrome` (default if that file exists; otherwise Playwright's bundled Chromium, installed with `playwright install chromium`). `export_assets.py` prints `PNG export skipped: ...` and still writes the SVGs if Playwright is unavailable.
- Pillow was used only to make the contact sheets; it is not needed to build anything.
- `src/__pycache__` is deleted in the bundle; Python recreates it.

Working rules that kept the output clean:
1. After any change to the data or builder, rebuild and run `verify3.py`, then **look** at the affected figures with `lab.py` at 2x or more. Shape bugs (gaps, wrong winding, a muscle covering another) are visual.
2. Compare male and female every time; the female data is largely derived, so a male fix can shift her silhouette.
3. Check both the plain figure and the `-act` version, and the far limbs in side poses.
4. Do not hard-code paths; scripts must keep working from any folder.

---------------------------------------------------------------------------------------------------

## 12. Known limitations (be honest about these with the owner)

- Hands: the front hand has four separate fingers and a thumb but no finger joints. `fist` (flex pose) and the side-view `hand` are still simple shapes.
- Far limbs in side and running poses are mirrored, dimmed copies of the near limb (intentional depth cue, not independent drawings).
- Bra straps (sports top included) are straight rigid strips; the racerback straps from behind are straight too.
- The ankle slider rotates the whole shoe as one rigid piece. Beyond about 35 deg the foot looks stiff: the sole does not bend at the toes and the heel does not lift.
- Back views exist for relaxed, double biceps and arms-out only (no back running, squat, push-up or plank), no face (nothing to see from behind), and the rhomboids are not drawn separately (the trapezius plane represents them).
- Faces have no expressions or mouth shapes yet, so a narrated character cannot lip-sync.
- Activation badges only exist on the page, not in standalone SVGs.

## 13. Dead code and removable parts

Safe to delete once you are sure the owner does not want them back (nothing in the current design uses them):
- Curly hair: `HAIRSTYLE 'curly'`, the `curls` segment data in `rig_f.py`, its painter branch in `p_sculpt` and `figure()`.
- `chest_bralette` in `rig_f.py` and `rig_back.py` (third top style, unused).
- Face style `B` (the `elif style == 'B'` branches in `face_front` / `face_side`, `HAIR_CAP_F`, `HAIR_CAP_FEM`, `HAIR_CAP_S`, and the `hd` hair-cap block in `p_sculpt`).
- Legacy comparison panels in `page6.py` sections 1, 3 and 7 and everything they import (`build_v1.py`, `rig_v1.py`, `v3_defs.txt`, the `old` / `V3DEFS` lines near the top of `page6.py`). Removing them makes the page smaller and removes three source files.
- `bones`, `bone_lines`, `limb`, `sym`, `shoe` data keys (the painter does not read them; `sym` helpers in the data files may still use their own flags, so grep before deleting).

## 14. Suggested next steps (ask the owner which to do)

1. **Faces, if one is chosen:** a mouth-shape (viseme) set for narration plus brows/eye states for effort and fatigue; the visor face needs the most care to avoid reading as a robot.
2. **Back poses:** back-view running, squat, push-up/plank variants using the existing back data (`front_pose(..., 'B')` and the side solver are already view-agnostic, so this is mostly adding entries).
3. **Hands:** finger joints, a better fist, a proper side-view hand.
4. **Foot:** a two-piece shoe (heel + forefoot) so the ankle/toe-off can bend.
5. **Straps:** bend-capable bra straps.
6. **Animation export:** split each pose into named layers per segment (already addressable by id) and produce a Lottie/Rive/After Effects-friendly export, with the activation colours as keyframeable fills.
7. **Rhomboids and lower-back detail** if a lesson needs them called out separately.
8. **A script that regenerates the contact sheets and per-section screenshots** (currently produced ad hoc).

## 15. How to start your session

1. Read this file, then open `site/tibi_cobalt_sculpt_v6.html` (or look at `png/sheets/*` and `png/page_sections/*`).
2. Run the Quick start commands in section 0 and confirm the baseline matches.
3. Ask the owner what to do next, offering the options in section 14, or take the request they give you.
4. Make changes in `src/`, rebuild, verify, look at the result, and re-export assets with `export_assets.py` so `svg/` and `png/` stay in step with `site/`.
5. When you commit anything to git, follow the attribution lines you were given for this environment.
