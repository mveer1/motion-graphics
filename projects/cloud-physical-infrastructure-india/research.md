# The Cloud Has an Address: the Delhi data center fire, June 2026

Research dossier (Stage 0R). Sources consulted 2026-11-02. The primary source is Google Cloud's own Service Health incident page; news reports (Reuters via MarketScreener, Inc42, MediaNama, DCD) agree with it.

## What happened (verified)

- A fire at a **third-party data center facility** in Delhi "required an emergency power shutdown of networking equipment, isolating a non-compute local Point of Presence (POP) in Delhi and reducing available network capacity in the metro area." (Google, update of 9 Jun 2026, 18:13 PDT)
- Reported symptoms: **intermittent periods of elevated latency and possible packet loss** for network traffic to Google Cloud originating from **Delhi, Chennai, Mumbai and surrounding areas**.
- Google "rerouted significant traffic from the impacted facility" and warned of "intermittent latency spikes due to demand exceeding capacity across Indian metros and regional ISPs."
- Affected products: Hybrid Connectivity, Media CDN, Virtual Private Cloud (VPC). Location: Delhi (asia-south2).
- Workaround: **none** at the time.

## Recovery timeline (Google updates, US/Pacific)

| Date | Update |
| --- | --- |
| 9 Jun | First public update; mitigations and Internet Edge peering augmentation under way |
| 10-12 Jun | Working with regional ISP partners; planning to augment the Delhi POP and Chennai |
| 15 Jun | Delhi backbone augmented over the weekend |
| 17 Jun | Partial Internet Edge restoration in Delhi; more Delhi-Chennai and Delhi-Mumbai capacity |
| 22 Jun | Large portion of peering restored; Chennai augmentation done; crews accessed the damaged site |
| 29 Jun | Final update: service recovered and returned to normal as of Friday 26 Jun; latency and packet drops still monitored |

## What is not known

- Cause of the fire, when it started, the facility's name and operator, injuries, damage (not disclosed; MediaNama).
- Number of affected users or customers (not disclosed).
- The incident header says it began 2026-06-05, but the first update and all news reports date the event to 9 June. The discrepancy is unexplained, so the film says "June 2026" and does not quote a start date or a duration in days.

## Why a fire means a shutdown (general background)

Data centers usually have an emergency power off (EPO) so firefighters can work without electric shock risk; some standards (NFPA 75) also call for shutting down equipment when gaseous suppression discharges. This is context only; Google's page says an emergency power shutdown happened, not why it was triggered or by what standard (TechTarget).

## Reading of the evidence

The notable point is not that something failed, but how: a **non-compute** network junction in a **third-party** building went dark, traffic **was rerouted**, and the alternate paths were **narrower** than the road they replaced. Redundancy existed; headroom did not. Recovery meant adding capacity, route by route, for about two weeks (9-26 June).

## Visual metaphors

1. **Building on a map**: one glowing building, routes to cities, radial ink ripple (spatial_map_spread).
2. **Narrower detour**: traffic dots bend around the dark node and bunch on thin routes (vector_pulse_flow).
3. **Dated rebuild line**: ticks advance 9 Jun to 26 Jun, routes thicken, node relights (timeline_sequence).

## Words to avoid

"Outage of Google's data center", "all of India", "Google Cloud went down", "caused by" (for the fire), any user or company counts, any logo.
