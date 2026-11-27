"""
Materials for the 3D mythic figures, by role, in two looks.

- `painted` (default): a painted sculpture. Skin and painted cloth read the per-vertex colour,
  roughness and metalness written by core.Paint; a cavity term (ambient occlusion) darkens folds and
  creases the way paint pools in a carved image. Colours come from the identity blocks
  (figure-design.md section 4), so skin is the text's colour, never a default.
- `bronze`: one cast metal for everything (a Chola bronze, a Greek bronze): warm bronze, a dark patina
  in the cavities, polished high points. Glows are not drawn; haloes and flames stay as cast metal.

Every builder asks the Look for a material by role, so a figure is drawn once and dressed in either look.
"""

import bpy

from .core import lin

BRONZE = "#A0703C"
PATINA = "#3B2B1C"


def _lum(hexc):
    v = hexc.lstrip("#")
    r, g, b = (int(v[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _set(node, names, value):
    for name in names if isinstance(names, (list, tuple)) else [names]:
        sock = node.inputs.get(name)
        if sock is not None:
            sock.default_value = value
            return True
    return False


def _new(name):
    mat = bpy.data.materials.new(name)
    if hasattr(mat, "use_nodes") and not mat.use_nodes:
        mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    if bsdf is None:
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        nt.links.new(bsdf.outputs[0], out.inputs[0])
    return mat, nt, bsdf, out


def _cavity(nt, color_socket, amount, distance=0.035, dark=None):
    """Return a socket: colour * (1 - amount + amount * AO) (+ a dark tint in the creases)."""
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    _set(ao, "Distance", distance)
    fac = nt.nodes.new("ShaderNodeMath")
    fac.operation = "MULTIPLY_ADD"
    nt.links.new(ao.outputs["AO"], fac.inputs[0])
    fac.inputs[1].default_value = amount
    fac.inputs[2].default_value = 1.0 - amount
    sc = nt.nodes.new("ShaderNodeVectorMath")
    sc.operation = "SCALE"
    if isinstance(color_socket, tuple):
        sc.inputs["Vector"].default_value = color_socket[:3]
    else:
        nt.links.new(color_socket, sc.inputs["Vector"])
    nt.links.new(fac.outputs[0], sc.inputs["Scale"])
    return sc.outputs["Vector"]


def _attr(nt, name):
    a = nt.nodes.new("ShaderNodeAttribute")
    a.attribute_type = "GEOMETRY"
    a.attribute_name = name
    return a


class Look:
    def __init__(self, kind="painted"):
        if kind not in ("painted", "bronze"):
            raise ValueError(f"unknown look '{kind}' (painted | bronze)")
        self.kind = kind
        self.cache = {}

    @property
    def bronze(self):
        return self.kind == "bronze"

    def _key(self, *parts):
        return "|".join(str(p) for p in parts)

    def _bronze(self, name, tone=0.0, rough=0.34):
        """Cast bronze; tone > 0 is a brighter (gilded or polished) alloy, < 0 darker."""
        key = self._key("bronze", tone, rough)
        if key in self.cache:
            return self.cache[key]
        mat, nt, b, _ = _new("bronze-" + name)
        base = BRONZE if tone == 0 else ("#C49650" if tone > 0 else "#7A5430")
        c = _cavity(nt, lin(base), 0.85, 0.05)
        nt.links.new(c, b.inputs["Base Color"])
        _set(b, "Metallic", 1.0)
        _set(b, "Roughness", rough)
        self.cache[key] = mat
        return mat

    # ------------------------------------------------------------------ roles
    def skin(self, name="skin", cavity=0.45, sss=0.08):
        """Reads the Paint attributes (Col, rough, metal)."""
        if self.bronze:
            return self._bronze("skin")
        key = self._key("skin", name)
        if key in self.cache:
            return self.cache[key]
        mat, nt, b, _ = _new(name)
        col = _attr(nt, "Col")
        nt.links.new(_cavity(nt, col.outputs["Color"], cavity), b.inputs["Base Color"])
        nt.links.new(_attr(nt, "rough").outputs["Fac"], b.inputs["Roughness"])
        nt.links.new(_attr(nt, "metal").outputs["Fac"], b.inputs["Metallic"])
        _set(b, ["Subsurface Weight", "Subsurface"], sss)
        _set(b, "Subsurface Radius", (0.06, 0.03, 0.02))
        _set(b, "Subsurface Scale", 0.02)
        _set(b, ["Specular IOR Level", "Specular"], 0.35)
        self.cache[key] = mat
        return mat

    def solid(self, name, hexc, rough=0.6, metal=0.0, sheen=0.0, cavity=0.4, coat=0.0, tone=0.0):
        if self.bronze:
            return self._bronze(name, tone)
        key = self._key("solid", name, hexc, rough, metal, sheen)
        if key in self.cache:
            return self.cache[key]
        mat, nt, b, _ = _new(name)
        nt.links.new(_cavity(nt, lin(hexc), cavity), b.inputs["Base Color"])
        _set(b, "Roughness", rough)
        _set(b, "Metallic", metal)
        _set(b, ["Sheen Weight", "Sheen"], sheen)
        _set(b, ["Coat Weight", "Clearcoat"], coat)
        self.cache[key] = mat
        return mat

    def cloth(self, name, hexc, rough=0.78, sheen=0.35):
        return self.solid(name, hexc, rough=rough, sheen=sheen, cavity=0.55)

    def gold(self, name="gold", hexc="#D7A443", rough=0.26):
        if self.bronze:
            return self._bronze("gold", 1.0, 0.24)
        return self.solid(name, hexc, rough=rough, metal=1.0, cavity=0.5)

    def silver(self, name="silver", hexc="#C9CCD0", rough=0.3):
        if self.bronze:
            return self._bronze("silver", 1.0, 0.26)
        return self.solid(name, hexc, rough=rough, metal=1.0, cavity=0.4)

    def metal(self, name, hexc, rough=0.35):
        if self.bronze:
            return self._bronze(name, -1.0 if _lum(hexc) < 0.35 else 0.0, rough)
        return self.solid(name, hexc, rough=rough, metal=1.0, cavity=0.45)

    def gem(self, name, hexc):
        if self.bronze:
            return self._bronze("gem", 1.0, 0.18)
        return self.solid(name, hexc, rough=0.12, coat=0.6, cavity=0.1)

    def wood(self, name, hexc="#5A3A22", rough=0.55):
        if self.bronze:
            return self._bronze(name, -1.0)
        return self.solid(name, hexc, rough=rough, cavity=0.5, coat=0.15)

    def emissive(self, name, hexc, strength=3.0):
        """A lit surface (an arrow's tejas, the living eye, flames). Bronze: cast metal."""
        if self.bronze:
            return self._bronze(name, 1.0, 0.22)
        key = self._key("emit", name, hexc, strength)
        if key in self.cache:
            return self.cache[key]
        mat, nt, b, _ = _new(name)
        _set(b, "Base Color", lin(hexc))
        _set(b, ["Emission Color", "Emission"], lin(hexc))
        _set(b, "Emission Strength", strength)
        _set(b, "Roughness", 0.5)
        self.cache[key] = mat
        return mat

    def glow(self, name, hexc, strength=1.6, power=2.2, alpha=1.0):
        """Soft glow for a camera-facing card: emission fading from the centre (Object coords, unit radius)."""
        if self.bronze:
            return None
        key = self._key("glow", name, hexc, strength, power)
        if key in self.cache:
            return self.cache[key]
        mat, nt, b, out = _new(name)
        nt.nodes.remove(b)
        tc = nt.nodes.new("ShaderNodeTexCoord")
        ln = nt.nodes.new("ShaderNodeVectorMath")
        ln.operation = "LENGTH"
        nt.links.new(tc.outputs["Object"], ln.inputs[0])
        inv = nt.nodes.new("ShaderNodeMath")
        inv.operation = "SUBTRACT"
        inv.use_clamp = True
        inv.inputs[0].default_value = 1.0
        nt.links.new(ln.outputs["Value"], inv.inputs[1])
        pw = nt.nodes.new("ShaderNodeMath")
        pw.operation = "POWER"
        nt.links.new(inv.outputs[0], pw.inputs[0])
        pw.inputs[1].default_value = power
        mul = nt.nodes.new("ShaderNodeMath")
        mul.operation = "MULTIPLY"
        mul.use_clamp = True
        nt.links.new(pw.outputs[0], mul.inputs[0])
        mul.inputs[1].default_value = alpha
        em = nt.nodes.new("ShaderNodeEmission")
        _set(em, "Color", lin(hexc))
        _set(em, "Strength", strength)
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        mx = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(mul.outputs[0], mx.inputs[0])
        nt.links.new(tr.outputs[0], mx.inputs[1])
        nt.links.new(em.outputs[0], mx.inputs[2])
        nt.links.new(mx.outputs[0], out.inputs["Surface"])
        for attr, value in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND"), ("use_transparent_shadow", True)):
            if hasattr(mat, attr):
                try:
                    setattr(mat, attr, value)
                except TypeError:
                    pass
        self.cache[key] = mat
        return mat

    def eye(self, name, iris="#2A1A12", glow=0.0, sclera="#E8DFCE"):
        """Eyeball: sclera, iris ring and pupil from the angle to the object's -Y (gaze) axis."""
        if self.bronze:
            return self._bronze("eye", 0.0, 0.3)
        key = self._key("eye", name, iris, glow)
        if key in self.cache:
            return self.cache[key]
        mat, nt, b, _ = _new(name)
        tc = nt.nodes.new("ShaderNodeTexCoord")
        nrm = nt.nodes.new("ShaderNodeVectorMath")
        nrm.operation = "NORMALIZE"
        nt.links.new(tc.outputs["Object"], nrm.inputs[0])
        dot = nt.nodes.new("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        nt.links.new(nrm.outputs[0], dot.inputs[0])
        dot.inputs[1].default_value = (0.0, -1.0, 0.0)
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        cr = ramp.color_ramp
        cr.interpolation = "LINEAR"
        cr.elements[0].position = 0.0
        cr.elements[0].color = lin(sclera)
        cr.elements[1].position = 0.83
        cr.elements[1].color = lin(sclera)
        for pos, col in ((0.85, iris), (0.95, iris), (0.962, "#0B0807"), (1.0, "#0B0807")):
            e = cr.elements.new(pos)
            e.color = lin(col)
        nt.links.new(dot.outputs["Value"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
        _set(b, "Roughness", 0.12)
        _set(b, ["Coat Weight", "Clearcoat"], 0.8)
        if glow > 0:
            sock = b.inputs.get("Emission Color") or b.inputs.get("Emission")
            nt.links.new(ramp.outputs["Color"], sock)
            _set(b, "Emission Strength", glow)
        self.cache[key] = mat
        return mat

    def stripes(self, name, base, stripe, scale=18.0, rough=0.8):
        """Tiger skin: dark wavy stripes on an orange hide (wave texture + noise), object space."""
        if self.bronze:
            return self._bronze(name)
        key = self._key("stripes", name, base, stripe)
        if key in self.cache:
            return self.cache[key]
        mat, nt, b, _ = _new(name)
        tc = nt.nodes.new("ShaderNodeTexCoord")
        wave = nt.nodes.new("ShaderNodeTexWave")
        wave.wave_type = "BANDS"
        if hasattr(wave, "bands_direction"):
            wave.bands_direction = "Z"
        _set(wave, "Scale", scale)
        _set(wave, "Distortion", 9.0)
        _set(wave, "Detail", 3.0)
        nt.links.new(tc.outputs["Object"], wave.inputs["Vector"])
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        cr = ramp.color_ramp
        cr.elements[0].position = 0.0
        cr.elements[0].color = lin(stripe)
        cr.elements[1].position = 0.32
        cr.elements[1].color = lin(base)
        e = cr.elements.new(0.24)
        e.color = lin(stripe)
        nt.links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
        nt.links.new(_cavity(nt, ramp.outputs["Color"], 0.5), b.inputs["Base Color"])
        _set(b, "Roughness", rough)
        _set(b, ["Sheen Weight", "Sheen"], 0.4)
        self.cache[key] = mat
        return mat
