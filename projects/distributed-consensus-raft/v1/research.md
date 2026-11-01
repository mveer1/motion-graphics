# Stage 0 Research Dossier: How Does Raft Reach Consensus?

> **Topic ID:** `distributed-consensus-raft`  
> **Domain:** `distributed_systems` | **Difficulty:** `intermediate`  
> **Target Duration:** 25.0s (Range: 22.0s – 28.0s)  
> **Canonical Source:** Diego Ongaro, John Ousterhout, *In Search of an Understandable Consensus Algorithm* (2014, USENIX ATC).

---

## 1. Pedagogical Scope & Objectives

### 1.1 The Core Problem
In distributed systems, independent servers must agree on an ordered log of state transitions even when individual nodes crash, restart, or network packets are delayed or reordered.

### 1.2 Central Thesis & Mental Model
- **Central Thesis:** Raft solves consensus by electing a distinguished leader who assumes sole responsibility for managing an append-only replicated log across a majority quorum.
- **Mental Model:** A parliamentary body that elects a chairperson; decisions only become binding law once signed by a strict majority ($N/2 + 1$).
- **Key Takeaway:** Consensus requires a stable leader and majority log commitment.

### 1.3 Verified Mechanical Claims
1. **Election Safety:** At most one leader can be elected in any given term.
2. **Leader Append-Only:** A leader never overwrites or truncates its own entries; it only appends.
3. **Log Matching:** If two logs contain an entry with the same index and term, they are identical up to that point.
4. **Majority Commitment:** An entry is committed as soon as a majority quorum of servers stores it.

---

## 2. Technical Ground Truth & Mathematical Formulations

### 2.1 Core Entities & Variables
| Symbol | Name | Domain / Type | Functional Role |
|---|---|---|---|
| `$S$` | Server Cluster | $\{S_1, \dots, S_N\}$ | Set of distributed nodes |
| `$t$` | Term Number | $\mathbb{N}$ | Logical epoch counter detecting stale leaders |
| `$Q$` | Quorum Bound | $\lfloor N/2 \rfloor + 1$ | Strict majority threshold |
| `$e$` | Log Entry | $(t, i, \text{cmd})$ | Replicated transaction tuple |

### 2.2 Mathematical Equations
$$V_{\text{votes}} \ge \left\lfloor \frac{N}{2} \right\rfloor + 1$$
- **Spoken Form:** *"Votes received must meet or exceed a majority quorum of the cluster."*
- **Context:** Guarantees that any two quorums overlap in at least one server, preventing split-brain.

$$T_{\text{timeout}} \sim U(150\text{ms}, 300\text{ms})$$
- **Spoken Form:** *"Randomized election timeouts prevent split-vote deadlocks."*

---

## 3. Visual Metaphor & Spatial Choreography

| Concept ID | Visual Archetype | SVG Primitives | Spatial Anchor | Motion Pattern | Color Token |
|---|---|---|---|---|---|
| `cluster_topology` | `node_network_graph` | `<circle>`, `<line>` | `canvas_center` | Pentagon ring with status borders | `accent_primary_blue` |
| `leader_authority` | `state_machine_transition` | `<circle>`, `<text>` | `canvas_center` | Node turns glowing amber with crown tag | `warning_amber` |
| `heartbeat_wave` | `vector_pulse_flow` | `<circle>` | `canvas_center` | Concentric ripple rings broadcasting outward | `accent_secondary_teal` |
| `quorum_commitment` | `ring_buffer_pipeline` | `<rect>`, `<text>` | `bottom_dock_timeline` | Log slots turn from amber to emerald green | `state_active_emerald` |

---

## 4. Acoustic & Phonetic Guidance
- **Recommended Voice:** `am_adam`
- **Speech Rate:** `1.15` (20% faster)
- **Inter-Scene Pause Buffer:** `0.5s`

### Phonetic Lexicon
| Term | Phonetic Respelling | Rationale |
|---|---|---|
| `quorum` | `KWOR-um` | Ensures clean Latinate articulation in Kokoro |
| `RPC` | `R-P-C` | Acronym pronunciation |
| `Raft` | `raft` | Clear noun |

---

## 5. Scene Blueprint & Narration Draft
1. **Scene 1 (s1): The Consensus Problem ($t = 0.0\text{s} \to 6.2\text{s}$)**
   - *Narration:* "In distributed systems, independent servers must agree on a single shared state, even when nodes fail."
2. **Scene 2 (s2): Leader Election ($t = 6.7\text{s} \to 13.0\text{s}$)**
   - *Narration:* "Raft solves this by electing a leader. If a node times out, it requests votes until it wins a majority quorum."
3. **Scene 3 (s3): Log Replication ($t = 13.5\text{s} \to 19.8\text{s}$)**
   - *Narration:* "The leader accepts client commands and broadcasts them across the cluster through heartbeat messages."
4. **Scene 4 (s4): Quorum Commitment ($t = 20.3\text{s} \to 25.5\text{s}$)**
   - *Narration:* "Once a majority of followers acknowledge the entry, it commits permanently. The cluster reaches consensus."
