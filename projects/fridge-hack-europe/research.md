# Research: The 2026 European supermarket refrigeration attacks

Consulted 2026-11-02, the day the second wave was reported. The story is still developing: counts, vendors and attribution are provisional. Machine-readable version: `research.json`. Every number on screen must match this page, including ranges and "reported" qualifiers.

## Correction to the pitch

The pitch said "hackers turned off supermarket refrigerators (November 2026)". Reporting says something different:

- The attackers did not switch fridges off. They forced **defrost mode**, so the equipment heated itself with food still inside.
- November 2026 is the **second wave**. The first and larger wave hit France overnight on **11-12 October 2026**.

The film covers both waves.

## Sources

| Source | Used for |
| --- | --- |
| [Wikipedia, 2026 French supermarket refrigerator hack](https://en.wikipedia.org/wiki/2026_French_supermarket_refrigerator_hack) (secondary; edited 2 Nov, flagged as a snapshot with weak citations in places) | timeline, chain counts, temperatures, models, end-of-life dates, ANSSI response, second-wave countries |
| [CBS News, 12 Oct](https://www.cbsnews.com/news/cyberattack-supermarkets-refrigerators-france-fires-food-losses/) (AFP-based) | chains confirming, Danfoss statement, fires confirmed by Paris prosecutors, quotes |
| [Help Net Security, 2 Nov](https://helpnetsecurity.com/2026/11/02/european-supermarkets-refrigeration-units-cyberattacks) | second wave countries, Sunday-midnight start, Sabcobel on the fix, end-of-life units left online |
| [TechCrunch, 2 Nov](https://techcrunch.com/2026/11/02/a-fresh-wave-of-cyberattacks-has-hit-europes-supermarket-refrigerators-destroying-food-across-countries/) | Ahold Delhaize and Colruyt confirmed; "changed the settings to defrost" |
| [Claroty Team82, "Freeze the controller, defrost the food"](https://claroty.com/team82/research/freeze-the-controller-defrost-the-food-uncovering-vulnerabilities-in-danfoss-refrigeration-controllers) (primary, vendor research) | what the AK-SM 800A is, the code-of-the-day bypass (CVE-2025-41450), 2,765 exposed devices, fix in R4.3.1 |
| [CISA ICSA-25-140-03](https://www.cisa.gov/news-events/ics-advisories/icsa-25-140-03) (listed in search results; page not opened) | existence of a 2025 advisory on the AK-SM 8xxA |
| Search-result summaries of SecurityWeek, BleepingComputer, The Local, ACHR News, Al Jazeera, Reuters syndication | chain counts, the "one to eight hours" defrost extension, Shodan, alarms, CERT-FR advice. These pages returned 403 and were **not opened**; treat their claims as medium confidence |
| USDA FSIS and Australian state food authorities (search summaries) | danger zone, bacterial doubling time |

Not read: the CERT-FR bulletin (CERTFR-2026-ALE-012), the Danfoss advisory, any French court or ANSSI document. No primary government text was read.

## Verified claims used in the film

- **When (wave 1):** overnight **Sunday 11 to Monday 12 October 2026**. Intermarché, Coopérative U and E.Leclerc confirmed to AFP on Monday 12 October.
- **What happened:** controllers were set to **forced defrost**; some freezers were reportedly extended from a one-hour to an **eight-hour** defrost cycle (medium confidence, single summary of Reuters-syndicated coverage).
- **Temperatures:** many cases reached about **50 °C** after about six hours (Wikipedia; widely repeated). One Normandy store reported **80 °C** (single-store report).
- **Damage:** Paris prosecutors confirmed the attack **sparked fires** and opened an investigation (CBS). Intermarché said affected branches must discard all fresh and frozen products.
- **Scale:** counts conflict. Intermarché/Netto at least 300 (BFM TV); Coopérative U "over 100" (CBS) or 80 (a later company update); Carrefour 80 of about 6,000; Monoprix about 5% of about 490 stores (about 30 per Wikipedia); E.Leclerc "several". The French economy minister later cited about **700 of roughly 10,000** supermarket locations. The film uses "about seven hundred stores, per France's economy minister".
- **Money:** "at least €10 million" (Wikipedia infobox) and "tens of millions" (Wikipedia text) do not agree, and neither is sourced to a loss audit. **Not used in narration.**
- **Equipment:** Danfoss named the **AK-SM800** and **AK-SC355** regulators and said most affected equipment was legacy product no longer receiving security updates, one version on outdated firmware. ANSSI also tied the attack to Copeland and Dixell (XWEB) systems. AK-SC355 reached end-of-life in 2016 and AK-SM800 in May 2021 (Wikipedia).
- **Exposure:** the controllers' web interfaces were reachable from the public internet. Reportedly found with Shodan (medium confidence). Claroty's Censys scan counted **2,765 exposed AK-SM 800A** devices.
- **Known flaws:** Claroty documented a **code-of-the-day authentication bypass** (CVE-2025-41450, CVSS 8.2; the password is checked against a value derived from the device's current date) and a post-authentication command injection (CVE-2025-41451, CVSS 7.6). Fixed in firmware R4.3.1.
- **Not confirmed:** several outlets note it is unclear whether the attackers used these exact flaws. The film says so.
- **Alarms:** early findings say alarms were disabled or the overnight defrost was extended so staff only found out on arrival (medium confidence). The film says "reportedly".
- **Response:** the PM (Sébastien Lecornu) directed ANSSI to investigate and coordinate across Europe. CERT-FR advised removing direct internet access, checking settings including defrost schedules, and installing firmware updates. Investigators found the same flaws in Belgium, Germany, Luxembourg, the Netherlands, Portugal, Poland and Spain (Wikipedia).
- **Second wave:** overnight **Sunday 1 to Monday 2 November 2026** ("around midnight on a Sunday", Sabcobel CEO). Reported in Belgium (Delhaize, Carrefour, Spar), Luxembourg, Sweden (Coop, Ica; reported 50 °C), Ireland (SuperValu: 13 of 223 stores), Estonia, the Netherlands, Finland. Ahold Delhaize and Colruyt confirmed hacks; some retailers said only "technical problems". Vendors for this wave are **not confirmed**.
- **Fix:** Sabcobel says a thorough fix needs both a **software update and physical modification** of the units.
- **Attribution:** none, for either wave. Ken Munro (Pen Test Partners) suggested "kids messing around" given the exploit's ease; state actors have the capability. A US report of Iran-backed hackers hitting military-base freezers was mentioned by TechCrunch and is **not linked to Europe** and not used.
- **Food safety:** the temperature danger zone starts at about 5 °C (Australian authorities; US FDA 41 °F, USDA 40 °F); USDA FSIS says bacteria can double in as little as 20 minutes in the zone. The film says "above five degrees, bacteria multiply fast".
- **Defrost mechanics (general, manufacturer-dependent):** electric defrost heats the evaporator coil to melt frost; a timer starts it, typically for 15-30 minutes every several hours, and a termination thermostat ends it at about 5 °C at the coil. Sourced from patent and parts-supplier pages, so the film says only "a short cycle", never a number.

## Disputed or provisional, so shown that way

| Question | Positions |
| --- | --- |
| How many stores? | 300+ (BFM TV, one chain family) to about 700 (economy minister) of about 10,000 French locations. Film: "about seven hundred, per the economy minister". |
| Were the known Claroty flaws used? | Unconfirmed. Film: "whether that exact flaw was used is unconfirmed". |
| Who did it? | Unknown. No claim of responsibility found. |
| Which vendors in wave 2? | Unconfirmed. Film does not name vendors for wave 2. |
| Defrost duration | "one to eight hours" is one summary; temperatures and hours vary by outlet. Film says "reports say". |

## Deliberately left out

- Financial totals (conflicting, unsourced).
- The Dutch and US website outages at Ahold Delhaize brands: the company said there was no reason to link them to the fridge attacks.
- The US military-base freezer reports and any state attribution.
- The "admin / today's date" password story (Wikipedia only; the Claroty page describes the date-derived code but not this login). Film says "a hidden daily password, built from the date".
- Logos and brand marks. Retailer names appear as plain text only, and only where reporting names them.

## Open items before render

1. Re-check chain counts and the second-wave country list the day of render; reporting is moving.
2. Claroty's page date is ambiguous in the fetch (shows August 2026; CISA advisory numbering implies 2025; Wikipedia says the patch shipped August 2025). The film gives no date for the flaw disclosure beyond "already documented".
3. Open the CISA advisory and CERT-FR bulletin directly and confirm the CVE and firmware wording.
