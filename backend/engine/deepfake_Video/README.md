# 🛡️ DeepGuard — Deepfake Detection System

ViT-powered deepfake detector: Flask backend + professional web UI.

---

## 📁 ملفات المشروع

```
deepfake_Video/
├── backend.py      ← سيرفر Flask (منطق الذكاء الاصطناعي)
├── index.html      ← واجهة الويب الاحترافية
└── README.md
```

---

## 🚀 تشغيل السيرفر

### 1. تثبيت المتطلبات

```bash
pip install flask flask-cors transformers facenet-pytorch \
            opencv-python Pillow torch torchvision numpy
```

### 2. تشغيل Backend

```bash
python backend.py
```

السيرفر سيشتغل على: `http://localhost:5000`

### 3. فتح الواجهة

افتح `index.html` في المتصفح مباشرة، أو شغّل سيرفر محلي:

```bash
python -m http.server 8080
# ثم افتح: http://localhost:8080
```

---

## 🔌 API Endpoints

| Endpoint | Method | وصف |
|---|---|---|
| `GET  /api/health` | GET | فحص حالة السيرفر |
| `POST /api/analyze` | POST | تحليل فيديو (multipart: `video`) |
| `POST /api/analyze/image` | POST | تحليل صورة (multipart: `image`) |

### مثال — تحليل فيديو

```bash
curl -X POST http://localhost:5000/api/analyze \
     -F "video=@my_video.mp4"
```

### مثال — تحليل صورة

```bash
curl -X POST http://localhost:5000/api/analyze/image \
     -F "image=@face.jpg"
```

---

## 📊 نظام التقييم

| Composite Score | الحكم |
|---|---|
| < 30% | ✅ REAL |
| 30% – 50% | ⚠️ UNCERTAIN |
| > 50% | 🚨 DEEPFAKE |

**Composite Score** = (متوسط الاحتمال × 50%) + (% فريمات > 60% × 50%)

---

## 🧠 الموديل

- **الاسم:** `prithivMLmods/Deep-Fake-Detector-v2-Model`
- **المعمارية:** ViT-Base/16 (fine-tuned)
- **Accuracy:** 92.12%
- **Deepfake Recall:** 97.15%
- **F1:** 0.9249
- **Training data:** 56,001 صورة real + deepfake

---

## 🎛️ إعدادات قابلة للتعديل (backend.py)

```python
MAX_FRAMES          = 60     # أقصى عدد فريمات للتحليل
FRAME_INTERVAL_SEC  = 0.5    # تحليل فريم كل X ثانية
THRESHOLD_REAL      = 0.30   # دون هذا → Real
THRESHOLD_UNCERTAIN = 0.50   # بين الاثنين → Uncertain
```
