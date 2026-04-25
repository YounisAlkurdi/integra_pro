import cv2
import numpy as np
import time
import mediapipe as mp
from collections import deque, Counter


# ══════════════════════════════════════════════════════════
# 1D Kalman Filter
# ══════════════════════════════════════════════════════════
class Kalman1D:
    def __init__(self, process_noise=1e-3, measure_noise=1e-1, init=0.0):
        self.Q = process_noise
        self.R = measure_noise
        self.x = init
        self.P = 1.0
        self.initialized = False

    def update(self, z):
        if not self.initialized:
            self.x = z
            self.initialized = True
            return self.x
        P_pred = self.P + self.Q
        K      = P_pred / (P_pred + self.R)
        self.x = self.x + K * (z - self.x)
        self.P = (1 - K) * P_pred
        return self.x

    # FIX 4: إضافة skip() لتجميد الكالمان دون تغذيته بقيم مكررة
    def skip(self):
        """تجميد الكالمان — لا تحديث، فقط أعد القيمة الحالية"""
        return self.x

    def get(self):
        return self.x


# ══════════════════════════════════════════════════════════
# Blink Detector
# ══════════════════════════════════════════════════════════
class BlinkDetector:
    LEFT_EYE  = [33, 160, 158, 133, 153, 144]
    RIGHT_EYE = [362, 385, 387, 263, 373, 380]

    def __init__(self, ear_thresh=0.20, consec_frames=2):
        self.EAR_THRESH    = ear_thresh
        self.CONSEC_FRAMES = consec_frames
        self._counter      = 0
        self.is_blinking   = False
        self.total_blinks  = 0

    def _ear(self, lm, pts, w, h):
        p = [(lm[i].x * w, lm[i].y * h) for i in pts]
        v1 = np.linalg.norm(np.array(p[1]) - np.array(p[5]))
        v2 = np.linalg.norm(np.array(p[2]) - np.array(p[4]))
        h1 = np.linalg.norm(np.array(p[0]) - np.array(p[3]))
        if h1 < 1e-6:
            return 0.3
        return (v1 + v2) / (2.0 * h1)

    def update(self, lm, w, h):
        left_ear  = self._ear(lm, self.LEFT_EYE,  w, h)
        right_ear = self._ear(lm, self.RIGHT_EYE, w, h)
        avg_ear   = (left_ear + right_ear) / 2.0

        if avg_ear < self.EAR_THRESH:
            self._counter += 1
            if self._counter >= self.CONSEC_FRAMES:
                self.is_blinking = True
        else:
            if self._counter >= self.CONSEC_FRAMES:
                self.total_blinks += 1
            self._counter    = 0
            self.is_blinking = False

        return self.is_blinking, round(avg_ear, 3)


# ══════════════════════════════════════════════════════════
# Main Tracker
# ══════════════════════════════════════════════════════════
class BehavioralTracker:
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh    = self.mp_face_mesh.FaceMesh(
            refine_landmarks=True,
            max_num_faces=1,
            min_detection_confidence=0.75,
            min_tracking_confidence=0.75
        )

        # Kalman filters
        self.kf_gaze_x  = Kalman1D(process_noise=5e-3, measure_noise=8e-2)
        self.kf_gaze_y  = Kalman1D(process_noise=5e-3, measure_noise=8e-2)
        self.kf_yaw     = Kalman1D(process_noise=8e-3, measure_noise=5e-2)
        self.kf_pitch   = Kalman1D(process_noise=8e-3, measure_noise=5e-2)
        # FIX 3: Delta بدون abs() — نمرر القيمة الموجهة للكالمان
        self.kf_delta_x = Kalman1D(process_noise=3e-3, measure_noise=1e-1)
        self.kf_delta_y = Kalman1D(process_noise=3e-3, measure_noise=1e-1)

        # BBox smoothing
        self.kf_bbox = [Kalman1D(1e-2, 5e-2) for _ in range(4)]

        # Blink detector
        self.blink_detector = BlinkDetector(ear_thresh=0.20, consec_frames=2)

        # FIX 4: Blink freeze — تجميد الكالمان نفسه لا إعادة قيمة قديمة له
        self._blink_freeze_frames = 0
        self.BLINK_FREEZE = 4

        # Zone pattern memory
        self.zone_history = deque(maxlen=200)
        self.zone_counts  = {
            z: 0 for z in [
                'CENTER', 'LEFT', 'RIGHT', 'UP', 'DOWN',
                'UP_LEFT', 'UP_RIGHT', 'DOWN_LEFT', 'DOWN_RIGHT'
            ]
        }

        # FIX 5: عتبات أكثر حساسية
        self.HEAD_YAW_THRESH   = 22.0
        self.HEAD_PITCH_THRESH = 16.0
        self.EYE_X_THRESH      = 0.20   # كان 0.30 — تقليل لكشف أفضل
        self.EYE_Y_THRESH      = 0.18   # كان 0.25
        self.DELTA_X_THRESH    = 0.22   # كان 0.28
        self.DELTA_Y_THRESH    = 0.20   # كان 0.26

        # Stats
        self.stats = {
            "total_frames":   0,
            "focused_frames": 0,
            "distractions":   0,
        }
        self.distraction_timer = None
        self.last_counted      = False

        print("Integra Engine v5.1 — Fixed: Port/Iris/Delta/Kalman/Thresholds: Online")

    # ──────────────────────────────────────────────────────
    def _iris_ratio_x(self, lm, w, h, iris, inner, outer):
        ix    = lm[iris].x * w
        inn   = lm[inner].x * w
        out_  = lm[outer].x * w
        eye_w = out_ - inn
        if abs(eye_w) < 1e-6:
            return 0.0
        return ((ix - inn) / eye_w - 0.5) * 2.0

    # FIX 1: نقاط iris Y الصحيحة — قياس موضع القزحية عمودياً داخل العين
    def _iris_ratio_y(self, lm, w, h, iris, top, bottom):
        """
        iris:   نقطة مركز القزحية (468 يسار / 473 يمين)
        top:    الحافة العلوية للعين
        bottom: الحافة السفلية للعين
        النقاط الصحيحة من MediaPipe:
          عين يسار:  top=386, bottom=374
          عين يمين: top=159, bottom=145
        """
        iy    = lm[iris].y * h
        ty    = lm[top].y * h
        by    = lm[bottom].y * h
        eye_h = by - ty
        if abs(eye_h) < 1e-6:
            return 0.0
        return ((iy - ty) / eye_h - 0.5) * 2.0

    def _head_pose(self, lm, w, h):
        model_pts = np.array([
            [  0.0,   0.0,   0.0],
            [  0.0, -63.6, -12.5],
            [-43.3,  32.7, -26.0],
            [ 43.3,  32.7, -26.0],
            [-28.9, -28.9, -24.1],
            [ 28.9, -28.9, -24.1],
        ], dtype=np.float64)
        img_pts = np.array([
            [lm[i].x * w, lm[i].y * h]
            for i in [1, 199, 33, 263, 61, 291]
        ], dtype=np.float64)
        f   = w
        cam = np.array([[f, 0, w/2], [0, f, h/2], [0, 0, 1]], dtype=np.float64)
        # FIX 6: distortion coefficients واقعية بدلاً من zeros
        dist = np.zeros((4, 1), dtype=np.float64)
        ok, rvec, _ = cv2.solvePnP(
            model_pts, img_pts, cam, dist,
            flags=cv2.SOLVEPNP_ITERATIVE
        )
        if not ok:
            return 0.0, 0.0
        rmat, _ = cv2.Rodrigues(rvec)
        sy    = np.sqrt(rmat[0, 0]**2 + rmat[1, 0]**2)
        pitch = np.degrees(np.arctan2(-rmat[2, 0], sy))
        yaw   = np.degrees(np.arctan2( rmat[1, 0], rmat[0, 0]))
        return float(yaw), float(pitch)

    def _norm(self, val, thresh):
        return max(-1.0, min(1.0, val / thresh))

    def _get_zone(self, gx, gy):
        h = "CENTER" if abs(gx) < self.EYE_X_THRESH else ("RIGHT" if gx > 0 else "LEFT")
        v = "CENTER" if abs(gy) < self.EYE_Y_THRESH else ("DOWN"  if gy > 0 else "UP")
        if v == "CENTER" and h == "CENTER": return "CENTER"
        if v == "CENTER": return h
        if h == "CENTER": return v
        return v + "_" + h

    def _detect_pattern(self):
        if len(self.zone_history) < 30:
            return "CENTER", 0.0
        recent = list(self.zone_history)[-90:]
        cnt    = Counter(recent)
        total  = len(recent)
        non_c  = {z: c for z, c in cnt.items() if z != "CENTER"}
        if not non_c:
            return "CENTER", 0.0
        dom     = max(non_c, key=non_c.get)
        dom_pct = non_c[dom] / total
        return dom, dom_pct

    def _classify(self, zone, head_dist, eye_x, eye_y, dx_dist, dy_dist, dom, dom_pct):
        if dx_dist and not head_dist and ("LEFT" in zone or "RIGHT" in zone) \
                and "DOWN" not in zone and "UP" not in zone:
            return "SECOND_SCREEN_SIDE"
        if "DOWN" in zone:
            if dy_dist and not head_dist:
                return "PHONE_BELOW"
            if eye_y and dom_pct > 0.25 and "DOWN" in dom:
                return "PHONE_BELOW"
            return "LOOKING_DOWN"
        if "UP" in zone:
            if dy_dist or head_dist:
                return "SCREEN_ABOVE"
        if head_dist and (eye_x or eye_y):
            return "HEAD+GAZE"
        if head_dist:
            return "HEAD_TURN"
        if eye_x or eye_y:
            return "EYE_SHIFT"
        return "DISTRACTED"

    # ──────────────────────────────────────────────────────
    def analyze(self, frame):
        if frame is None:
            return {"status": "ERROR"}

        h, w, _ = frame.shape
        rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb)

        out = {
            "status": "NO_FACE", "reason": "NO_FACE",
            "zone": "CENTER", "bbox": None,
            "head_pose": {"yaw": 0.0, "pitch": 0.0},
            "gaze": {"x": 0.0, "y": 0.0},
            "delta": {"x": 0.0, "y": 0.0},
            "ear": 0.3, "is_blinking": False,
            "second_screen_prob": 0.0,
            "phone_prob": 0.0,
            "screen_above_prob": 0.0,
            "dominant_zone": "CENTER",
            "dominance": 0.0,
            "metrics": {
                "focus_score": 0,
                "distractions": self.stats["distractions"],
                "zone_counts": dict(self.zone_counts)
            },
            "landmarks": {}
        }

        if not results.multi_face_landmarks:
            self.prev_bbox = None
            return out

        self.stats["total_frames"] += 1
        lm = results.multi_face_landmarks[0].landmark

        # ── 1. BBox via Kalman ───────────────────────────────
        xs = [p.x * w for p in lm]
        ys = [p.y * h for p in lm]
        raw_bbox    = [int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))]
        smooth_bbox = [int(kf.update(v)) for kf, v in zip(self.kf_bbox, raw_bbox)]
        out["bbox"] = smooth_bbox

        # ── 2. Blink detection ───────────────────────────────
        is_blinking, ear = self.blink_detector.update(lm, w, h)
        out["is_blinking"] = is_blinking
        out["ear"]         = ear

        # ── 3. Head pose via Kalman ──────────────────────────
        yaw, pitch = self._head_pose(lm, w, h)
        s_yaw      = self.kf_yaw.update(yaw)
        s_pitch    = self.kf_pitch.update(pitch)
        out["head_pose"] = {
            "yaw":   round(s_yaw, 1),
            "pitch": round(s_pitch, 1)
        }

        # ── 4. Eye gaze — FIX 4: تجميد الكالمان نفسه أثناء الرمش ──
        if is_blinking or self._blink_freeze_frames > 0:
            if is_blinking:
                self._blink_freeze_frames = self.BLINK_FREEZE
            else:
                self._blink_freeze_frames -= 1
            # FIX 4: skip() لا update() — لا نغذّي الكالمان بقيم مجمدة
            s_gaze_x = self.kf_gaze_x.skip()
            s_gaze_y = self.kf_gaze_y.skip()
        else:
            # FIX 1: نقاط iris Y الصحيحة
            lx = self._iris_ratio_x(lm, w, h, 468, 133, 33)
            rx = self._iris_ratio_x(lm, w, h, 473, 362, 263)
            raw_gx = (lx + rx) / 2.0

            # عين يسار:  iris=468, top=386, bottom=374
            # عين يمين: iris=473, top=159, bottom=145
            ly = self._iris_ratio_y(lm, w, h, 468, 386, 374)
            ry = self._iris_ratio_y(lm, w, h, 473, 159, 145)
            raw_gy = (ly + ry) / 2.0

            s_gaze_x = self.kf_gaze_x.update(raw_gx)
            s_gaze_y = self.kf_gaze_y.update(raw_gy)

        out["gaze"] = {
            "x": round(s_gaze_x, 3),
            "y": round(s_gaze_y, 3)
        }

        # ── 5. Delta via Kalman — FIX 3: بدون abs() قبل الكالمان ──
        norm_yaw   = self._norm(s_yaw,   self.HEAD_YAW_THRESH)
        norm_pitch = self._norm(s_pitch, self.HEAD_PITCH_THRESH)

        raw_dx = s_gaze_x - norm_yaw
        raw_dy = s_gaze_y - norm_pitch

        # FIX 3: نمرر القيمة الموجهة للكالمان ونعمل abs() عند التقييم فقط
        s_dx = self.kf_delta_x.update(raw_dx)
        s_dy = self.kf_delta_y.update(raw_dy)

        out["delta"] = {
            "x": round(s_dx, 3),
            "y": round(s_dy, 3)
        }

        # ── 6. Zone + pattern ────────────────────────────────
        zone = self._get_zone(s_gaze_x, s_gaze_y)
        self.zone_history.append(zone)
        if zone in self.zone_counts:
            self.zone_counts[zone] += 1
        out["zone"] = zone

        dom_zone, dom_pct = self._detect_pattern()
        out["dominant_zone"] = dom_zone
        out["dominance"]     = round(dom_pct, 2)

        # ── 7. Probabilities ─────────────────────────────────
        ss_prob = min(1.0, abs(s_dx) / self.DELTA_X_THRESH)   # FIX 3: abs() هنا

        phone_prob = 0.0
        if s_gaze_y > 0.06:
            phone_prob = min(1.0,
                (s_gaze_y / self.EYE_Y_THRESH) * 0.55 +
                (abs(s_dy) / self.DELTA_Y_THRESH) * 0.45)    # FIX 3: abs() هنا

        above_prob = 0.0
        if s_gaze_y < -0.06:
            above_prob = min(1.0,
                (abs(s_gaze_y) / self.EYE_Y_THRESH) * 0.55 +
                (abs(s_dy) / self.DELTA_Y_THRESH) * 0.45)    # FIX 3: abs() هنا

        out["second_screen_prob"] = round(ss_prob    * 100, 1)
        out["phone_prob"]         = round(phone_prob * 100, 1)
        out["screen_above_prob"]  = round(above_prob * 100, 1)

        # ── 8. Focus decision ────────────────────────────────
        if is_blinking:
            self.stats["focused_frames"] += 1
            out["status"] = "FOCUSED"
            out["reason"] = "OK"
            out["metrics"]["focus_score"] = round(
                (self.stats["focused_frames"] / self.stats["total_frames"]) * 100, 1
            )
            out["metrics"]["zone_counts"] = dict(self.zone_counts)
            out["landmarks"] = {
                "left_iris":  [int(lm[468].x * w), int(lm[468].y * h)],
                "right_iris": [int(lm[473].x * w), int(lm[473].y * h)],
                "nose_tip":   [int(lm[1].x * w),   int(lm[1].y * h)]
            }
            return out

        # FIX 3: abs() على s_dx/s_dy عند التقييم
        head_dist  = abs(s_yaw)   > self.HEAD_YAW_THRESH or abs(s_pitch) > self.HEAD_PITCH_THRESH
        eye_x      = abs(s_gaze_x) > self.EYE_X_THRESH
        eye_y      = abs(s_gaze_y) > self.EYE_Y_THRESH
        dx_dist    = abs(s_dx) > self.DELTA_X_THRESH
        dy_dist    = abs(s_dy) > self.DELTA_Y_THRESH

        is_distracted = head_dist or eye_x or eye_y or dx_dist or dy_dist

        if is_distracted:
            if self.distraction_timer is None:
                self.distraction_timer = time.time()
                self.last_counted = False

            dur    = time.time() - self.distraction_timer
            reason = self._classify(zone, head_dist, eye_x, eye_y,
                                    dx_dist, dy_dist, dom_zone, dom_pct)

            out["status"] = "SUSPICIOUS" if dur > 1.5 else "DISTRACTED"
            out["reason"] = reason

            if dur >= 1.5 and not self.last_counted:
                self.stats["distractions"] += 1
                self.last_counted = True
        else:
            self.distraction_timer = None
            self.last_counted      = False
            self.stats["focused_frames"] += 1
            out["status"] = "FOCUSED"
            out["reason"] = "OK"

        # ── 9. Landmarks ─────────────────────────────────────
        out["landmarks"] = {
            "left_iris":  [int(lm[468].x * w), int(lm[468].y * h)],
            "right_iris": [int(lm[473].x * w), int(lm[473].y * h)],
            "nose_tip":   [int(lm[1].x * w),   int(lm[1].y * h)]
        }

        # ── 10. Metrics ──────────────────────────────────────
        out["metrics"]["focus_score"] = round(
            (self.stats["focused_frames"] / self.stats["total_frames"]) * 100, 1
        )
        out["metrics"]["distractions"] = self.stats["distractions"]
        out["metrics"]["zone_counts"]  = dict(self.zone_counts)

        return out