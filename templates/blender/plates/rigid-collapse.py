"""
Plate template: rigid-collapse. A stack of blocks hit by a falling weight topples under real rigid-body
physics: a system failing, a bubble bursting, dominoes of consequence. The simulation is baked before
rendering, so every frame (and a preview that skips frames) sees the same result.

Params:
  rows, cols     size of the stack                                (default 6, 4)
  block_color    palette role of the blocks                       (default 'paper-2')
  accent_every   every Nth block takes the accent colour          (default 5)
  impact         plate seconds when the weight is released        (cue 'impact' wins; default 0.8)
Cues: 'impact' - the weight starts to fall (snap it to the spoken word).
"""


def build(lab, job):
    rng = lab.rng()
    rows, cols = int(lab.param("rows", 6)), int(lab.param("cols", 4))
    lab.world("paper", strength=0.8)
    ground = lab.floor("paper-2", size=30.0, shadow_catcher=False)
    lab.rigid(ground, kind="PASSIVE", friction=0.9)

    plain = lab.material("block", lab.param("block_color", "paper-2"), roughness=0.55)
    accent = lab.material("block-accent", "accent", roughness=0.4, coat=0.3)
    every = int(lab.param("accent_every", 5))
    size = 0.34
    n = 0
    for r in range(rows):
        for c in range(cols):
            jitter = rng.uniform(-0.015, 0.015)
            x = (c - (cols - 1) / 2) * (size * 2.04) + (size if r % 2 else 0) * 0.5 + jitter
            block = lab.primitive("cube", f"block-{r}-{c}", size=size, location=(x, 0, size + r * size * 2.02),
                                  material=accent if every and n % every == 0 else plain, smooth=False)
            lab.bevel(block, 0.02, 2)
            lab.rigid(block, mass=1.0, friction=0.7, bounce=0.05, shape="BOX")
            n += 1

    impact = lab.cue("impact", float(lab.param("impact", 0.8)))
    weight = lab.primitive("sphere", "weight", size=0.55, location=(-0.6, 0, rows * size * 2.4 + 4.0),
                           material=lab.material("weight", "ink", roughness=0.25, metallic=0.6))
    lab.rigid(weight, mass=25.0, friction=0.5, bounce=0.1, shape="SPHERE")
    # held kinematic (animated) until the impact cue, then handed to the simulation
    weight.rigid_body.kinematic = True
    lab.key(weight.rigid_body, "kinematic", [(0.0, True), (impact, True), (impact + 1.0 / lab.fps, False)], ease="none")

    lab.studio_lights(target=(0, 0, rows * size), scale=1.4, rim="accent-2")
    top = rows * size * 2
    cam = lab.camera(location=(lab.pick(5.5, 3.6, 4.6), -9.5, top * 0.55 + 1.2), target=(0, 0, top * 0.45),
                     fov_short=lab.pick(34, 44, 38))
    lab.key(cam, "location", [(0.0, tuple(cam.location)),
                              (lab.duration, (cam.location[0] * 0.8, -8.4, cam.location[2] * 0.85))], ease="sine.inOut")
