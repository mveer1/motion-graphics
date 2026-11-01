# Stage 0 Research Dossier: How Does a Neural Network Learn?

> **Topic:** Neural Network Learning Mechanics (Forward Pass, Loss Function, Backpropagation & Gradient Descent)  
> **Target Audience:** Technical & Scientific Practitioners (Engineers, Data Scientists, Students)  
> **Output Deliverable:** 25–30s Motion Graphics Explainer (1280×720 @ 30fps)

---

## 1. Pedagogical Scope & Objectives

The goal is to demystify neural network training in under 30 seconds by presenting the core mechanical feedback loop:
1. **Prediction (Forward Pass):** Data propagation through affine transformations and activation layers.
2. **Error Evaluation (Loss):** Quantifying discrepancy between model prediction and ground truth.
3. **Parameter Adaptation (Backpropagation & Gradient Descent):** Propagating error gradients backward to update synaptic weights.
4. **Convergence:** Iterative descent leading to error minimization.

---

## 2. Technical Ground Truth & Mathematical Foundations

### 2.1 The Forward Pass
For layer $l \in \{1, \dots, L\}$:
$$z^{[l]} = W^{[l]} a^{[l-1]} + b^{[l]}$$
$$a^{[l]} = \sigma(z^{[l]})$$
where:
- $a^{[0]} = x$ (input feature vector).
- $W^{[l]}$ is the weight matrix connecting layer $l-1$ to $l$.
- $b^{[l]}$ is the bias offset.
- $\sigma$ is a non-linear activation function (e.g., ReLU or Sigmoid).

### 2.2 The Loss Metric (Discrepancy)
For a single prediction $\hat{y} = a^{[L]}$ and ground truth $y$, the loss $L$ measures discrepancy:
$$L(\hat{y}, y) = \frac{1}{2} \|\hat{y} - y\|^2 \quad \text{(Mean Squared Error)}$$

### 2.3 Gradient Descent & Weight Updates
Weights are adjusted opposite to the gradient of the loss surface:
$$W^{[l]} \leftarrow W^{[l]} - \eta \frac{\partial L}{\partial W^{[l]}}$$
where:
- $\eta > 0$ represents the learning rate.
- $\frac{\partial L}{\partial W^{[l]}}$ is computed analytically via the chain rule (backpropagation).

---

## 3. Visual Metaphor & Motion Mapping

To avoid visual clutter and cognitive fatigue, abstract mathematical mechanics are mapped to clear 2D vector primitives:

| Technical Concept | Visual Representation | GSAP Animation Behavior |
|---|---|---|
| **Input Vector ($x$)** | Glowing input nodes with floating feature labels | Staggered entrance, pulsing glow ($1.0 \to 1.15$ scale) |
| **Synaptic Weights ($W$)** | Directed connection lines between node layers | Stroke opacity and thickness vary with weight magnitude |
| **Forward Information Flow** | Signal packets / light pulses traversing connections | Path stroke-dashoffset animation traveling left-to-right |
| **Prediction vs. Truth ($\hat{y}$ vs $y$)** | Output node emitting predicted vector compared against target beacon | Target marker appears; discrepancy bracket highlights $\Delta$ |
| **Loss ($L$)** | Convex loss basin curve with marker | Point slides down the gradient slope toward the global minimum |
| **Backpropagation ($\nabla L$)** | Reverse color pulse (warm coral/red) flowing right-to-left | Reverse stroke illumination traversing back through hidden layers |
| **Convergence** | Loss curve asymptotically approaching zero | Metric counter eases downward; final checkmark/stabilization pulse |

---

## 4. Domain Glossary & Phonetic Respellings

All technical terminology is cross-referenced with `.agents/skills/voice-director/references/phonetics.md` for Kokoro TTS synthesis:

| Technical Term | IPA / Phonetic Respelling | Context / Usage |
|---|---|---|
| **Neural Network** | `NYOOR-ul NET-wurk` | Overall system architecture |
| **Loss** | `LAWS` | Scalar discrepancy value |
| **Gradient** | `GRAY-dee-unt` | Vector of partial derivatives |
| **Weights** | `WAYTS` | Adjustable parameters |
| **Backpropagation** | `BACK-prah-puh-GAY-shun` | Reverse error propagation |

---

## 5. Storyboard & Scene Breakdown

1. **Scene 1 (s1): The Problem & Premise ($t = 0.0\text{s} - 6.5\text{s}$)**
   - *Narration:* "A neural network is a system that learns from examples. Given an input, it produces a prediction."
   - *Visual:* Clean grid, input node excitation, initial prediction emission.
2. **Scene 2 (s2): Forward Information Flow ($t = 7.0\text{s} - 13.5\text{s}$)**
   - *Narration:* "Information flows forward through layers of connected nodes, each applying a simple transformation."
   - *Visual:* Multi-layer bipartite graph; signal pulses travel left-to-right across connections.
3. **Scene 3 (s3): Error Measurement & Weight Adaptation ($t = 14.0\text{s} - 21.5\text{s}$)**
   - *Narration:* "The network compares its prediction to the correct answer. The difference — the loss — tells it how to adjust every weight."
   - *Visual:* Discrepancy bracket appears; reverse gradient pulse fires right-to-left; weights thicken/thin.
4. **Scene 4 (s4): Convergence & Mastery ($t = 22.0\text{s} - 27.5\text{s}$)**
   - *Narration:* "Repeat this across many examples, and the loss falls. The network learns."
   - *Visual:* Loss curve with descending point, error reaches minimum, network glows in coherent synchronized state.

