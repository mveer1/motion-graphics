"""
Motion Lab Blender plate kit (runs inside Blender, `bpy`).

A plate script defines `build(lab, job)` and builds its scene through this object. The kit keeps
Blender plates consistent with the HyperFrames runtime:

- time is film seconds relative to the plate start (`lab.f(t)` -> frame), never raw frames;
- easing uses GSAP names (`'expo.out'`, `'sine.inOut'`), mapped to Blender interpolation;
- colours are palette roles from the project's style sheet (`lab.color('accent')`), sRGB hex in the
  sheet, converted to Blender's scene-linear space here;
- the camera is framed on the short side of the frame, like `--u`, so one script frames every
  format (`lab.camera(fov_short=...)`, `lab.pick(landscape=..., portrait=..., square=...)`);
- randomness comes only from `lab.rng()` (seeded from the plate), never `random.random()`;
- no text: words, numbers and labels belong to the HyperFrames layer above the plate.

Canonical copy: src/blender/mlab.py. Tested against Blender 5.2 LTS.
"""

import math
import random
import zlib

import bpy

# GSAP ease family -> Blender keyframe interpolation
_EASE_FAMILIES = {
    "none": "LINEAR", "linear": "LINEAR",
    "sine": "SINE", "power1": "QUAD", "quad": "QUAD", "power2": "CUBIC", "cubic": "CUBIC",
    "power3": "QUART", "quart": "QUART", "power4": "QUINT", "quint": "QUINT", "strong": "QUINT",
    "expo": "EXPO", "circ": "CIRC", "back": "BACK", "elastic": "ELASTIC", "bounce": "BOUNCE",
}
_EASE_DIRECTIONS = {"in": "EASE_IN", "out": "EASE_OUT", "inout": "EASE_IN_OUT"}


def ease_to_blender(ease):
    """'expo.out' -> ('EXPO', 'EASE_OUT'); 'none' -> ('LINEAR', 'AUTO'); unknown families raise."""
    ease = (ease or "power2.out").strip().lower()
    family, _, direction = ease.partition(".")
    if family not in _EASE_FAMILIES:
        raise ValueError(f"unknown ease '{ease}' (use a GSAP name such as 'expo.out' or 'sine.inOut')")
    interp = _EASE_FAMILIES[family]
    if interp == "LINEAR":
        return interp, "AUTO"
    return interp, _EASE_DIRECTIONS.get(direction or "out", "EASE_OUT")


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_to_linear(value, alpha=1.0):
    """'#E05A47' or 'rgba(217, 164, 65, 0.42)' -> linear (r, g, b, a)."""
    v = value.strip()
    if v.startswith("rgb"):
        parts = [p.strip() for p in v[v.index("(") + 1:v.rindex(")")].split(",")]
        r, g, b = (float(p) / 255.0 for p in parts[:3])
        a = float(parts[3]) if len(parts) > 3 else alpha
        return (srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b), a)
    v = v.lstrip("#")
    if len(v) == 3:
        v = "".join(ch * 2 for ch in v)
    r, g, b = (int(v[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    return (srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b), alpha)


def _set_input(node, names, value):
    """Set the first socket that exists among `names` (socket names change between Blender versions)."""
    for name in names if isinstance(names, (list, tuple)) else [names]:
        sock = node.inputs.get(name)
        if sock is not None:
            sock.default_value = value
            return True
    return False


def _fcurves(idb):
    """F-curves of an ID's action on both the slotted (4.4+/5.x) and the legacy action API."""
    ad = getattr(idb, "animation_data", None)
    if not ad or not ad.action:
        return []
    act = ad.action
    try:
        from bpy_extras import anim_utils
        bag = anim_utils.action_get_channelbag_for_slot(act, ad.action_slot)
        if bag is not None:
            return list(bag.fcurves)
    except (ImportError, AttributeError):
        pass
    return list(getattr(act, "fcurves", []))


def _ease_value(u, interp, easing):
    """GSAP-like ease curves for sampled paths (orbit)."""
    if interp == "LINEAR":
        return u
    if interp == "SINE":
        def f_in(x):
            return 1 - math.cos(x * math.pi / 2)
    elif interp == "EXPO":
        def f_in(x):
            return 0.0 if x == 0 else 2 ** (10 * (x - 1))
    elif interp == "CIRC":
        def f_in(x):
            return 1 - math.sqrt(max(0.0, 1 - x * x))
    else:
        power = {"QUAD": 2, "CUBIC": 3, "QUART": 4, "QUINT": 5}.get(interp, 2)

        def f_in(x):
            return x ** power
    if easing == "EASE_IN":
        return f_in(u)
    if easing == "EASE_OUT":
        return 1 - f_in(1 - u)
    return f_in(2 * u) / 2 if u < 0.5 else 1 - f_in(2 * (1 - u)) / 2


class Lab:
    def __init__(self, job):
        self.job = job
        self.fps = int(job["fps"])
        self.duration = float(job["duration_sec"])
        self.frames = max(1, int(round(self.duration * self.fps)))
        self.width = int(job["width"])
        self.height = int(job["height"])
        self.format = job.get("format", "landscape")
        self.alpha = bool(job.get("alpha"))
        self.palette = dict(job.get("palette") or {})
        self.seed = int(job.get("seed", zlib.crc32(job.get("plate", "plate").encode()) & 0x7FFFFFFF))
        self.scene = bpy.context.scene

    # ------------------------------------------------------------------ time, format, randomness
    def f(self, t):
        """Plate-relative seconds -> Blender frame (frame 1 is t = 0)."""
        return 1 + int(round(float(t) * self.fps))

    def cue(self, name, default=0.0):
        """A named moment from the plan's cues (plate-relative seconds)."""
        return float((self.job.get("cues") or {}).get(name, default))

    def pick(self, landscape=None, portrait=None, square=None):
        """Per-format value, like Studio.pick: falls back to landscape."""
        val = {"landscape": landscape, "portrait": portrait, "square": square}.get(self.format)
        return landscape if val is None else val

    @property
    def aspect(self):
        return self.width / float(self.height)

    def rng(self, salt=0):
        """Seeded random.Random for this plate; `salt` gives independent streams."""
        return random.Random((self.seed * 1000003 + int(salt)) & 0x7FFFFFFF)

    def param(self, name, default=None):
        return (self.job.get("params") or {}).get(name, default)

    # ------------------------------------------------------------------ colour and materials
    def color(self, role_or_hex, alpha=1.0):
        """Palette role ('accent', 'paper', 'ink', 'accent-2', ...) or a hex string -> linear RGBA."""
        value = self.palette.get(role_or_hex, role_or_hex)
        if not isinstance(value, str) or not (value.startswith("#") or value.startswith("rgb")):
            raise KeyError(f"unknown palette role '{role_or_hex}' (known: {', '.join(sorted(self.palette))})")
        return hex_to_linear(value, alpha)

    def material(self, name, color="accent", roughness=0.45, metallic=0.0, transmission=0.0, ior=1.45,
                 emission=None, emission_strength=0.0, coat=0.0):
        mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        if hasattr(mat, "use_nodes") and not mat.use_nodes:
            mat.use_nodes = True
        bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf is None:
            bsdf = mat.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
            out = next(n for n in mat.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
            mat.node_tree.links.new(bsdf.outputs[0], out.inputs[0])
        _set_input(bsdf, "Base Color", self.color(color))
        _set_input(bsdf, "Roughness", float(roughness))
        _set_input(bsdf, "Metallic", float(metallic))
        _set_input(bsdf, ["Transmission Weight", "Transmission"], float(transmission))
        _set_input(bsdf, "IOR", float(ior))
        _set_input(bsdf, ["Coat Weight", "Clearcoat"], float(coat))
        if emission is not None:
            _set_input(bsdf, ["Emission Color", "Emission"], self.color(emission))
            _set_input(bsdf, "Emission Strength", float(emission_strength))
        if transmission > 0:
            # EEVEE (4.2+) refracts only with ray-traced refraction on the material and ray tracing on the scene
            for attr, value in (("use_raytrace_refraction", True), ("use_screen_refraction", True),
                                ("surface_render_method", "DITHERED"), ("thickness_mode", "SPHERE")):
                if hasattr(mat, attr):
                    setattr(mat, attr, value)
            if hasattr(self.scene.eevee, "use_raytracing"):
                self.scene.eevee.use_raytracing = True
        return mat

    def glass(self, name="glass", tint="paper", roughness=0.02, ior=1.45):
        return self.material(name, color=tint, roughness=roughness, transmission=1.0, ior=ior)

    def emissive(self, name, color="accent-3", strength=4.0):
        return self.material(name, color=color, emission=color, emission_strength=strength, roughness=0.6)

    def assign(self, obj, mat):
        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)
        return obj

    # ------------------------------------------------------------------ geometry
    def _link(self, obj):
        self.scene.collection.objects.link(obj)
        return obj

    def mesh_object(self, name, verts, faces, edges=()):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata([tuple(v) for v in verts], list(edges), [tuple(f) for f in faces])
        mesh.update()
        return self._link(bpy.data.objects.new(name, mesh))

    def primitive(self, kind, name=None, size=1.0, location=(0, 0, 0), rotation=(0, 0, 0), material=None,
                  smooth=True, segments=48, subdivisions=3):
        """'sphere' | 'ico' | 'cube' | 'cylinder' | 'cone' | 'torus' | 'plane', built with bmesh (no operator context)."""
        import bmesh
        bm = bmesh.new()
        if kind == "sphere":
            bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=max(8, segments // 2), radius=size)
        elif kind == "ico":
            bmesh.ops.create_icosphere(bm, subdivisions=subdivisions, radius=size)
        elif kind == "cube":
            bmesh.ops.create_cube(bm, size=size * 2)
        elif kind == "cylinder":
            bmesh.ops.create_cone(bm, cap_ends=True, segments=segments, radius1=size, radius2=size, depth=size * 2)
        elif kind == "cone":
            bmesh.ops.create_cone(bm, cap_ends=True, segments=segments, radius1=size, radius2=0.0, depth=size * 2)
        elif kind == "plane":
            bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=size)
        elif kind == "torus":
            major, minor = size, size * 0.32
            ring, tube = segments, max(12, segments // 2)
            verts = []
            for i in range(ring):
                a = 2 * math.pi * i / ring
                for j in range(tube):
                    b = 2 * math.pi * j / tube
                    r = major + minor * math.cos(b)
                    verts.append(bm.verts.new((r * math.cos(a), r * math.sin(a), minor * math.sin(b))))
            for i in range(ring):
                for j in range(tube):
                    a, b = i * tube + j, ((i + 1) % ring) * tube + j
                    c, d = ((i + 1) % ring) * tube + (j + 1) % tube, i * tube + (j + 1) % tube
                    bm.faces.new((verts[a], verts[b], verts[c], verts[d]))
        else:
            raise ValueError(f"unknown primitive '{kind}'")
        mesh = bpy.data.meshes.new(name or kind)
        bm.to_mesh(mesh)
        bm.free()
        if smooth:
            for poly in mesh.polygons:
                poly.use_smooth = True
        obj = self._link(bpy.data.objects.new(name or kind, mesh))
        obj.location = location
        obj.rotation_euler = rotation
        if material is not None:
            self.assign(obj, material)
        return obj

    def bevel(self, obj, width=0.04, segments=4):
        mod = obj.modifiers.new("bevel", "BEVEL")
        mod.width, mod.segments, mod.limit_method = width, segments, "ANGLE"
        return mod

    def floor(self, color="paper", size=40.0, z=0.0, shadow_catcher=None, roughness=0.8):
        """Ground plane. On an alpha plate it becomes a Cycles shadow catcher (EEVEE has none, so it is hidden)."""
        obj = self.primitive("plane", "floor", size=size, location=(0, 0, z),
                             material=self.material("floor", color, roughness))
        catcher = self.alpha if shadow_catcher is None else shadow_catcher
        if catcher:
            if self.scene.render.engine == "CYCLES":
                obj.is_shadow_catcher = True
            else:
                obj.hide_render = True
        return obj

    def cyclorama(self, color="paper-2", width=48.0, depth=14.0, radius=5.0, height=16.0, back=11.0, roughness=0.85):
        """Seamless studio sweep: floor curving up into a back wall, so no horizon line shows in any format.
        On an alpha plate it behaves like floor(): a Cycles shadow catcher, hidden in EEVEE."""
        profile = [(-depth, 0.0), (back - radius, 0.0)]
        for i in range(1, 13):
            a = math.pi / 2 * i / 12
            profile.append((back - radius + radius * math.sin(a), radius - radius * math.cos(a)))
        profile.append((back, height))
        half = width / 2.0
        verts = [(x, y, z) for (y, z) in profile for x in (-half, half)]
        faces = [(2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2) for i in range(len(profile) - 1)]
        obj = self.mesh_object("cyclorama", verts, faces)
        for poly in obj.data.polygons:
            poly.use_smooth = True
        self.assign(obj, self.material("cyclorama", color, roughness))
        if self.alpha:
            if self.scene.render.engine == "CYCLES":
                obj.is_shadow_catcher = True
            else:
                obj.hide_render = True
        return obj

    # ------------------------------------------------------------------ light, world, camera
    def world(self, color="paper", strength=1.0):
        world = bpy.data.worlds.new("mlab-world")
        self.scene.world = world
        if hasattr(world, "use_nodes") and not world.use_nodes:
            world.use_nodes = True
        bg = next((n for n in world.node_tree.nodes if n.type == "BACKGROUND"), None)
        if bg is not None:
            _set_input(bg, "Color", self.color(color))
            _set_input(bg, "Strength", float(strength))
        return world

    def light(self, kind="AREA", name="light", location=(4, -4, 6), energy=600.0, color="paper", size=3.0,
              target=None):
        data = bpy.data.lights.new(name, type=kind)
        data.energy = float(energy)
        data.color = self.color(color)[:3]
        if kind == "AREA":
            data.size = float(size)
        elif kind in ("POINT", "SPOT"):
            data.shadow_soft_size = float(size) * 0.25
        obj = self._link(bpy.data.objects.new(name, data))
        obj.location = location
        if kind != "SUN" or target is not None:
            self.aim(obj, target or (0, 0, 0))
        return obj

    def studio_lights(self, target=(0, 0, 0.8), scale=1.0, key="paper", rim="accent-3", strength=1.0):
        """Soft three-point rig: warm key, fill, coloured rim. Returns (key, fill, rim)."""
        s, e = float(scale), float(strength)
        return (
            self.light("AREA", "key", (4.5 * s, -4.0 * s, 5.5 * s), 340 * e * s * s, key, 4.0 * s, target),
            self.light("AREA", "fill", (-5.0 * s, -3.0 * s, 2.5 * s), 80 * e * s * s, "paper", 6.0 * s, target),
            self.light("AREA", "rim", (0.5 * s, 5.5 * s, 4.0 * s), 420 * e * s * s, rim, 2.5 * s, target),
        )

    def aim(self, obj, target):
        """Point obj's -Z at a location or an object (a Track To constraint, so it follows animation)."""
        con = obj.constraints.get("aim") or obj.constraints.new("TRACK_TO")
        con.name = "aim"
        if isinstance(target, bpy.types.Object):
            con.target = target
        else:
            empty = bpy.data.objects.new(f"{obj.name}-target", None)
            empty.location = target
            self._link(empty)
            con.target = empty
        con.track_axis, con.up_axis = "TRACK_NEGATIVE_Z", "UP_Y"
        return con

    def camera(self, location=(0, -8, 3), target=(0, 0, 1), fov_short=38.0, dof_focus=None, fstop=2.8,
               name="camera", subject_y=0.0):
        """Camera whose field of view `fov_short` (degrees) spans the frame's short side in every format.

        subject_y moves the aimed subject up (+) or down (-) by that fraction of the frame height with a lens
        shift (no perspective change), so the hero lands in the zone the HyperFrames layout leaves free."""
        data = bpy.data.cameras.new(name)
        data.sensor_fit = "VERTICAL" if self.width >= self.height else "HORIZONTAL"
        data.angle = math.radians(float(fov_short))
        data.clip_end = 1000.0
        # shift is measured in units of the frame's longer side
        data.shift_y = -float(subject_y) * self.height / float(max(self.width, self.height))
        obj = self._link(bpy.data.objects.new(name, data))
        obj.location = location
        self.aim(obj, target)
        self.scene.camera = obj
        if dof_focus is not None:
            data.dof.use_dof = True
            data.dof.aperture_fstop = float(fstop)
            if isinstance(dof_focus, bpy.types.Object):
                data.dof.focus_object = dof_focus
            else:
                data.dof.focus_distance = float(dof_focus)
        return obj

    def motion_blur(self, shutter=0.5):
        self.scene.render.use_motion_blur = True
        self.scene.render.motion_blur_shutter = float(shutter)

    def fog(self, density=0.02, color="paper", anisotropy=0.2, extent=(14.0, 14.0, 9.0), center=(0.0, 0.0, 0.0)):
        """Volumetric haze in a box around the set (god rays need a light passing through it).

        A box, not a world volume: EEVEE (4.2+) treats a world volume as infinite, so it absorbs all sun
        and world light. extent is the half-size (x, y, z); keep the camera and the lights' paths inside."""
        box = self.primitive("cube", "fog", size=1.0, location=center, smooth=False)
        box.scale = extent
        mat = bpy.data.materials.new("fog")
        if hasattr(mat, "use_nodes") and not mat.use_nodes:
            mat.use_nodes = True
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        for node in [n for n in nodes if n.type == "BSDF_PRINCIPLED"]:
            nodes.remove(node)
        vol = nodes.new("ShaderNodeVolumePrincipled")
        _set_input(vol, "Color", self.color(color))
        _set_input(vol, "Density", float(density))
        _set_input(vol, "Anisotropy", float(anisotropy))
        out = next(n for n in nodes if n.type == "OUTPUT_MATERIAL")
        links.new(vol.outputs[0], out.inputs["Volume"])
        self.assign(box, mat)
        box.visible_shadow = False
        ev = self.scene.eevee
        # shafts need occluders to shadow the volume
        for attr, value in (("use_volumetric_shadows", True), ("volumetric_tile_size", "4"), ("volumetric_end", 60.0)):
            if hasattr(ev, attr):
                try:
                    setattr(ev, attr, value)
                except TypeError:
                    pass
        return vol

    # ------------------------------------------------------------------ animation
    def key(self, target, path, keys, ease="power2.out"):
        """Keyframe `target.<path>` at plate seconds: keys = [(t, value), ...]; `ease` shapes every segment."""
        interp, easing = ease_to_blender(ease)
        frames = []
        for t, value in keys:
            frame = self.f(t)
            setattr(target, path, value)
            target.keyframe_insert(data_path=path, frame=frame)
            frames.append(frame)
        for fc in _fcurves(target.id_data):
            if fc.data_path.endswith(path):
                for kp in fc.keyframe_points:
                    if int(round(kp.co[0])) in frames:
                        kp.interpolation = interp
                        if easing != "AUTO":
                            kp.easing = easing
        return frames

    def orbit(self, obj, center=(0, 0, 0), radius=8.0, height=3.0, start_deg=-90.0, end_deg=-60.0,
              t0=0.0, t1=None, ease="sine.inOut", steps=None):
        """Move obj on a circular arc around `center` (aim it separately); sampled so the path stays an arc."""
        t1 = self.duration if t1 is None else t1
        steps = steps or max(2, int(math.ceil((t1 - t0) / 0.5)))
        interp, easing = ease_to_blender(ease)
        keys = []
        for i in range(steps + 1):
            u = i / steps
            w = _ease_value(u, interp, easing)
            a = math.radians(start_deg + (end_deg - start_deg) * w)
            loc = (center[0] + radius * math.cos(a), center[1] + radius * math.sin(a), center[2] + height)
            keys.append((t0 + (t1 - t0) * u, loc))
        return self.key(obj, "location", keys, ease="none")

    def on_frame(self, fn):
        """Drive properties as a pure function of plate time: fn(t_seconds), on every frame and sub-frame."""
        fps = float(self.fps)

        def handler(scene, *_):
            fn((scene.frame_current - 1 + scene.frame_subframe) / fps)

        bpy.app.handlers.frame_change_pre.append(handler)
        return handler

    # ------------------------------------------------------------------ simulation helpers
    def particles(self, emitter, count=400, lifetime_sec=None, start_sec=0.0, end_sec=None, size=0.03,
                  instance=None, velocity=0.6, gravity=0.0, seed=None):
        """Emitter particle system on `emitter`, seeded and timed in plate seconds."""
        mod = emitter.modifiers.new("particles", "PARTICLE_SYSTEM")
        psys = mod.particle_system
        psys.seed = int(self.seed if seed is None else seed) % 100000
        st = psys.settings
        st.count = int(count)
        st.frame_start = self.f(start_sec)
        st.frame_end = self.f(self.duration if end_sec is None else end_sec)
        st.lifetime = max(1, int(round((lifetime_sec or self.duration) * self.fps)))
        st.normal_factor = float(velocity)
        st.particle_size = float(size)
        st.effector_weights.gravity = float(gravity)
        if instance is not None:
            st.render_type = "OBJECT"
            st.instance_object = instance
        emitter.show_instancer_for_render = False
        return psys

    def rigid_world(self, substeps=10):
        if self.scene.rigidbody_world is None:
            with bpy.context.temp_override(scene=self.scene):
                bpy.ops.rigidbody.world_add()
        rbw = self.scene.rigidbody_world
        rbw.substeps_per_frame = int(substeps)
        rbw.point_cache.frame_start = 1
        rbw.point_cache.frame_end = self.frames
        return rbw

    def rigid(self, obj, kind="ACTIVE", mass=1.0, friction=0.6, bounce=0.1, shape="CONVEX_HULL"):
        self.rigid_world()
        with bpy.context.temp_override(object=obj, active_object=obj, selected_objects=[obj], scene=self.scene):
            bpy.ops.rigidbody.object_add(type=kind)
        rb = obj.rigid_body
        rb.mass, rb.friction, rb.restitution, rb.collision_shape = mass, friction, bounce, shape
        return rb


def reset_scene():
    """Empty the factory scene (cube, light, camera) and drop earlier frame handlers."""
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.lights, bpy.data.cameras, bpy.data.materials):
        for block in list(coll):
            if block.users == 0:
                coll.remove(block)
    bpy.app.handlers.frame_change_pre.clear()


def engine_id(name):
    """'eevee' | 'cycles' | 'workbench' -> the engine identifier this Blender build exposes."""
    items = bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items.keys()
    wanted = {"eevee": ["BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"], "cycles": ["CYCLES"],
              "workbench": ["BLENDER_WORKBENCH"]}[name]
    for ident in wanted:
        if ident in items:
            return ident
    raise RuntimeError(f"render engine '{name}' is not available in this Blender build ({', '.join(items)})")


def use_gpu_for_cycles():
    """First available Cycles GPU backend (Metal on the M2); CPU when there is none."""
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
    except KeyError:
        return "CPU"
    for backend in ("METAL", "OPTIX", "CUDA", "HIP", "ONEAPI"):
        try:
            prefs.compute_device_type = backend
        except TypeError:
            continue
        prefs.get_devices()
        if any(d.type != "CPU" for d in prefs.devices):
            for d in prefs.devices:
                d.use = d.type != "CPU"
            bpy.context.scene.cycles.device = "GPU"
            return backend
    prefs.compute_device_type = "NONE"
    bpy.context.scene.cycles.device = "CPU"
    return "CPU"


def configure(lab, job):
    """Render settings from the job: size, fps, range, engine, samples, seed, colour, alpha, output."""
    scene = lab.scene
    r = scene.render
    r.resolution_x, r.resolution_y = lab.width, lab.height
    preview = job.get("preview") or {}
    r.resolution_percentage = int(preview.get("resolution_percent", 100))
    r.fps, r.fps_base = lab.fps, 1.0
    scene.frame_start, scene.frame_end = 1, lab.frames
    scene.frame_step = int(preview.get("frame_step", 1))
    engine = job.get("engine", "eevee")
    r.engine = engine_id(engine)
    samples = int(preview.get("samples") or job.get("samples") or (64 if engine == "cycles" else 32))
    device = "CPU"
    if engine == "cycles":
        device = use_gpu_for_cycles()
        scene.cycles.samples = samples
        scene.cycles.seed = lab.seed % 2147483647
        scene.cycles.use_animated_seed = False
        scene.cycles.use_denoising = True
    elif engine == "eevee":
        scene.eevee.taa_render_samples = samples
        device = "GPU"
    r.film_transparent = lab.alpha
    r.use_persistent_data = False
    scene.view_settings.view_transform = job.get("view_transform", "Standard")
    scene.view_settings.look = "None"
    img = r.image_settings
    if hasattr(img, "media_type"):
        img.media_type = "IMAGE"
    img.file_format = "PNG"
    img.color_mode = "RGBA" if lab.alpha else "RGB"
    img.color_depth = "8"
    img.compression = 15
    r.use_file_extension = True
    r.filepath = job["frames_dir"].rstrip("/\\") + "/frame_#####"
    return {"engine": r.engine, "samples": samples, "device": device}
