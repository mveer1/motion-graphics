# Fitness research protocol and evidence grading

Fitness claims change what people do with their bodies, so they carry more care than ordinary explainers. This specialises `technical-researcher` (which still writes `research.json`); the fitness layer adds `research/dossier.json` (`specs/fitness-dossier-spec.json`), checked by `python scripts/fitness.py dossier <slug>`.

## 1. Question first

Write the one research question the film answers ("What makes a muscle grow after resistance training, and is damage the trigger?"). Then list the claims the story needs, and look for each claim's best evidence; do not collect papers first and build a story from them.

## 2. Source priority

1. Systematic reviews and meta-analyses (Cochrane, BJSM, Sports Medicine, J Strength Cond Res...).
2. Randomised controlled trials.
3. Well-designed observational and longitudinal training studies.
4. Exercise physiology textbooks (facts only; check the licence before using any figure).
5. Position stands from professional bodies (ACSM, NSCA, ISSN, IOC consensus).
6. Single mechanistic or acute studies, which say what happens in a session, not what happens over months.

Search PubMed and Cochrane by title; fetch abstracts from **Europe PMC's REST API** (`https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:<PMID>%20AND%20SRC:MED&resultType=core&format=json`, or `TITLE:"..."`), because PubMed pages block automated fetches. Record `verified_via` for every source. Quote numbers from the abstract or the full text you actually read, never from memory or a secondary blog.

## 3. Evidence grades (fixed colours on screen: `G.evidenceBadge`)

| Grade | Use when | Example |
|---|---|---|
| `established` | Textbook mechanism agreed for decades | sliding filaments; mTORC1 needed for the contraction-induced rise in protein synthesis |
| `strong` | Consistent systematic reviews or meta-analyses of RCTs (the dossier check requires one among the sources) | light and heavy loads to failure grow similar muscle (Schoenfeld 2017) |
| `moderate` | Several RCTs, or one meta-analysis with real limits | tension as the leading hypertrophy stimulus; acute protein-synthesis time course |
| `preliminary` | Few or small studies, animal or cell work, acute markers only | a new supplement's acute signalling effect |
| `hypothesis` | Plausible, untested in humans | a specific mechanosensor pathway |
| `unsupported` | Evidence contradicts it (myths) | "soreness means growth" |

Separate on screen and in words: an **established mechanism**, a **finding** (what a study measured), a **number** (with population, design and n), a **hypothesis**, and an **anecdote** (never presented as evidence).

## 4. The dossier (`research/dossier.json`)

For each source: id, full citation, year, design, population, n, duration, key findings, limitations, url/doi/pmid, verified_via. For each claim: id (`c1`...), the claim, the grade, the kind, the sources, `where` (scenes), the exact safe `wording` and caveats. Plus `conflicting_evidence`, `do_not_claim`, `medical_boundary` and `reviewed` (by, date, verdict). Every sentence of narration and every on-screen number maps to a claim id.

## 5. Rules

- Never fabricate citations, findings, mechanisms or statistics. If a claim cannot be sourced, cut it.
- Acute is not chronic: "protein synthesis +109% at 24 h" is not "muscle grows 109%".
- Say the sample when it is small ("one study, 6 men") and frame the finding as directional.
- A myth film states the strongest honest version of the belief before the counter-evidence.
- No activation percentages or "isolation" claims; no supplement endorsements; no doses as prescriptions ("about 1.6 g/kg/day is where added protein stopped adding muscle in a meta-analysis" is a finding, "eat 1.6 g/kg" is advice).
- Injury and pain topics: general education only, the medical boundary line on screen and in the description, and no diagnosis, rehabilitation protocol or return-to-run advice.
- Units and scale labels come from a source too (the demo's sizes cite OpenStax §10.2).
- Re-check the dossier after every script change (`fitness.py dossier`), and before review.

## 6. Hand-offs

The story-writer opens a research request for any beat that needs a fact the dossier lacks. The researcher answers in the dossier, never in the script. A `needs-research` request on a name already in the film blocks the render (story-writer rule L14).
