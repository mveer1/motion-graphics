# Research: Sparks of Weight-Space Programming

Consulted 2026-11-05. Every on-screen number and narrated claim in this film traces to one of the sources below. The machine-readable dossier is `research.json`.

## The source

- **Primary:** Rikiya Takehi\*, Jayden Teoh\*, Alex Zhang, Omar Khattab (MIT CSAIL). "Sparks of Weight-Space Programming: LLMs can natively read & write neural network weights." Blog post, 2 November 2026. <https://rikiyat.github.io/blog/weight-space-programming/>
- **Logs:** <https://github.com/RikiyaT/lm_understand-logs> (CC BY 4.0 logs, MIT scripts). Used for: the editor is OpenAI's `gpt-6-astra` through the Codex CLI with every built-in tool switched off, and all 1,125 turns were audited tool-free (`README.md`). Also the exact Experiment 8 edit and its 2 × 64 × 1,024 count (`exp8_math/README.md`, `runs/p50c/final_answer.md`, `runs/p50c/work_notes/final_report.md`).
- **Related work cited by the post and used in the film:** Elhage et al. 2021, *A Mathematical Framework for Transformer Circuits*: copying (induction) heads found by composing weight matrices, which Astra re-derived unprompted. Arditi et al. 2024, *Refusal … Mediated by a Single Direction*: the directional-ablation precedent. Young & Tian 2019 (MinAtar). Matthews et al. 2025 (Kinetix).
- **Press:** The Register, 3 November 2026. It quotes no independent experts and reports no replication.

**Status.** This is a blog post with full logs, not a peer-reviewed paper. No independent replication was found as of 2026-11-05. The blog says Hugging Face's Ahsen Khaliq rebuilt the edited Qwen from the logs and re-ran its evaluation.

## What the study claims (and what it does not)

Definition, quoted from the post: *"In Weight-Space Programming, a general-purpose LLM reads and writes a network's weights directly (i.e., not through an optimizer, and in particular not with gradient descent) around some natural language spec, sometimes even with no environment feedback at all."*

| # | Task | Setting | Result |
|---|---|---|---|
| 1 | Which game? 4 PPO policies, MLP 500→32→32→5, 17,253 weights | no tools, no options given | all 4 named. Clue: Breakout's agent-channel weights lie along the bottom row (a paddle) |
| 2 | Which shape does a DDPM draw? 23,824 weights | no tools, no forward pass | all 3 right, but drawn as outlines (the models make filled shapes) |
| 3 | Which language? 4×6-head char transformer, input and output layers removed | Python analysis, no running | all 3 right in both attempts. Every copying head found (Python 2.1, 3.1, 3.5), no false ones |
| 4 | Fix a car stuck on a ramp, 171,664 weights | one reply, no tools | 0/256 → 1,024/1,024. 3.5% of weights changed |
| 5 | Write MinAtar players from all-zero weights, 600→32→32→6 | no data, loss, gradients, tools or rollouts | Breakout 517.4 vs PPO-100M 15.8 and PPO-500M 25.3. Seaquest 53.1 vs 5.6 / 88.9. Asterix 53.2 vs 25.8 / 55.2 |
| 6 | Write a 9×9 Go player, 1,480,274 weights | Python sandbox, 0 to 50 forward passes | 0 passes: wins more than half its games vs two small PPO nets. 50 passes: beats the equal-sized PPO net trained on 20M games |
| 7 | Which Gemma 3 270M copy is sycophantic? | weights only, then an attention tool | **failed** from weights (4 attempts). With attention patterns: 3/3. Head 10.2: honest 94.3% on the question's numbers, sycophant 85.7% on the user's answer |
| 8 | Make Qwen3.5-0.8B better at math | Python kernel, 10/25/50 forward passes, practice sets only | 50 passes: MATH-500 7.9 → 48.1, GSM8K 13.8 → 67.1, IFEval 21.0 → 62.3, token-limit hits 93.0 → 33.1 (%) |
| + | Same for Gemma 3 270M (rarely loops) | same | **no gain**: 6.8 → at most 7.7 |

### Experiment 8 in detail (the film's longest chapter)

- **Failure:** 85 of the base model's first 96 practice answers ran to the 32,768-token limit, about 95% of them with duplicated tail phrases.
- **Diagnosis:** a unit "repetition direction" `u` in the residual stream, measured from matched looping and productive contexts. It is written mostly by the MLPs (`down_proj`) of layers 15 and 19.
- **Edit (run p50c):** `W = W0 − 6·outer(u, mask64 ⊙ (uᵀW0))`. For each of the 64 selected columns `c` (neurons) per layer, `w_c ← w_c − 6 (u·w_c) u`, so the column now writes against the loop direction. That is 2 × 64 × 1,024 = 131,072 weights, 0.016% of 0.8 billion.
- **Control (Astra's own, on held-out practice problems):** a norm-matched orthogonal random direction gave +1.56 points (SE 3.52), against +49.8 for the targeted edit on 1,152 problems (579 rescued, 5 regressed).
- **Interpretation, from the post:** fixing loops lets the model finish answers it could already work out. *"Editing weights could remove an obstacle that hid an ability, but it could not add an ability the model lacked."*

## Accuracy guardrails for the script

- Never say "trained" or "fine-tuned" for Astra's edits.
- Don't say Qwen became "smarter". Say the loops were removed.
- Mark the tool-assisted experiments (3, 6, 7, 8) apart from the tool-free ones (1, 2, 4, 5).
- Label the random-direction control as practice-set data and Astra's own check.
- Say "blog post, not peer-reviewed" and "the models are small" (largest 0.8B).
- The post's forward-looking ideas (auditing without evaluation, zero-data unlearning, avoiding catastrophic forgetting, recursive self-improvement, model grafting) are proposals, not results. The film mentions none of them as achieved.

## Pronunciation

MIT CSAIL is said "M I T see-sail", GPT-6 Astra "G P T six Astra", Qwen "Kwen", PPO "P P O", MLP "M L P" and MATH-500 "Math five hundred".
