# 📁 تنظيم المشروع — Project Structure Reorganization

## الوضع الحالي (مبعثر 😬)

```
c:\tist_integra\
├── appointments.html       ← Frontend
├── appointments.js         ← Frontend
├── auth.py                 ← Backend
├── checkout-card.css       ← Frontend
├── checkout.html           ← Frontend
├── checkout.js             ← Frontend
├── config.js               ← Frontend
├── dashboard.html          ← Frontend
├── dashboard.js            ← Frontend
├── index.html              ← Frontend
├── integra-session.css     ← Frontend
├── integra-session.html    ← Frontend
├── integra-session.js      ← Frontend
├── livekit-session.js      ← Frontend
├── livekit_error.txt       ← ❌ Debug junk
├── livekit_routes.py       ← Backend
├── login.html              ← Frontend
├── login.js                ← Frontend
├── logs.py                 ← Backend
├── main.py                 ← Backend
├── nodes.py                ← Backend
├── nodes_buffer.json       ← ❌ سيُحذف
├── payments.py             ← Backend
├── pricing.html            ← Frontend
├── pricing.js              ← Frontend
├── pricing.json            ← Data (مشترك)
├── reports.css             ← Frontend
├── reports.html            ← Frontend
├── reports.js              ← Frontend
├── requirements.txt        ← Backend
├── script.js               ← Frontend
├── security_threats.log    ← ❌ log ملف
├── settings.js             ← Frontend Config
├── style.css               ← Frontend
├── stt.js                  ← Frontend
├── supabase-client.js      ← Frontend
├── utils.py                ← Backend
├── Design/                 ← Assets
├── Images/                 ← Assets
├── Spline_Skill/           ← Assets
├── frames/                 ← Assets
├── video/                  ← Assets
└── _INTEGRA_DOCS/          ← Documentation
```

---

## الهيكل المقترح ✨

```
c:\tist_integra\
│
├── 📂 backend/                    ← كل كود Python
│   ├── main.py                    ← App entry point
│   ├── auth.py                    ← JWT verification
│   ├── nodes.py                   ← Interview nodes logic
│   ├── payments.py                ← Stripe payments
│   ├── livekit_routes.py          ← LiveKit tokens
│   ├── logs.py                    ← Logging utilities
│   ├── utils.py                   ← Shared helpers
│   ├── requirements.txt
│   └── 📂 routes/                 ← Router modules (مستقبلاً)
│       ├── reports.py
│       ├── subscriptions.py
│       └── webhook.py
│
├── 📂 frontend/                   ← كل ملفات الواجهة
│   ├── 📂 pages/                  ← HTML pages
│   │   ├── index.html             ← Landing page
│   │   ├── login.html
│   │   ├── dashboard.html
│   │   ├── appointments.html
│   │   ├── reports.html
│   │   ├── pricing.html
│   │   ├── checkout.html
│   │   ├── integra-session.html
│   │   ├── profile.html           ← جديد ✨
│   │   ├── billing.html           ← جديد ✨
│   │   ├── join.html              ← صفحة QR ✨
│   │   └── candidate.html         ← جديد ✨
│   │
│   ├── 📂 js/                     ← JavaScript files
│   │   ├── 📂 core/               ← مكتبات مشتركة
│   │   │   ├── settings.js        ← Config (SUPABASE_URL, etc.)
│   │   │   ├── supabase-client.js ← Supabase init
│   │   │   ├── auth-guard.js      ← مشترك: التحقق من الجلسة
│   │   │   └── stt.js             ← STT Engine
│   │   │
│   │   ├── 📂 pages/              ← Page-specific JS
│   │   │   ├── login.js
│   │   │   ├── dashboard.js
│   │   │   ├── appointments.js
│   │   │   ├── reports.js
│   │   │   ├── pricing.js
│   │   │   ├── checkout.js
│   │   │   ├── integra-session.js
│   │   │   ├── livekit-session.js
│   │   │   └── script.js          ← index page
│   │   │
│   │   └── 📂 utils/              ← مساعدات مشتركة
│   │       ├── ui-helpers.js      ← Toast, Modal, Loading
│   │       ├── date-utils.js      ← تنسيق التواريخ
│   │       └── api-client.js      ← Fetch wrapper
│   │
│   └── 📂 css/                    ← Stylesheets
│       ├── style.css              ← Global styles
│       ├── checkout-card.css
│       ├── integra-session.css
│       └── reports.css
│
├── 📂 assets/                     ← Static assets
│   ├── 📂 images/                 ← (محتوى Images/)
│   ├── 📂 video/                  ← (محتوى video/)
│   ├── 📂 design/                 ← (محتوى Design/)
│   └── 📂 frames/                 ← (محتوى frames/)
│
├── 📂 data/                       ← Data files
│   └── pricing.json               ← Pricing tiers
│
├── 📂 _INTEGRA_DOCS/              ← Documentation
│   ├── 00_README.md
│   └── ...
│
├── .env                           ← Environment variables
├── .gitignore
└── README.md
```

---

## خطوات التنظيم (Migration Steps)

> **⚠️ افعل هذا فقط بعد git commit لضمان إمكانية الرجوع**

### الخطوة 1: إنشاء المجلدات
```powershell
cd c:\tist_integra

mkdir backend\routes
mkdir frontend\pages
mkdir frontend\js\core
mkdir frontend\js\pages
mkdir frontend\js\utils
mkdir frontend\css
mkdir assets\images
mkdir assets\video
mkdir assets\design
mkdir assets\frames
mkdir data
```

### الخطوة 2: نقل ملفات Python
```powershell
Move-Item main.py, auth.py, nodes.py, payments.py, livekit_routes.py, logs.py, utils.py, requirements.txt backend\
```

### الخطوة 3: نقل HTML
```powershell
Move-Item index.html, login.html, dashboard.html, appointments.html, reports.html, pricing.html, checkout.html, integra-session.html frontend\pages\
```

### الخطوة 4: نقل JS
```powershell
Move-Item settings.js, supabase-client.js, stt.js frontend\js\core\
Move-Item login.js, dashboard.js, appointments.js, reports.js, pricing.js, checkout.js, integra-session.js, livekit-session.js, script.js frontend\js\pages\
```

### الخطوة 5: نقل CSS
```powershell
Move-Item style.css, checkout-card.css, integra-session.css, reports.css frontend\css\
```

### الخطوة 6: نقل Assets
```powershell
Move-Item Images\* assets\images\
Move-Item video\* assets\video\
Move-Item Design\* assets\design\
Move-Item frames\* assets\frames\
Move-Item pricing.json data\
```

### الخطوة 7: حذف الملفات غير المطلوبة
```powershell
Remove-Item nodes_buffer.json  # بعد الترحيل لـ Supabase
Remove-Item livekit_error.txt
Remove-Item security_threats.log  # بعد إضافة proper logging
```

### الخطوة 8: تحديث المسارات في HTML
في كل HTML page غيّر المسارات:
```html
<!-- قبل: -->
<script src="settings.js"></script>
<script src="supabase-client.js"></script>

<!-- بعد: -->
<script src="../js/core/settings.js"></script>
<script src="../js/core/supabase-client.js"></script>
```

### الخطوة 9: تشغيل Backend من المجلد الجديد
```python
# backend/main.py — تحقق من مسارات الـ imports:
# لا تغيير في Python imports لأنها relative
```

---

## ملفات يجب إضافتها في `.gitignore`
```
# Python
__pycache__/
*.pyc
.env

# Logs
*.log
livekit_error.txt

# Data buffers (لا ترفع)
nodes_buffer.json
security_threats.log

# OS
.DS_Store
Thumbs.db

# Editor
.vscode/settings.json
```

---

## بديل خفيف: تنظيم الجذر دون نقل ملفات

إذا لم تريد نقل الملفات الآن، يمكنك الإبقاء على البنية الحالية مع تسمية واضحة للملفات:

| الفئة | الملفات |
|-------|---------|
| **Core Config** | `settings.js`, `supabase-client.js`, `config.js` |
| **Pages** | `index.html`, `login.html`, `dashboard.html`, ... |
| **Backend** | `main.py`, `auth.py`, `nodes.py`, `payments.py`, ... |
| **Styles** | `style.css`, `checkout-card.css`, `reports.css`, ... |
| **Docs** | `_INTEGRA_DOCS/` |
