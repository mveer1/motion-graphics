"""
Plate template: light-shafts. Volumetric haze cut by sheets of light falling through a slatted
ceiling onto a lit subject pillar: revelation, insight, a lab or archive mood, an atmospheric opener
behind a title that HyperFrames sets on top (keep the title band dark: the light falls below it).

Params:
  density      haze density                                  (default 0.035)
  beam_color   palette role of the light                     (default 'accent-3')
  strength     sun strength once revealed                    (default 5.0)
  slats        number of ceiling slats                       (default 9)
  sweep_deg    how far the light swings, degrees             (default 12)
  subject      palette role of the subject                   (default 'accent')
Cues: 'reveal' - the light reaches full strength; default 1.5 s.
"""

import math


def build(lab, job):
    lab.world("ink", strength=0.04)
    lab.fog(density=float(lab.param("density", 0.035)), color="paper", anisotropy=0.55,
            extent=(10.0, 12.0, 3.95), center=(0.0, 0.0, 2.95))  # haze ends just under the ceiling
    lab.floor("ink-2" if "ink-2" in lab.palette else "ink", size=40.0, shadow_catcher=False, roughness=0.6)

    # slatted ceiling, slats along the view axis: the sheets of light are seen edge-on, as diagonal beams
    slats = int(lab.param("slats", 9))
    wall = lab.material("slat", "ink", roughness=0.95)
    for i in range(slats):
        x = (i - (slats - 1) / 2.0) * 1.15 - 2.0
        slat = lab.primitive("cube", f"slat-{i}", size=1.0, location=(x, 2.0, 7.0), material=wall, smooth=False)
        slat.scale = (0.32, 11.0, 0.12)

    subject = lab.primitive("cylinder", "subject", size=0.6, location=(0, 1.0, 1.2),
                            material=lab.material("subject", lab.param("subject", "accent"), roughness=0.35, coat=0.5))
    subject.scale = (1.0, 1.0, 2.0)

    sun = lab.light("SUN", "beam", location=(-10.0, 2.0, 14.0), energy=0.0, color=lab.param("beam_color", "accent-3"),
                    size=0.2, target=(0, 0, 0))
    sun.data.angle = math.radians(0.6)
    reveal = lab.cue("reveal", 1.5)
    lab.key(sun.data, "energy", [(0.0, 0.0), (reveal, float(lab.param("strength", 5.0)))], ease="power2.out")
    sweep = float(lab.param("sweep_deg", 12))
    sy = 8.0 * math.sin(math.radians(sweep))
    lab.key(sun, "location", [(0.0, (-10.0, 2.0 - sy, 14.0)), (lab.duration, (-10.0, 2.0 + sy, 14.0))], ease="sine.inOut")

    lab.light("AREA", "fill", location=(-3.0, -5.0, 2.5), energy=140.0, color="paper", size=5.0, target=(0, 1.0, 1.2))
    cam = lab.camera(location=(0, -9.0, 1.4), target=(0, 1.0, 2.6), fov_short=lab.pick(40, 54, 46), dof_focus=subject, fstop=4.0)
    lab.key(cam, "location", [(0.0, (0, -9.0, 1.4)), (lab.duration, (0, -7.6, 1.5))], ease="sine.inOut")
