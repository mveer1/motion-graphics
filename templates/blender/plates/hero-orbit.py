"""
Plate template: hero-orbit. A hero object on a soft studio set, the camera arcing slowly around it
with real depth of field. The workhorse for "show the thing": a product, a device, a crystal, a cell.

Params (plan `params`):
  shape        'torus' | 'ico' | 'sphere' | 'cube' | 'cylinder' | 'cone'   (default 'torus')
  material     'glass' | 'satin' | 'metal' | 'clay'                       (default 'satin')
  color        palette role for the object                                (default 'accent')
  arc_deg      how far the camera travels, degrees                        (default 40)
  spin_deg     how far the object turns on its own axis, degrees          (default 25)
  set_color    palette role of the seamless studio sweep                 (default 'paper-2')
  subject_y    lift the hero by this fraction of the frame height        (default: landscape 0, portrait 0.2, square 0.1)
  behind       palette roles of bars standing behind the hero, so glass shows its refraction (default none)
Cues: 'settle' (seconds) - the object finishes its rise; default 1.2 s.

On an alpha plate the studio sweep becomes a shadow catcher in Cycles and is hidden in EEVEE.
"""

import math


def build(lab, job):
    shape = lab.param("shape", "torus")
    finish = lab.param("material", "satin")
    role = lab.param("color", "accent")

    lab.world("paper", strength=0.6)
    lab.cyclorama(lab.param("set_color", "paper-2"))

    if finish == "glass":
        mat = lab.glass("hero-glass", tint="paper", ior=1.5)
    elif finish == "metal":
        mat = lab.material("hero-metal", role, roughness=0.22, metallic=1.0)
    elif finish == "clay":
        mat = lab.material("hero-clay", role, roughness=0.85)
    else:
        mat = lab.material("hero-satin", role, roughness=0.32, coat=0.4)

    # glass needs something behind it to bend: optional coloured bars the camera sees through the hero
    behind = lab.param("behind") or []
    for i, bar_role in enumerate(behind):
        x = (i - (len(behind) - 1) / 2.0) * 0.42
        bar = lab.primitive("cube", f"behind-{i}", size=1.0, location=(x, 2.6, 1.6),
                            material=lab.material(f"behind-{i}", bar_role, roughness=0.6), smooth=False)
        bar.scale = (0.16, 0.05, 1.6)

    hero = lab.primitive(shape, "hero", size=1.0, location=(0, 0, 1.25), material=mat)
    if shape == "torus":
        hero.rotation_euler = (math.radians(62), 0, 0)
    if shape == "cube":
        lab.bevel(hero, 0.08, 5)

    settle = lab.cue("settle", 1.2)
    lab.key(hero, "location", [(0.0, (0, 0, 0.85)), (settle, (0, 0, 1.25))], ease="expo.out")
    base_rot = tuple(hero.rotation_euler)
    spin = math.radians(lab.param("spin_deg", 25))
    lab.key(hero, "rotation_euler", [(0.0, base_rot), (lab.duration, (base_rot[0], base_rot[1], base_rot[2] + spin))],
            ease="sine.inOut")

    lab.studio_lights(target=(0, 0, 1.2), key="paper", rim=lab.param("rim", "accent-3"))

    arc = lab.param("arc_deg", 40)
    cam = lab.camera(location=(0, -7, 2.4), target=(0, 0, 1.15), fov_short=lab.pick(30, 40, 34),
                     dof_focus=hero, fstop=2.2, subject_y=lab.param("subject_y", lab.pick(0.0, 0.2, 0.1)))
    lab.orbit(cam, center=(0, 0, 0), radius=7.0, height=2.4, start_deg=-90 - arc / 2, end_deg=-90 + arc / 2,
              ease="sine.inOut")
