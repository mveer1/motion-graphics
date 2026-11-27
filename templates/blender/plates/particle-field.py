"""
Plate template: particle-field. A seeded field of glowing motes drifting through depth with a slow
camera push and shallow focus: data as stars, a swarm, dust in light, a population. Pair it with
HyperFrames labels or counters above it.

Params:
  count        number of motes                                  (default 700)
  colors       palette roles the motes cycle through            (default ['accent', 'accent-3', 'accent-2'])
  glow         emission strength                                (default 6.0)
  push         how far the camera travels forward, metres       (default 3.0)
  background   palette role for the world                       (default 'ink')
Cues: 'gather' (seconds) - motes start to pull toward the centre; default: no gathering.

Every position comes from lab.rng(), so the same plan renders the same field on every host.
"""

import math


def build(lab, job):
    rng = lab.rng()
    count = int(lab.param("count", 700))
    roles = lab.param("colors", ["accent", "accent-3", "accent-2"])
    glow = float(lab.param("glow", 6.0))
    lab.world(lab.param("background", "ink"), strength=0.25)

    mats = [lab.emissive(f"mote-{i}", role, glow) for i, role in enumerate(roles)]
    protos = []
    for i, mat in enumerate(mats):
        proto = lab.primitive("ico", f"mote-proto-{i}", size=1.0, subdivisions=2, material=mat)
        proto.hide_render = True
        protos.append(proto)

    # instances: linked duplicates of the prototypes, placed from the seeded stream
    motes = []
    spread_x = lab.pick(9.0, 5.5, 7.0)
    spread_z = lab.pick(5.0, 9.0, 7.0)
    for i in range(count):
        proto = protos[i % len(protos)]
        ob = proto.copy()
        ob.hide_render = False
        lab.scene.collection.objects.link(ob)
        x = rng.uniform(-spread_x, spread_x)
        y = rng.uniform(-2.0, 14.0)
        z = rng.uniform(-spread_z, spread_z) + 2.0
        s = 0.012 + rng.random() ** 3 * 0.05
        ob.location = (x, y, z)
        ob.scale = (s, s, s)
        motes.append((ob, (x, y, z), rng.uniform(0, math.tau), rng.uniform(0.15, 0.45)))

    gather = (job.get("cues") or {}).get("gather")

    def drift(t):
        pull = 0.0
        if gather is not None and t > gather:
            u = min(1.0, (t - gather) / max(0.5, lab.duration - gather))
            pull = 1 - (1 - u) ** 3
        for ob, (x, y, z), phase, amp in motes:
            dx = math.sin(phase + t * 0.6) * amp
            dz = math.cos(phase * 1.3 + t * 0.45) * amp
            px, pz = x + dx, z + dz
            ob.location = (px * (1 - 0.85 * pull), y, 2.0 + (pz - 2.0) * (1 - 0.85 * pull))

    lab.on_frame(drift)

    push = float(lab.param("push", 3.0))
    cam = lab.camera(location=(0, -9.0, 2.0), target=(0, 6.0, 2.0), fov_short=lab.pick(42, 55, 48),
                     dof_focus=5.0 + push, fstop=1.8)
    lab.key(cam, "location", [(0.0, (0, -9.0, 2.0)), (lab.duration, (0, -9.0 + push, 2.0))], ease="sine.inOut")
