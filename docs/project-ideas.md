# Next project ideas

Backlog of video ideas. The project catalogue (`out/catalogue.html`, tab "Ideas") reads this file and shows it as an editable sheet. Add, edit or delete ideas there, then use "Download .md" and save the file over this one (or edit it here), and rebuild with `python3 scripts/build-catalogue.py`.

Format: one `## <category id>` heading per category (ids are in `specs/categories.json`), then one bullet per idea: `- **Title** — one-line pitch (also: id, id) [length]`. `(also: ...)` is optional and lists secondary categories. `[length]` is required and is one of the video types in `specs/video-types.json`: `short` (short-form micro explainer, 20-60 s), `mid` (mid-form focused explainer, 60-180 s) or `long` (long-form documentary or deep dive, 5-12 min), each with a 15 s margin. The pre-2.0 tags `reel`, `long-reel` and `youtube` are still read. Every idea needs research before it is briefed.

## technology
- **What happens when you type a URL** — Follow one DNS lookup from the browser to the root servers and back, and show why it takes tens of milliseconds. [mid]
- **The padlock handshake** — How TLS lets two strangers agree on a secret in the open. Pairs with the Raft and B-tree explainers as an "internals" run. [mid]
- **Consistent hashing** — Why adding one server should not reshuffle every key, shown as a ring that only moves a little. [short]

## finance
- **How a bank run works** — Why a healthy bank can fail in days once enough people want their money at once. The 2023 Silicon Valley Bank run is the worked example. (also: news) [mid]
- **The rule of 72** — Compound interest as a doubling clock, with three rates side by side. [short]
- **Why most stock pickers lose to an index** — Fees, averages and the arithmetic of beating the market, with the numbers sourced. [mid]

## science
- **Why the sky is blue and sunsets are red** — Rayleigh scattering as light travelling through more or less air. [short]
- **Why ice floats** — The hydrogen-bond lattice that makes frozen water less dense, and what that means for lakes in winter. [short]
- **How a vaccine teaches the immune system** — The first exposure, the memory cells and the second exposure, with no jargon. [mid]

## history
- **The Broad Street pump** — John Snow's 1854 cholera map and the argument that water, not "bad air", carried the disease. (also: science) [mid]
- **The Salt March, 1930** — Twenty-four days on foot to a pinch of salt, and why a tax became a turning point. [long]
- **What we actually know about the Library of Alexandria** — Separating the record from the legend. [long]

## mathematics
- **The birthday paradox** — Why 23 people give better than even odds of a shared birthday. [short]
- **Why 0.999… equals 1** — Three short arguments, from fractions, from limits and from the number line. [mid]
- **Fourier series: drawing with circles** — Stacked rotating circles trace any closed curve. Visual-first, little narration. [mid]
- **Why tit for tat won: Axelrod's tournaments** — Part 2 of the game-theory-trust reel: play the prisoner's dilemma again and again, and the simplest entry, start nice then copy, won Axelrod's 1980 tournament and the second one. Needs research on how matches were scored, how many rounds each pairing played, who the rivals were, and why tit for tat came first while never beating its partner in a single pairing. [mid]

## news
- **How a power grid blackout cascades** — Why one failure spreads and what grid operators do to stop it. Needs a recent, well-sourced event to anchor it. (also: technology) [mid]
- **Undersea cables and the internet** — Most international traffic crosses the sea floor, so a cut changes what loads. Natural follow-up to the Korea, cloud and fridge films. (also: technology) [mid]

## storytelling
- **The Voyager Golden Record** — What was put on a record meant for someone else, and who chose it. (also: science) [long]
- **One raindrop, one monsoon** — A narrative-first journey from sea to cloud to a street in July. Mood over explanation. [mid]
- **The tea stall at 1 a.m.** — A quiet portrait piece built around one scene and one sound bed. Builds on the masala-chai look. [short]
