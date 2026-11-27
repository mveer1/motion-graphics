"""
Core of the 3D mythic figure kit (runs inside Blender, `bpy` + bundled numpy).

How a figure is made, in four layers that mirror the 2D kit's layer order (base, shadow, light, features):

1. **Skin** - one metaball family per figure (`Blob`): bone capsules plus muscle masses as ellipsoids, all
   given in *visible* half-extents (the helper solves Blender's field radius and stiffness), so the body
   blends into one continuous surface with no seams at the shoulder, hip, knee or neck.
2. **Sculpt** - `Sculpt` pushes the converted mesh along its normals with analytic bumps and grooves
   (pectoral edge, linea alba, deltoid separation, lips, eyelid creases): the definition metaballs cannot give.
3. **Paint** - `Paint` writes per-vertex colour, roughness and metalness from region functions (lips,
   tilak, brows, the blue throat, hair caps, painted cloth), so no UV unwrapping is needed.
4. **Dress and attributes** - separate meshes (lathe, sweep, ribbon, extrusion), fitted to the body
   with BVH ray casts where they touch it (belts, armbands, the sacred thread).

Everything is deterministic: no `random`, no time; noise is a hash of the position.
"""

import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

THRESHOLD = 0.6


# ---------------------------------------------------------------------- colour
def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def lin(hexstr, alpha=1.0):
    """'#E05A47' -> linear (r, g, b, a)."""
    v = hexstr.lstrip("#")
    if len(v) == 3:
        v = "".join(ch * 2 for ch in v)
    r, g, b = (int(v[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    return (srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b), alpha)


def mix_hex(a, b, t):
    """Mix two sRGB hex colours in display space (for derived tones)."""
    a, b = a.lstrip("#"), b.lstrip("#")
    out = ""
    for i in (0, 2, 4):
        x = int(a[i:i + 2], 16) * (1 - t) + int(b[i:i + 2], 16) * t
        out += "%02X" % max(0, min(255, int(round(x))))
    return "#" + out


# ---------------------------------------------------------------------- vectors and frames
def V(p):
    return Vector((float(p[0]), float(p[1]), float(p[2])))


def lerp(a, b, t):
    return a + (b - a) * t


def vlerp(a, b, t):
    return V(a).lerp(V(b), t)


def basis(along, front=(0.0, -1.0, 0.0)):
    """3x3 rotation whose columns are local x (along), y (towards `front`), z (x cross y)."""
    x = V(along).normalized()
    f = V(front)
    y = f - x * f.dot(x)
    if y.length < 1e-5:
        alt = Vector((0.0, 0.0, 1.0)) if abs(x.z) < 0.9 else Vector((0.0, -1.0, 0.0))
        y = alt - x * alt.dot(x)
    y.normalize()
    z = x.cross(y)
    return Matrix((x, y, z)).transposed()


def rot_z(deg):
    return Matrix.Rotation(math.radians(deg), 3, "Z")


def rot_x(deg):
    return Matrix.Rotation(math.radians(deg), 3, "X")


def rot_y(deg):
    return Matrix.Rotation(math.radians(deg), 3, "Y")


def ik2(s, w, a, b, pole):
    """Two-bone IK: (elbow, reached wrist) joining s to w with lengths a, b, bending towards `pole`."""
    s, w, pole = V(s), V(w), V(pole)
    d = w - s
    dist = max(abs(a - b) + 1e-4, min(a + b - 1e-4, d.length))
    dn = d.normalized()
    cos_a = max(-1.0, min(1.0, (a * a + dist * dist - b * b) / (2 * a * dist)))
    along = a * cos_a
    perp = math.sqrt(max(0.0, a * a - along * along))
    p = pole - dn * pole.dot(dn)
    if p.length < 1e-6:
        p = Vector((0.0, -1.0, 0.0)) - dn * (-dn.y)
    p.normalize()
    return s + dn * along + p * perp, s + dn * dist


# ---------------------------------------------------------------------- metaballs
class Blob:
    """One metaball family. Sizes are visible half-extents in metres; `soft` 0 (tight) .. 1 (melting)."""

    def __init__(self, name, res=0.0036):
        self.name = name
        self.mb = bpy.data.metaballs.new(name)
        self.mb.resolution = res
        self.mb.render_resolution = res
        self.mb.threshold = THRESHOLD
        self.obj = bpy.data.objects.new(name, self.mb)
        bpy.context.scene.collection.objects.link(self.obj)
        self.count = 0

    @staticmethod
    def _stiff(soft):
        return 1.0 + (1.0 - max(0.0, min(1.0, soft))) * 9.0

    @staticmethod
    def _k(stiff):
        return math.sqrt(max(1e-6, 1.0 - (THRESHOLD / stiff) ** (1.0 / 3.0)))

    def ell(self, c, ext, rot=None, soft=0.5, neg=False):
        """Ellipsoid with visible half-extents ext=(ex, ey, ez) along rot's columns (world axes if None)."""
        s = self._stiff(soft)
        k = self._k(s)
        ex = [max(1e-4, float(e)) for e in ext]
        r = max(ex) / k
        e = self.mb.elements.new(type="ELLIPSOID")
        e.co = V(c)
        e.radius = r
        e.size_x, e.size_y, e.size_z = (x / (k * r) for x in ex)
        e.stiffness = s
        e.use_negative = bool(neg)
        if rot is not None:
            e.rotation = rot.to_quaternion()
        self.count += 1
        return e

    def cap(self, p0, p1, r, soft=0.5, neg=False):
        """Capsule from p0 to p1 with visible radius r."""
        p0, p1 = V(p0), V(p1)
        s = self._stiff(soft)
        k = self._k(s)
        d = p1 - p0
        e = self.mb.elements.new(type="CAPSULE")
        e.co = (p0 + p1) * 0.5
        e.radius = float(r) / k
        e.size_x = max(1e-4, d.length * 0.5)
        e.stiffness = s
        e.use_negative = bool(neg)
        if d.length > 1e-6:
            e.rotation = basis(d).to_quaternion()
        self.count += 1
        return e

    def ball(self, c, r, soft=0.5, neg=False):
        s = self._stiff(soft)
        e = self.mb.elements.new(type="BALL")
        e.co = V(c)
        e.radius = float(r) / self._k(s)
        e.stiffness = s
        e.use_negative = bool(neg)
        self.count += 1
        return e

    def to_mesh(self, name=None, material=None):
        dg = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(self.obj.evaluated_get(dg))
        me.name = name or self.name
        ob = bpy.data.objects.new(name or (self.name + "-mesh"), me)
        bpy.context.scene.collection.objects.link(ob)
        bpy.data.objects.remove(self.obj, do_unlink=True)
        smooth(me)
        if material is not None:
            me.materials.append(material)
        return ob


# ---------------------------------------------------------------------- numpy mesh access
def smooth(me):
    if hasattr(me, "shade_smooth"):
        me.shade_smooth()
    else:
        for p in me.polygons:
            p.use_smooth = True


def verts_np(me):
    a = np.empty(len(me.vertices) * 3, dtype=np.float64)
    me.vertices.foreach_get("co", a)
    return a.reshape(-1, 3)


def set_verts(me, arr):
    me.vertices.foreach_set("co", np.ascontiguousarray(arr, dtype=np.float32).ravel())
    me.update()


def normals_np(me):
    a = np.empty(len(me.vertices) * 3, dtype=np.float64)
    if hasattr(me, "vertex_normals"):
        me.vertex_normals.foreach_get("vector", a)
    else:
        me.vertices.foreach_get("normal", a)
    return a.reshape(-1, 3)


def set_point_attr(me, name, values, kind="FLOAT"):
    attr = me.attributes.get(name) or me.attributes.new(name, kind, "POINT")
    attr.data.foreach_set("value", np.ascontiguousarray(values, dtype=np.float32).ravel())


def set_point_color(me, name, rgba):
    attr = me.color_attributes.get(name) or me.color_attributes.new(name, "FLOAT_COLOR", "POINT")
    attr.data.foreach_set("color", np.ascontiguousarray(rgba, dtype=np.float32).ravel())


# ---------------------------------------------------------------------- region functions (numpy)
def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def local(P, c, rot):
    """Points expressed in a frame at c whose axes are the columns of rot (3x3 Matrix)."""
    R = np.array(rot, dtype=np.float64) if rot is not None else np.eye(3)
    return (P - np.asarray(c, dtype=np.float64)) @ R


def r_ell(P, c, ext, rot=None, edge=0.12):
    """1 inside the ellipsoid, 0 outside, soft over `edge` (fraction of the normalised radius)."""
    q = local(P, c, rot) / np.asarray(ext, dtype=np.float64)
    d = np.sqrt((q * q).sum(1))
    return 1.0 - smoothstep(1.0 - edge, 1.0 + edge, d)


def seg_dist(P, a, b):
    """Distance from points to segment a-b, and the parameter along it."""
    a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    ab = b - a
    L2 = max(1e-12, float(ab @ ab))
    t = np.clip(((P - a) @ ab) / L2, 0.0, 1.0)
    proj = a + t[:, None] * ab
    return np.sqrt(((P - proj) ** 2).sum(1)), t


def curve_dist(P, pts):
    """Distance to a polyline and the arc-length fraction of the nearest point."""
    pts = [np.asarray(tuple(p), dtype=np.float64) for p in pts]
    lens = [float(np.linalg.norm(pts[i + 1] - pts[i])) for i in range(len(pts) - 1)]
    tot = max(1e-9, sum(lens))
    best = np.full(len(P), np.inf)
    frac = np.zeros(len(P))
    acc = 0.0
    for i in range(len(pts) - 1):
        d, t = seg_dist(P, pts[i], pts[i + 1])
        m = d < best
        best[m] = d[m]
        frac[m] = (acc + t[m] * lens[i]) / tot
        acc += lens[i]
    return best, frac


def r_curve(P, pts, width, edge=0.35, taper=None):
    """Band of half-width `width` around a polyline; taper (w0, w1) scales the width along it."""
    d, f = curve_dist(P, pts)
    w = width if taper is None else width * (taper[0] + (taper[1] - taper[0]) * f)
    return 1.0 - smoothstep(w * (1 - edge), w * (1 + edge), d)


def r_plane(P, point, normal, edge=0.002):
    """1 on the side the normal points to."""
    n = np.asarray(tuple(normal), dtype=np.float64)
    n = n / np.linalg.norm(n)
    s = (P - np.asarray(tuple(point), dtype=np.float64)) @ n
    return smoothstep(-edge, edge, s)


def r_zband(P, z0, z1, edge=0.003):
    return smoothstep(z0 - edge, z0 + edge, P[:, 2]) * (1 - smoothstep(z1 - edge, z1 + edge, P[:, 2]))


def hash_noise(P, scale, seed=0):
    """Deterministic value noise in [-1, 1] (trilinear over a hashed lattice)."""
    q = P * scale + seed * 17.13
    i = np.floor(q)
    f = q - i
    f = f * f * (3 - 2 * f)

    def h(ix, iy, iz):
        n = np.sin(ix * 127.1 + iy * 311.7 + iz * 74.7 + seed * 13.3) * 43758.5453
        return (n - np.floor(n)) * 2 - 1

    out = 0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (f[:, 0] if dx else 1 - f[:, 0]) * (f[:, 1] if dy else 1 - f[:, 1]) * (f[:, 2] if dz else 1 - f[:, 2])
                out = out + w * h(i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz)
    return out


# ---------------------------------------------------------------------- sculpt and paint
class Sculpt:
    """Accumulates normal displacement on a mesh, then applies it once."""

    def __init__(self, ob):
        self.ob = ob
        self.me = ob.data
        self.P = verts_np(self.me)
        self.N = normals_np(self.me)
        self.d = np.zeros(len(self.P))

    def bump(self, c, ext, amp, rot=None):
        """Smooth bump (amp > 0) or dent (amp < 0) shaped by an ellipsoid."""
        q = local(self.P, c, rot) / np.asarray(ext, dtype=np.float64)
        r2 = (q * q).sum(1)
        self.d += amp * np.exp(-r2 * 2.2) * (r2 < 9)

    def groove(self, pts, width, depth, taper=(1.0, 1.0), sharp=1.0, ends=0.12):
        """A crease along a polyline: depth > 0 cuts in, width is the half-width."""
        d, f = curve_dist(self.P, pts)
        w = width * (taper[0] + (taper[1] - taper[0]) * f)
        e = smoothstep(0.0, ends, f) * smoothstep(0.0, ends, 1.0 - f) if ends > 0 else 1.0
        self.d -= depth * np.exp(-(d / w) ** (2.0 * sharp)) * e

    def ridge(self, pts, width, height, taper=(1.0, 1.0)):
        self.groove(pts, width, -height, taper)

    def profile(self, pts, widths, heights):
        """A raised (heights > 0) or cut (< 0) form along a curve whose width and height vary along it
        (lists sampled evenly from start to end): a nose, a lid, a brow."""
        d, f = curve_dist(self.P, pts)
        xs = np.linspace(0, 1, len(widths))
        w = np.interp(f, xs, widths)
        h = np.interp(f, np.linspace(0, 1, len(heights)), heights)
        self.d += h * np.exp(-(d / w) ** 2)

    def region(self, mask, amount):
        """Raise (or lower) a painted region: hair caps, tight cloth, ornaments in relief."""
        self.d += amount * mask

    def noise(self, mask, scale, amp, seed=0):
        self.d += amp * mask * hash_noise(self.P, scale, seed)

    def apply(self):
        set_verts(self.me, self.P + self.N * self.d[:, None])


class Paint:
    """Per-vertex colour, roughness and metalness, composited layer by layer like the 2D kit."""

    def __init__(self, ob, base, rough=0.5, metal=0.0):
        self.ob = ob
        self.me = ob.data
        self.P = verts_np(self.me)
        n = len(self.P)
        self.col = np.tile(np.array(lin(base), dtype=np.float64), (n, 1))
        self.rough = np.full(n, float(rough))
        self.metal = np.full(n, float(metal))
        self.mask = {}

    def layer(self, mask, color, opacity=1.0, rough=None, metal=None, name=None):
        w = np.clip(mask * opacity, 0.0, 1.0)
        c = np.array(lin(color), dtype=np.float64)
        self.col[:, :3] = self.col[:, :3] * (1 - w[:, None]) + c[:3] * w[:, None]
        if rough is not None:
            self.rough = self.rough * (1 - w) + rough * w
        if metal is not None:
            self.metal = self.metal * (1 - w) + metal * w
        if name:
            self.mask[name] = np.maximum(self.mask.get(name, 0), w)
        return w

    def apply(self):
        set_point_color(self.me, "Col", self.col)
        set_point_attr(self.me, "rough", self.rough)
        set_point_attr(self.me, "metal", self.metal)


# ---------------------------------------------------------------------- mesh builders
def link(ob):
    bpy.context.scene.collection.objects.link(ob)
    return ob


def mesh_obj(name, verts, faces, material=None, smooth_shade=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, v)) for v in verts], [], [tuple(f) for f in faces])
    me.validate()
    me.update()
    if smooth_shade:
        smooth(me)
    ob = link(bpy.data.objects.new(name, me))
    if material is not None:
        me.materials.append(material)
    return ob


def catmull(pts, n_per=8, closed=False):
    """Catmull-Rom resample of a polyline (list of Vector)."""
    pts = [V(p) for p in pts]
    if len(pts) < 3:
        out = []
        for i in range(len(pts) - 1):
            for j in range(n_per):
                out.append(pts[i].lerp(pts[i + 1], j / n_per))
        out.append(pts[-1])
        return out
    if closed:
        P = [pts[-1]] + pts + [pts[0], pts[1]]
    else:
        P = [pts[0] * 2 - pts[1]] + pts + [pts[-1] * 2 - pts[-2]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for j in range(n_per):
            t = j / n_per
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    if not closed:
        out.append(pts[-1])
    return out


def resample(values, n_out):
    xs = np.linspace(0, 1, len(values))
    return list(np.interp(np.linspace(0, 1, n_out), xs, values))


def transport_frames(path, up=(0, 0, 1)):
    """Parallel-transport frames (tangent, normal, binormal) along a polyline."""
    T = []
    for i in range(len(path)):
        a = path[max(0, i - 1)]
        b = path[min(len(path) - 1, i + 1)]
        t = (b - a)
        T.append(t.normalized() if t.length > 1e-9 else Vector((0, 0, 1)))
    u = V(up)
    n0 = u - T[0] * u.dot(T[0])
    if n0.length < 1e-5:
        alt = Vector((1, 0, 0)) if abs(T[0].x) < 0.9 else Vector((0, 1, 0))
        n0 = alt - T[0] * alt.dot(T[0])
    n0.normalize()
    N = [n0]
    for i in range(1, len(path)):
        n = N[-1] - T[i] * N[-1].dot(T[i])
        if n.length < 1e-9:
            n = N[-1]
        N.append(n.normalized())
    B = [T[i].cross(N[i]) for i in range(len(path))]
    return T, N, B


def sweep(name, pts, radii, sides=14, material=None, n_per=6, caps=True, profile=None, up=(0, 0, 1),
          closed=False, twist=0.0):
    """Tube (or any profile) swept along a smooth curve. radii: one per control point (r or (rx, ry)).
    profile: [(x, y)] around the unit circle (default circle). twist: turns of the profile along the path."""
    path = catmull(pts, n_per, closed)
    n = len(path)
    if isinstance(radii, (int, float)):
        radii = [radii] * len(pts)
    pairs = [(r, r) if isinstance(r, (int, float)) else tuple(r) for r in radii]
    rx = resample([p[0] for p in pairs], n)
    ry = resample([p[1] for p in pairs], n)
    if profile is None:
        profile = [(math.cos(2 * math.pi * k / sides), math.sin(2 * math.pi * k / sides)) for k in range(sides)]
    m = len(profile)
    T, N, B = transport_frames(path, up)
    verts, faces = [], []
    for i in range(n):
        ang = twist * 2 * math.pi * i / max(1, n - 1)
        ca, sa = math.cos(ang), math.sin(ang)
        for (x, y) in profile:
            xx, yy = x * ca - y * sa, x * sa + y * ca
            verts.append(path[i] + N[i] * (xx * rx[i]) + B[i] * (yy * ry[i]))
    for i in range(n - (0 if closed else 1)):
        i2 = (i + 1) % n
        for k in range(m):
            k2 = (k + 1) % m
            faces.append((i * m + k, i * m + k2, i2 * m + k2, i2 * m + k))
    if caps and not closed:
        c0 = len(verts)
        verts.append(path[0])
        c1 = len(verts)
        verts.append(path[-1])
        for k in range(m):
            k2 = (k + 1) % m
            faces.append((c0, k2, k))
            faces.append((c1, (n - 1) * m + k, (n - 1) * m + k2))
    ob = mesh_obj(name, verts, faces, material)
    ob["path"] = [tuple(p) for p in path]
    return ob


def place(ob, center=(0, 0, 0), rot=None, scale=None):
    """Bake a transform into the mesh: scale, then rotate, then move."""
    M = Matrix.Translation(V(center))
    if rot is not None:
        M = M @ rot.to_4x4()
    if scale is not None:
        M = M @ Matrix.Diagonal((float(scale[0]), float(scale[1]), float(scale[2]), 1.0))
    ob.data.transform(M)
    ob.data.update()
    return ob


def lathe(name, profile, segs=64, material=None, radial=None, center=(0, 0, 0), rot=None, caps=True, ry=1.0):
    """Revolve a profile [(r, z), ...] about the local z axis. radial(theta, i) multiplies r (flutes).
    ry squashes the y radius (elliptic sections)."""
    verts, faces = [], []
    m = len(profile)
    for j in range(segs):
        th = 2 * math.pi * j / segs
        for i, (r, z) in enumerate(profile):
            rr = r * (radial(th, i) if radial else 1.0)
            verts.append((rr * math.cos(th), rr * math.sin(th) * ry, z))
    for j in range(segs):
        j2 = (j + 1) % segs
        for i in range(m - 1):
            faces.append((j * m + i, j2 * m + i, j2 * m + i + 1, j * m + i + 1))
    if caps:
        if profile[0][0] > 1e-6:
            c = len(verts)
            verts.append((0, 0, profile[0][1]))
            for j in range(segs):
                faces.append((c, ((j + 1) % segs) * m, j * m))
        if profile[-1][0] > 1e-6:
            c = len(verts)
            verts.append((0, 0, profile[-1][1]))
            for j in range(segs):
                faces.append((c, j * m + m - 1, ((j + 1) % segs) * m + m - 1))
    ob = mesh_obj(name, verts, faces, material)
    return place(ob, center, rot)


def ellipsoid(name, c, ext, rot=None, material=None, segs=32):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=max(8, segs // 2), radius=1.0)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    smooth(me)
    ob = link(bpy.data.objects.new(name, me))
    if material is not None:
        me.materials.append(material)
    return place(ob, c, rot, ext)


def extrude(name, poly, depth, material=None, center=(0, 0, 0), rot=None, bevel=0.0):
    """Extrude a 2D polygon (x, y) along local z by depth (centred), optional bevel width."""
    bm = bmesh.new()
    top = [bm.verts.new((x, y, depth / 2)) for (x, y) in poly]
    bot = [bm.verts.new((x, y, -depth / 2)) for (x, y) in poly]
    bm.faces.new(top)
    bm.faces.new(list(reversed(bot)))
    n = len(poly)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = link(bpy.data.objects.new(name, me))
    if material is not None:
        me.materials.append(material)
    if bevel > 0:
        mod = ob.modifiers.new("bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 3
        mod.limit_method = "ANGLE"
    return place(ob, center, rot)


def ribbon(name, pts, widths, normal_hint, material=None, n_per=6, thickness=0.004, waves=None, cols=7):
    """A cloth strip along a curve; its width lies across the curve, facing `normal_hint`.
    waves: (amplitude, count) ripples across the width, growing towards the free end."""
    path = catmull(pts, n_per)
    n = len(path)
    W = resample(widths, n)
    T, _, _ = transport_frames(path)
    verts, faces = [], []
    hint = V(normal_hint)
    for i in range(n):
        side = T[i].cross(hint)
        if side.length < 1e-6:
            side = T[i].orthogonal()
        side.normalize()
        nrm = side.cross(T[i]).normalized()
        for k in range(cols):
            u = k / (cols - 1) - 0.5
            off = 0.0
            if waves:
                off = waves[0] * math.sin((u + 0.5) * math.pi * waves[1] + i * 0.35) * (i / max(1, n - 1))
            verts.append(path[i] + side * (u * W[i]) + nrm * off)
    for i in range(n - 1):
        for k in range(cols - 1):
            a = i * cols + k
            faces.append((a, a + 1, a + cols + 1, a + cols))
    ob = mesh_obj(name, verts, faces, material)
    if thickness > 0:
        mod = ob.modifiers.new("solid", "SOLIDIFY")
        mod.thickness = thickness
        mod.offset = 0.0
    return ob


def grid_surface(name, rows, material=None, thickness=0.0):
    """Quad surface from a grid of points rows[i][j] (Vector)."""
    nr, nc = len(rows), len(rows[0])
    verts = [p for row in rows for p in row]
    faces = []
    for i in range(nr - 1):
        for j in range(nc - 1):
            a = i * nc + j
            faces.append((a, a + 1, a + nc + 1, a + nc))
    ob = mesh_obj(name, verts, faces, material)
    if thickness > 0:
        mod = ob.modifiers.new("solid", "SOLIDIFY")
        mod.thickness = thickness
        mod.offset = 0.0
    return ob


def subdivide(ob, levels=1):
    mod = ob.modifiers.new("subd", "SUBSURF")
    mod.levels = levels
    mod.render_levels = levels
    return mod


def instance_along(make, pts, name):
    """Call make(i, p) for each point and join the results into one object."""
    objs = [make(i, V(p)) for i, p in enumerate(pts)]
    return join(objs, name)


def join(objs, name):
    """Join meshes into one object (modifiers applied, materials kept)."""
    objs = [o for o in objs if o is not None]
    if not objs:
        return None
    dg = bpy.context.evaluated_depsgraph_get()
    bm = bmesh.new()
    mats = []
    for o in objs:
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
        me.transform(o.matrix_world)
        slot = []
        for m in (o.data.materials if o.data.materials else [None]):
            if m in mats:
                slot.append(mats.index(m))
            else:
                mats.append(m)
                slot.append(len(mats) - 1)
        for p in me.polygons:
            p.material_index = slot[min(p.material_index, len(slot) - 1)]
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    ob = link(bpy.data.objects.new(name, me))
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)
    return ob


# ---------------------------------------------------------------------- fitting to the body
class Fit:
    """Ray casts against the skin to fit belts, bands, threads and garments to it."""

    def __init__(self, ob):
        dg = bpy.context.evaluated_depsgraph_get()
        self.tree = BVHTree.FromObject(ob, dg)

    def nearest(self, p):
        loc, nrm, _, _ = self.tree.find_nearest(V(p))
        return loc, nrm

    def onto(self, pts, offset=0.004):
        """Project points to the skin and lift them by offset along the surface normal."""
        out = []
        for p in pts:
            loc, nrm = self.nearest(p)
            out.append(loc + nrm * offset if loc is not None else V(p))
        return out

    def ring(self, center, axis, n=48, offset=0.004, reach=0.6):
        """Closed loop hugging the skin around `axis` through `center`. Rays go from the centre outwards, so
        the first surface met is the limb or torso the centre is inside, never a neighbouring arm or hand."""
        c, a = V(center), V(axis).normalized()
        u = a.orthogonal().normalized()
        w = a.cross(u)
        pts = []
        for i in range(n):
            th = 2 * math.pi * i / n
            d = u * math.cos(th) + w * math.sin(th)
            hit = self.tree.ray_cast(c, d, reach)
            pts.append(hit[0] + d * offset if hit[0] is not None else c + d * 0.02)
        return pts

    def outer(self, z, theta, center_xy=(0.0, 0.0), reach=0.9):
        """Distance from a vertical axis to the outermost skin at height z and angle theta (0 if none)."""
        d = Vector((math.cos(theta), math.sin(theta), 0.0))
        origin = Vector((center_xy[0], center_xy[1], z)) + d * reach
        hit = self.tree.ray_cast(origin, -d, reach * 1.5)
        if hit[0] is None:
            return 0.0
        return Vector((hit[0].x - center_xy[0], hit[0].y - center_xy[1], 0.0)).length
