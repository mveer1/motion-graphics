"""
Studio for the 3D mythic figures: a warm paper cyclorama (the light canvas default), the storyteller's
lamp as the key light from the viewer's upper left (figure-design.md section 3.3), a cool fill, a rim in
the aura's colour, and a turntable root so every view is lit the same way and keeps the same landmarks.
"""

import math

import bpy
from mathutils import Vector

from .core import lin, mesh_obj

PAPER = "#F4EFE6"


def _engine(name):
    items = bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items.keys()
    for ident in {"eevee": ["BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"], "cycles": ["CYCLES"]}[name]:
        if ident in items:
            return ident
    raise RuntimeError(f"no {name} engine in this Blender build")


def _try(obj, attr, value):
    if hasattr(obj, attr):
        try:
            setattr(obj, attr, value)
        except (TypeError, AttributeError, ValueError):
            pass


def reset():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.lights, bpy.data.cameras, bpy.data.materials, bpy.data.metaballs,
                 bpy.data.curves, bpy.data.worlds):
        for block in list(coll):
            if block.users == 0:
                coll.remove(block)


class Stage:
    def __init__(self, width=900, height=1200, samples=48, engine="eevee", paper=PAPER, rim="#F2C46B"):
        reset()
        sc = bpy.context.scene
        self.scene = sc
        r = sc.render
        r.engine = _engine(engine)
        r.resolution_x, r.resolution_y, r.resolution_percentage = int(width), int(height), 100
        r.film_transparent = False
        if engine == "eevee":
            ev = sc.eevee
            _try(ev, "taa_render_samples", int(samples))
            _try(ev, "use_raytracing", True)
            _try(ev, "use_shadows", True)
            _try(ev, "shadow_ray_count", 2)
            _try(ev, "shadow_step_count", 8)
            _try(ev, "use_gtao", True)
            _try(ev, "gtao_distance", 0.25)
            _try(ev, "fast_gi_distance", 0.4)
        else:
            sc.cycles.samples = int(samples)
            sc.cycles.use_denoising = True
            sc.cycles.seed = 7
        sc.view_settings.view_transform = "Standard"
        sc.view_settings.look = "None"
        img = r.image_settings
        if hasattr(img, "media_type"):
            img.media_type = "IMAGE"
        img.file_format = "PNG"
        img.color_mode = "RGB"
        img.color_depth = "8"
        w = bpy.data.worlds.new("mythic-world")
        sc.world = w
        if hasattr(w, "use_nodes") and not w.use_nodes:
            w.use_nodes = True
        bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
        bg.inputs["Color"].default_value = lin("#EFE6D6")
        bg.inputs["Strength"].default_value = 0.38
        self.paper = paper
        self.cyclorama(paper)
        self.lights(rim)
        self.root = bpy.data.objects.new("figure-root", None)
        sc.collection.objects.link(self.root)
        cam = bpy.data.cameras.new("camera")
        cam.sensor_fit = "VERTICAL"
        cam.clip_end = 200.0
        self.cam = bpy.data.objects.new("camera", cam)
        sc.collection.objects.link(self.cam)
        sc.camera = self.cam
        self.glows = []

    def cyclorama(self, color):
        """Floor sweeping up into a back wall far behind the figure (no horizon in any view)."""
        depth, back, rad, height, half = 14.0, 7.0, 3.5, 14.0, 30.0
        prof = [(-depth, 0.0), (back - rad, 0.0)]
        for i in range(1, 17):
            a = math.pi / 2 * i / 16
            prof.append((back - rad + rad * math.sin(a), rad - rad * math.cos(a)))
        prof.append((back, height))
        verts = [(x, y, z) for (y, z) in prof for x in (-half, half)]
        faces = [(2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2) for i in range(len(prof) - 1)]
        mat = bpy.data.materials.new("cyclorama")
        if hasattr(mat, "use_nodes") and not mat.use_nodes:
            mat.use_nodes = True
        b = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        b.inputs["Base Color"].default_value = lin(color)
        b.inputs["Roughness"].default_value = 0.9
        mesh_obj("cyclorama", verts, faces, mat)

    def _light(self, name, loc, energy, color, size, target=(0, 0, 1.0)):
        d = bpy.data.lights.new(name, "AREA")
        d.energy = energy
        d.color = lin(color)[:3]
        d.size = size
        ob = bpy.data.objects.new(name, d)
        self.scene.collection.objects.link(ob)
        ob.location = loc
        direction = Vector(target) - Vector(loc)
        ob.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        return ob

    def lights(self, rim):
        self.key = self._light("key-lamp", (-3.6, -4.2, 4.6), 820.0, "#FFE4C2", 3.0, (0, 0, 1.1))
        self.fill = self._light("fill", (4.2, -3.2, 1.8), 170.0, "#DCE4F0", 4.5, (0, 0, 1.0))
        self.rim = self._light("rim", (2.4, 3.6, 3.6), 700.0, rim, 2.2, (0, 0, 1.3))
        self.top = self._light("top", (0.0, -0.6, 6.0), 130.0, "#FFF4E2", 4.0, (0, 0, 1.0))

    def adopt(self, objs):
        for ob in objs:
            if ob is not None and ob.parent is None and ob is not self.root:
                ob.parent = self.root

    def glow_card(self, look, hexc, center, radius, strength=1.4, power=2.4, alpha=0.9):
        """A soft glow behind the figure, facing the camera (not on the turntable, so it stays behind)."""
        mat = look.glow("glow-" + hexc.lstrip("#"), hexc, strength, power, alpha)
        if mat is None:
            return None
        verts = [(0, 0, 0)] + [(math.cos(2 * math.pi * i / 64), 0.0, math.sin(2 * math.pi * i / 64)) for i in range(64)]
        faces = [(0, i + 1, (i + 1) % 64 + 1) for i in range(64)]
        ob = mesh_obj("glow", verts, faces, mat)
        ob.scale = (radius, radius, radius)
        ob.location = center
        if hasattr(ob, "visible_shadow"):
            ob.visible_shadow = False
        self.glows.append((ob, Vector(center)))
        return ob

    def view(self, target, frame_h, yaw=0.0, elev=0.0, dist=10.0):
        """Rotate the figure by yaw (degrees, positive turns its left side to the camera) and aim a long lens."""
        self.root.rotation_euler = (0.0, 0.0, math.radians(-yaw))
        t = Vector(target)
        e = math.radians(elev)
        loc = t + Vector((0.0, -dist * math.cos(e), dist * math.sin(e)))
        self.cam.location = loc
        self.cam.rotation_euler = (t - loc).to_track_quat("-Z", "Y").to_euler()
        self.cam.data.angle = 2 * math.atan(frame_h / 2 / dist)
        view_dir = (t - loc).normalized()
        for ob, c in self.glows:
            ob.location = Vector((c.x, c.y, c.z)) + view_dir * 0.45
            ob.rotation_euler = (math.radians(-elev), 0.0, 0.0)

    def render(self, path):
        self.scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
