"""
Bodies for the 3D mythic figures: skeleton, posture, and the muscle masses that make one skin.

Units are metres. The reference figure is the heroic male canon of the 2D kit (figure-design.md
sections 3, 7, 8): about 8.5 heads, shoulders about 2.3-2.6 head-widths, the waist on the navel line,
elbows on the navel, wrists just below the crotch, a wide A-stance. Vertical landmarks are fractions of
the height T (Drillis and Contini), so a smaller head (the heroic canon) does not shorten the legs.

The figure stands on z = 0 and faces -Y (towards the front camera); its right side is -X.
"""

import math

from mathutils import Matrix, Vector

from .core import Blob, V, basis, ik2

# Presets mirror HERO in figures-human.js. Multipliers on the reference warrior.
PRESETS = {
    "warrior": dict(T=1.86, heads=8.5, sh=1.0, chest=1.0, waist=1.0, hips=1.0, arm=1.0, leg=1.0, neck=1.0,
                    muscle=1.0, arm_len=1.05, female=False),
    "titan": dict(T=1.96, heads=7.9, sh=1.16, chest=1.18, waist=1.16, hips=1.1, arm=1.32, leg=1.25, neck=1.4,
                  muscle=1.25, arm_len=1.0, female=False),
    "ascetic": dict(T=1.86, heads=8.5, sh=0.98, chest=0.94, waist=0.92, hips=0.96, arm=0.9, leg=0.92, neck=0.95,
                    muscle=0.9, arm_len=1.0, female=False),
    "goddess": dict(T=1.80, heads=8.2, sh=0.84, chest=0.84, waist=0.8, hips=1.02, arm=0.68, leg=0.84, neck=0.78,
                    muscle=0.62, arm_len=1.0, female=True),
    "elder": dict(T=1.92, heads=8.0, sh=1.04, chest=1.08, waist=1.14, hips=1.02, arm=1.0, leg=1.0, neck=1.05,
                  muscle=0.95, arm_len=1.0, female=False),
    # The Jina and the Buddha: "lion-like" smooth torso, broad shoulders, narrow waist, no muscle grid.
    "calm": dict(T=1.84, heads=8.4, sh=0.98, chest=1.0, waist=0.86, hips=0.98, arm=0.92, leg=0.92, neck=0.98,
                 muscle=0.55, arm_len=0.98, female=False, smooth=True),
    # Ganesha: heroic shoulders and arms over the great belly (Lambodara).
    "ganesha": dict(T=1.78, heads=6.2, sh=1.12, chest=1.08, waist=1.5, hips=1.2, arm=1.1, leg=1.08, neck=1.5,
                    muscle=0.9, arm_len=1.0, female=False, belly=True),
}


class Body:
    """Skeleton, posture and skin elements. Call build(), then skin = blob.to_mesh()."""

    def __init__(self, name, preset, pose=None, res=0.003):
        self.name = name
        self.P = dict(PRESETS[preset])
        self.preset = preset
        self.pose = pose or {}
        self.T = self.P["T"]
        self.H = self.T / self.P["heads"]
        self.s = self.T / 1.85                     # scale against the reference figure
        self.blob = Blob(name, res=res)
        self.J = {}
        self.frames = {}
        self.marks = {}                              # named points for paint, sculpt and dress
        self.seated = self.pose.get("seated")
        self.z_off = 0.0

    # ------------------------------------------------------------------ helpers
    def sv(self, x, y, z):
        """Reference-figure metres -> this figure (scaled about the origin)."""
        return Vector((x * self.s, y * self.s, z * self.s))

    def torso_map(self, p):
        """Apply the torso posture (bend, side bend, twist about the waist; hip shift; seated lift)."""
        p = V(p)
        bend, side, twist = self.pose.get("torso", (0.0, 0.0, 0.0))
        pivot = Vector((0.0, 0.0, 0.6 * self.T))
        R = (Matrix.Rotation(math.radians(twist), 3, "Z") @ Matrix.Rotation(math.radians(-side), 3, "Y")
             @ Matrix.Rotation(math.radians(-bend), 3, "X"))
        shift = Vector((self.pose.get("hip_shift", 0.0) * self.s, 0.0, self.z_off))
        if p.z > pivot.z:
            return pivot + R @ (p - pivot) + shift
        return p + shift

    def torso_rot(self):
        bend, side, twist = self.pose.get("torso", (0.0, 0.0, 0.0))
        return (Matrix.Rotation(math.radians(twist), 3, "Z") @ Matrix.Rotation(math.radians(-side), 3, "Y")
                @ Matrix.Rotation(math.radians(-bend), 3, "X"))

    def T_(self, x, y, z):
        return self.torso_map(self.sv(x, y, z))

    # ------------------------------------------------------------------ skeleton
    def skeleton(self):
        P, T, H = self.P, self.T, self.H
        if self.seated:
            seat = self.pose.get("seat_z", 0.62)
            self.z_off = seat + 0.10 * self.s - 0.53 * T
        J = self.J
        J["head_top"] = self.torso_map(Vector((0, 0.0, T)))
        J["chin"] = self.torso_map(Vector((0, -0.07 * self.s, T - H)))
        J["neck_base"] = self.T_(0, 0.012, 0.818 * 1.85)
        J["chest"] = self.T_(0, 0.0, 0.72 * 1.85)
        J["navel"] = self.T_(0, -0.1 * P["waist"], 0.60 * 1.85)
        for side, sx in (("r", -1), ("l", 1)):
            J["shoulder_" + side] = self.T_(sx * 0.192 * P["sh"], 0.012, 0.80 * 1.85)
            J["hip_" + side] = self.T_(sx * 0.092 * P["hips"], 0.0, 0.53 * 1.85) if not self.seated else \
                Vector((sx * 0.092 * P["hips"] * self.s, 0.0, 0.53 * T + self.z_off))
        hc = self.T - 0.5 * H
        tilt, turn, roll = self.pose.get("head", (0.0, 0.0, 0.0))
        R = (self.torso_rot() @ Matrix.Rotation(math.radians(turn), 3, "Z") @ Matrix.Rotation(math.radians(-tilt), 3, "X")
             @ Matrix.Rotation(math.radians(-roll), 3, "Y"))
        neck_pivot = self.torso_map(Vector((0, 0.01 * self.s, T - 1.05 * H)))
        centre = neck_pivot + R @ Vector((0, -0.01 * self.s, hc - (T - 1.05 * H)))
        self.frames["head"] = (centre, R)
        J["head"] = centre
        self.arms()
        self.legs()

    def arm_lengths(self):
        k = self.P["arm_len"]
        return 0.186 * self.T * k, 0.146 * self.T * k

    def arm_sides(self):
        return ["r", "l"] + list(self.pose.get("extra_arms", []))

    def arms(self):
        a, b = self.arm_lengths()
        for side in self.arm_sides():
            sx = -1 if side.startswith("r") else 1
            spec = self.pose.get("arm_" + side, {})
            if side not in ("r", "l"):
                off = V(spec.get("shoulder", (0.0, 0.04, 0.03)))
                self.J["shoulder_" + side] = self.J["shoulder_" + side[0]] + self.torso_rot() @ (off * self.s)
            S = self.J["shoulder_" + side]
            tgt = spec.get("wrist")
            if tgt is None:
                tgt = S + Vector((sx * 0.08, 0.02, -(a + b) * 0.97)) * 1.0
            else:
                tgt = self.torso_map(self.sv(*tgt)) if spec.get("torso_space", False) else self.sv(*tgt) + Vector((0, 0, self.z_off))
            pole = V(spec.get("pole", (sx * 0.3, 0.5, -0.2)))
            E, W = ik2(S, tgt, a, b, pole)
            self.J["elbow_" + side], self.J["wrist_" + side] = E, W

    def legs(self):
        T = self.T
        if self.seated:
            self.seated_legs()
            return
        a, b = 0.255 * T, 0.246 * T
        st = self.pose.get("stance", 0.13)
        for side, sx in (("r", -1), ("l", 1)):
            spec = self.pose.get("leg_" + side, {})
            Hj = self.J["hip_" + side]
            ank = V(spec.get("ankle", (sx * st, 0.015, 0.039 * 1.85)))
            ank = self.sv(*ank)
            K, A = ik2(Hj, ank, a, b, V(spec.get("pole", (sx * 0.15, -1.0, 0.0))))
            self.J["knee_" + side], self.J["ankle_" + side] = K, A
            self.J["toe_dir_" + side] = (Matrix.Rotation(math.radians(sx * spec.get("turn", 12)), 3, "Z") @ Vector((0, -1, 0)))

    def seated_legs(self):
        """Padmasana: knees wide and forward, each foot sole-up on the opposite thigh."""
        s, z0 = self.s, self.J["hip_r"].z - 0.10 * self.s
        wide = self.pose.get("knee_wide", 0.40)
        for side, sx in (("r", -1), ("l", 1)):
            up = 0.0 if side == "l" else 0.035
            self.J["knee_" + side] = Vector((sx * wide * s, -0.30 * s, z0 + 0.075 * s))
            self.J["ankle_" + side] = Vector((-sx * 0.02 * s, (-0.2 - (0.03 if side == "r" else 0)) * s, z0 + (0.14 + up) * s))
            self.J["toe_dir_" + side] = Vector((-sx * 0.9, 0.35, 0.25)).normalized()

    # ------------------------------------------------------------------ skin
    def build(self):
        self.skeleton()
        self.torso()
        for side in self.arm_sides():
            self.arm(side)
        for side in ("r", "l"):
            if self.seated:
                self.seated_leg(side)
            else:
                self.leg(side)
        return self

    def torso(self):
        B, P, m = self.blob, self.P, self.P["muscle"]
        ch, wa, hp = P["chest"], P["waist"], P["hips"]
        sm = P.get("smooth", False)
        T_ = self.T_
        s = self.s
        rot = self.torso_rot()
        # Neck column and the sternocleidomastoids.
        nk = 0.056 * P["neck"]
        neck_top = self.torso_map(Vector((0, 0.012 * s, self.T - 1.0 * self.H)))
        neck_mid = T_(0, 0.02, 1.47).lerp(neck_top, 0.5)
        B.cap(T_(0, 0.02, 1.47), neck_mid, nk * s, soft=0.62)
        B.cap(neck_mid, neck_top, nk * 0.86 * s, soft=0.62)
        if not sm:
            for sx in (-1, 1):
                B.cap(self.torso_map(Vector((sx * 0.046 * s, 0.025 * s, self.T - 1.08 * self.H))), T_(sx * 0.014, -0.04, 1.5),
                      0.0125 * s * P["neck"], soft=0.6)
        # Ribcage, the upper chest under the clavicles, the pectorals (a man's flat, squared chest).
        B.ell(T_(0, 0.012, 1.33), (0.15 * ch * s, 0.122 * ch * s, 0.2 * s), rot, soft=0.6)
        B.ell(T_(0, -0.035, 1.43), (0.125 * ch * s, 0.07 * s, 0.06 * s), rot, soft=0.62)
        if P["female"]:
            for sx in (-1, 1):
                B.ell(T_(sx * 0.08, -0.068, 1.318), (0.064 * s, 0.046 * s, 0.056 * s), rot, soft=0.58)
        else:
            for sx in (-1, 1):
                R = rot @ Matrix.Rotation(math.radians(-sx * 14), 3, "Y")
                B.ell(T_(sx * 0.078, -0.078 * ch, 1.36), (0.09 * ch * s, (0.028 + 0.006 * m) * ch * s, 0.062 * s), R, soft=0.55)
        for sx in (-1, 1):
            # Trapezius: high on the neck, sloping to the shoulder top (the heroic yoke); the upper back below.
            B.cap(T_(sx * 0.026, 0.04, 1.59), T_(sx * 0.165 * P["sh"], 0.02, 1.495), (0.03 + 0.012 * m) * (0.72 if sm else 1.0) * s * P["neck"] ** 0.5, soft=0.62)
            B.ell(T_(sx * 0.07, 0.06, 1.43), (0.08 * s, 0.04 * s, 0.075 * s), rot, soft=0.6)
            # Lats (the V) and the spine erectors.
            B.ell(T_(sx * 0.124 * ch, 0.035, 1.28), ((0.042 + 0.012 * m) * s, 0.08 * s, 0.14 * s), rot, soft=0.56)
            B.ell(T_(sx * 0.033, 0.083, 1.15), (0.03 * s, 0.028 * s, 0.13 * s), rot, soft=0.56)
        # Abdomen, rectus columns, obliques.
        B.ell(T_(0, -0.012, 1.14), (0.113 * wa * s, 0.08 * wa * s, 0.13 * s), rot, soft=0.6)
        if not sm and not P.get("belly"):
            for sx in (-1, 1):
                B.ell(T_(sx * 0.042, -0.068 * wa, 1.16), (0.045 * s, 0.018 * s, 0.13 * s), rot, soft=0.56)
        for sx in (-1, 1):
            B.ell(T_(sx * 0.098 * wa, -0.006, 1.09), (0.046 * s, 0.076 * wa * s, 0.085 * s), rot, soft=0.56)
        if P.get("belly"):
            # Lambodara: the great round belly, low and forward.
            B.ell(T_(0, -0.13, 1.04), (0.25 * s, 0.24 * s, 0.24 * s), rot, soft=0.55)
        # Pelvis and glutes.
        B.ell(T_(0, 0.005, 0.99), (0.145 * hp * s, 0.105 * hp * s, 0.11 * s), None, soft=0.6)
        for sx in (-1, 1):
            B.ell(T_(sx * 0.07 * hp, 0.045, 0.94), (0.072 * hp * s, 0.05 * s, 0.088 * s), None, soft=0.62)
        self.marks["navel"] = T_(0, -0.1 * wa - (0.13 if P.get("belly") else 0.0), 1.10 if not P.get("belly") else 1.0)

    def arm(self, side):
        B, P = self.blob, self.P
        s, m, k = self.s, P["muscle"], P["arm"]
        sx = -1 if side.startswith("r") else 1
        S, E, W = self.J["shoulder_" + side], self.J["elbow_" + side], self.J["wrist_" + side]
        up = E - S
        fo = W - E
        bend = fo - up.normalized() * fo.dot(up.normalized())
        front = bend if bend.length > 0.02 * s else Vector((0, -1, 0))
        Ru = basis(up, front)
        out = Ru @ Vector((0, 0, 1)) * (1 if (Ru @ Vector((0, 0, 1))).x * sx > 0 else -1)
        Lu = up.length
        B.ball(S, 0.042 * s, soft=0.55)
        # Deltoid cap: rounds the shoulder past the torso (the heroic width), blended into chest and back.
        B.ell(S + up.normalized() * 0.055 * s + out * 0.012 * s + Vector((0, 0, 0.008 * s)),
              (0.082 * s, (0.05 + 0.01 * m) * k * s, (0.054 + 0.01 * m) * k * s), Ru, soft=0.55)
        B.cap(S, E, 0.04 * s * (0.85 + 0.15 * k), soft=0.55)
        fv = Ru @ Vector((0, 1, 0))
        B.ell(S + up * 0.56 + fv * 0.018 * s, (Lu * 0.3, (0.036 + 0.012 * m) * k * s, (0.036 + 0.01 * m) * k * s), Ru, soft=0.52)
        B.ell(S + up * 0.42 - fv * 0.022 * s, (Lu * 0.36, (0.036 + 0.01 * m) * k * s, (0.04 + 0.008 * m) * k * s), Ru, soft=0.52)
        B.ball(E, 0.034 * s * (0.85 + 0.15 * k), soft=0.55)
        Lf = fo.length
        palm_front = V(self.pose.get("arm_" + side, {}).get("palm", (0, -1, 0)))
        Rf = basis(fo, palm_front)
        B.ell(E + fo * 0.28, (Lf * 0.33, (0.036 + 0.008 * m) * k * s, (0.042 + 0.008 * m) * k * s), Rf, soft=0.55)
        B.cap(E + fo * 0.42, W, 0.026 * s * (0.9 + 0.1 * k), soft=0.55)
        self.frames["upper_" + side] = (S, Ru)
        self.frames["fore_" + side] = (E, Rf)
        self.hand(side)

    # ------------------------------------------------------------------ hands
    def hand_frame(self, side):
        """(origin at the wrist, rotation with columns: finger direction, palm normal, thumb-side axis).
        spec 'grip_axis': a shaft through the fist; the fingers wrap it and the thumb points along it."""
        spec = self.pose.get("arm_" + side, {})
        W, E = self.J["wrist_" + side], self.J["elbow_" + side]
        if spec.get("grip_axis") is not None:
            A = V(spec["grip_axis"]).normalized()
            F = V(spec.get("fingers", tuple(W - E)))
            X = F - A * F.dot(A)
            if X.length < 1e-4:
                X = A.orthogonal()
            X.normalize()
            Z = A if side.startswith("r") else -A
            Y = Z.cross(X)
            return W, Matrix((X, Y, Z)).transposed()
        fdir = V(spec.get("fingers", tuple(W - E)))
        pal = V(spec.get("palm", (0, -1, 0)))
        return W, basis(fdir, pal)

    def hand(self, side):
        """Hand from per-finger curls. kinds: open, relaxed, fist, grip, dhyana, varada, earth, anjali."""
        B, s = self.blob, self.s
        spec = self.pose.get("arm_" + side, {})
        kind = spec.get("hand", "relaxed")
        W, R = self.hand_frame(side)
        X, Y, Z = R @ Vector((1, 0, 0)), R @ Vector((0, 1, 0)), R @ Vector((0, 0, 1))
        th = 1 if side.startswith("r") else -1   # thumb lies on +Z for the right hand
        hk = 1.0 + 0.12 * (self.P["arm"] - 1)
        g = s * hk * 1.08
        palm = W + X * 0.05 * g
        B.ell(palm, (0.052 * g, 0.019 * g, 0.045 * g), R, soft=0.5)
        B.ell(W + X * 0.06 * g - Y * 0.004 * g - Z * th * 0.022 * g, (0.034 * g, 0.014 * g, 0.02 * g), R, soft=0.5)  # hypothenar
        B.ell(W + X * 0.035 * g + Y * 0.006 * g + Z * th * 0.024 * g, (0.03 * g, 0.016 * g, 0.022 * g), R, soft=0.5)  # thenar
        curls = {
            "open": [(4, 3, 2)] * 4, "relaxed": [(14, 16, 10), (17, 19, 12), (20, 22, 13), (24, 24, 15)],
            "fist": [(85, 95, 60)] * 4, "grip": [(78, 92, 58)] * 4, "dhyana": [(6, 8, 5)] * 4,
            "varada": [(6, 5, 3)] * 4, "earth": [(10, 12, 8)] * 4, "anjali": [(2, 2, 2)] * 4,
        }[kind]
        lens = [0.078, 0.086, 0.08, 0.064]
        spread = [-1.5, -0.5, 0.5, 1.5]
        tips = []
        for i in range(4):
            base = W + X * (0.096 - abs(spread[i]) * 0.004) * g + Z * (th * -spread[i] * 0.0205 * g)
            d = (X + Z * th * -spread[i] * 0.02).normalized()
            p = base
            seg = [0.46, 0.3, 0.24]
            r0 = [0.0112, 0.0108, 0.0102, 0.0091][i] * g
            ang = 0.0
            for j in range(3):
                ang += math.radians(curls[i][j])
                dj = (d * math.cos(ang) + Y * math.sin(ang)).normalized()
                q = p + dj * lens[i] * seg[j] * g
                B.cap(p, q, r0 * (1 - 0.08 * j), soft=0.42)
                p = q
            tips.append(p)
        # Thumb: from the base of the palm, opposing; across the fingers in a fist.
        tb = W + X * 0.022 * g + Z * th * 0.03 * g + Y * 0.008 * g
        if kind in ("fist", "grip"):
            dirs = [(X * 0.7 + Z * th * 0.55 + Y * 0.45), (X * 0.55 - Z * th * 0.2 + Y * 0.8), (X * 0.1 - Z * th * 0.7 + Y * 0.6)]
        elif kind == "anjali":
            dirs = [(X * 0.8 + Z * th * 0.4 + Y * 0.3), (X * 0.9 + Z * th * 0.2), (X * 1.0 + Z * th * 0.1)]
        else:
            dirs = [(X * 0.6 + Z * th * 0.7 + Y * 0.35), (X * 0.75 + Z * th * 0.55 + Y * 0.25), (X * 0.85 + Z * th * 0.4 + Y * 0.2)]
        p = tb
        for j, (dd, ln) in enumerate(zip(dirs, (0.04, 0.034, 0.028))):
            q = p + dd.normalized() * ln * g
            B.cap(p, q, (0.0138 - 0.0016 * j) * g, soft=0.42)
            p = q
        self.marks["palm_" + side] = palm
        self.marks["grip_" + side] = W + X * 0.058 * g + Y * 0.03 * g
        self.marks["tips_" + side] = tips
        self.frames["hand_" + side] = (W, R)

    # ------------------------------------------------------------------ legs
    def leg(self, side):
        B, P = self.blob, self.P
        s, m, k = self.s, P["muscle"], P["leg"]
        sx = -1 if side == "r" else 1
        Hj, K, A = self.J["hip_" + side], self.J["knee_" + side], self.J["ankle_" + side]
        th, sh = K - Hj, A - K
        Rt = basis(th, Vector((0, -1, 0)))
        fv, sv = Rt @ Vector((0, 1, 0)), Rt @ Vector((0, 0, 1))
        out = sv if sv.x * sx > 0 else -sv
        Lt = th.length
        B.cap(Hj, K, 0.06 * s * (0.85 + 0.15 * k), soft=0.58)
        B.ell(Hj + th * 0.46 + fv * 0.026 * s + out * 0.014 * s, (Lt * 0.42, (0.05 + 0.012 * m) * k * s, (0.058 + 0.012 * m) * k * s), Rt, soft=0.55)
        B.ell(Hj + th * 0.8 + fv * 0.022 * s - out * 0.032 * s, (0.068 * s, 0.04 * k * s, 0.04 * k * s), Rt, soft=0.55)
        B.ell(Hj + th * 0.3 - out * 0.034 * s, (Lt * 0.3, 0.048 * k * s, 0.044 * k * s), Rt, soft=0.58)
        B.ell(Hj + th * 0.48 - fv * 0.03 * s, (Lt * 0.36, 0.048 * k * s, 0.052 * k * s), Rt, soft=0.58)
        B.ball(K, 0.042 * s, soft=0.58)
        B.ell(K + fv * 0.036 * s + Vector((0, 0, 0.006 * s)), (0.026 * s, 0.016 * s, 0.028 * s), Rt, soft=0.5)
        Rs = basis(sh, Vector((0, -1, 0)))
        fs, ss = Rs @ Vector((0, 1, 0)), Rs @ Vector((0, 0, 1))
        Ls = sh.length
        B.cap(K, A, 0.035 * s, soft=0.55)
        for side_k in (-1, 1):
            B.ell(K + sh * 0.26 - fs * 0.036 * s + ss * side_k * 0.017 * s, (Ls * 0.24, (0.044 + 0.008 * m) * k * s, (0.034 + 0.006 * m) * k * s), Rs, soft=0.55)
        B.ell(K + sh * 0.5 - fs * 0.026 * s, (Ls * 0.24, 0.033 * k * s, 0.038 * k * s), Rs, soft=0.58)
        B.ell(K + sh * 0.25 + fs * 0.012 * s + out * 0.012 * s, (Ls * 0.26, 0.022 * s, 0.024 * s), Rs, soft=0.55)
        B.ball(A, 0.034 * s, soft=0.55)
        self.foot(side)
        self.frames["thigh_" + side] = (Hj, Rt)
        self.frames["shin_" + side] = (K, Rs)

    def foot(self, side, sole_z=None):
        B, s = self.blob, self.s
        A = self.J["ankle_" + side]
        f = self.J["toe_dir_" + side]
        if self.seated:
            Rf = basis(f, Vector((0, 0.3, 1)))      # sole turned up on the opposite thigh
        else:
            f = Vector((f.x, f.y, 0)).normalized()
            Rf = basis(f, Vector((0, 0, -1)))
        X, Yd, Z = Rf @ Vector((1, 0, 0)), Rf @ Vector((0, 1, 0)), Rf @ Vector((0, 0, 1))
        heel = A - X * 0.028 * s + Yd * 0.04 * s
        B.ell(heel, (0.04 * s, 0.036 * s, 0.034 * s), Rf, soft=0.5)
        B.ell(A + X * 0.072 * s + Yd * 0.04 * s, (0.098 * s, 0.032 * s, 0.043 * s), Rf, soft=0.52)
        B.ell(A + X * 0.022 * s + Yd * 0.01 * s, (0.05 * s, 0.032 * s, 0.033 * s), Rf, soft=0.55)
        th = 1 if side == "r" else -1   # big toe on the inside (+Z is medial for the right foot)
        for i, (ln, r) in enumerate(((0.045, 0.0128), (0.038, 0.0098), (0.034, 0.0092), (0.029, 0.0086), (0.024, 0.008))):
            zoff = th * (0.026 - i * 0.0135) * s
            b = A + X * (0.155 - i * 0.008) * s + Yd * 0.058 * s + Z * zoff
            B.cap(b, b + X * ln * s + Yd * 0.003 * s, r * s, soft=0.42)
        self.frames["foot_" + side] = (A, Rf)

    def seated_leg(self, side):
        B, P, s = self.blob, self.P, self.s
        k = P["leg"]
        Hj, K, A = self.J["hip_" + side], self.J["knee_" + side], self.J["ankle_" + side]
        th, sh = K - Hj, A - K
        Rt = basis(th, Vector((0, 0, 1)))
        B.cap(Hj, K, 0.066 * s * k, soft=0.55)
        B.ell(Hj + th * 0.45 + Vector((0, 0, 0.02 * s)), (th.length * 0.42, 0.06 * k * s, 0.062 * k * s), Rt, soft=0.5)
        B.ball(K, 0.05 * s, soft=0.5)
        Rs = basis(sh, Vector((0, 0, 1)))
        B.cap(K, A, 0.038 * s, soft=0.5)
        B.ell(K + sh * 0.3 - Vector((0, 0, 0.012 * s)), (sh.length * 0.26, 0.045 * k * s, 0.04 * k * s), Rs, soft=0.5)
        B.ball(A, 0.031 * s, soft=0.5)
        self.foot(side)
        if side == "l":
            # The lap: a seated image reads as one broad, solid base under the hands.
            z0 = self.J["hip_r"].z - 0.10 * s
            B.ell(Vector((0, -0.17 * s, z0 + 0.085 * s)), (0.36 * s, 0.17 * s, 0.07 * s), None, soft=0.7)
        self.frames["thigh_" + side] = (Hj, Rt)
        self.frames["shin_" + side] = (K, Rs)

    # ------------------------------------------------------------------ head space
    def hp(self, x, y, z):
        """Head-space point in head units H (origin at the head centre, -y forward) -> world."""
        c, R = self.frames["head"]
        return c + R @ Vector((x * self.H, y * self.H, z * self.H))

    def head_rot(self):
        return self.frames["head"][1]
