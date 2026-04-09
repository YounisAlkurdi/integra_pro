# 🚀 INTEGRA — Starter Prompt (انسخ هذا عند بداية كل جلسة)

---

## انسخ النص أدناه كاملاً:

---

```
أنت مساعد تطوير خبير أعمل معك على مشروع اسمه **Integra** — منصة مقابلات ذكية مدعومة بالذكاء الاصطناعي.

## 🗂️ المشروع
- **المسار:** `c:\tist_integra\`
- **Backend:** FastAPI (Python) — `main.py`, `auth.py`, `nodes.py`, `payments.py`, `livekit_routes.py`
- **Frontend:** Vanilla JS + HTML — لا frameworks
- **DB:** Supabase (PostgreSQL) مع RLS
- **Video:** LiveKit (WebRTC)
- **Payments:** Stripe
- **STT:** Web Speech API (Chrome/Edge فقط)

## 🗄️ جداول Supabase (الموجودة)
- `nodes` — بيانات المقابلات (room_id, candidate_name, candidate_email, position, status, scheduled_at, user_id)
- `subscriptions` — اشتراكات المستخدمين (plan_id, status, interviews_limit, interviews_computed)
- `invoices` — الفواتير (user_id, amount, plan_id, payment_intent_id, status)
- `interview_reports` — تقارير AI (room_id, user_id, score, strengths, weaknesses, ai_summary)
- `chat_logs` — سجل المحادثة (room_id, user_id, sender, message)

## ⚠️ المشاكل الحالية (مهمة جداً)
1. `nodes.py` لا يزال يكتب في `nodes_buffer.json` بدلاً من Supabase ← يجب الإصلاح
2. لا يوجد Stripe Webhook → المستخدم يدفع لكن لا يُحدَّث subscription
3. `SUPABASE_JWT_SECRET` فارغ → JWT verification معطّل
4. `chat_logs` لا تُحفظ بعد كل STT event
5. `interview_reports` تعرض أرقام عشوائية لا بيانات حقيقية

## 📄 الصفحات الموجودة
index.html, login.html, dashboard.html, appointments.html,
reports.html, pricing.html, checkout.html, integra-session.html

## 📄 الصفحات الناقصة (يجب بناؤها)
- `join.html` — صفحة انضمام المرشح عبر QR (أعلى أولوية)
- `profile.html` — ملف المستخدم + إدارة الاشتراك
- `billing.html` — تاريخ الفواتير

## 📱 QR System (مُصمَّم، لم يُنفَّذ بعد)
- Backend: `GET /api/nodes/{room_id}/qr` يُولّد QR image (base64)
- يتطلب: `pip install qrcode[pil]`
- صفحة `join.html` يفتحها المرشح بعد مسح QR — بدون تسجيل دخول

## 🔐 أمان
- الانتاج يحتاج: SUPABASE_JWT_SECRET, STRIPE_WEBHOOK_SECRET, ENVIRONMENT=production
- لا rate limiting موجود حالياً

## 📁 التوثيق الشامل
يوجد في `c:\tist_integra\_INTEGRA_DOCS\` — 15 ملف يغطي كل شيء:
- `07_BUGS_ISSUES.md` — قائمة المشاكل
- `08_IMPROVEMENT_PLAN.md` — خطة التطوير
- `11_SECURITY_AUDIT.md` — تحليل الأمان
- `14_QR_INTEGRATION.md` — نظام QR الكامل

## 🎯 مهمتي الآن
[اكتب هنا ما تريد العمل عليه — مثال:]
- "أريد بناء join.html وربطها بـ QR system"
- "أريد إصلاح nodes.py ليكتب في Supabase"
- "أريد إضافة Stripe Webhook"
- "أريد بناء profile.html"
```

---

## 📌 نصائح الاستخدام

### إذا أردت البدء بمهمة محددة، استبدل آخر سطر بـ:

**لبناء QR + join.html:**
```
أريد تنفيذ نظام QR الكامل: بناء join.html + إضافة endpoint /api/nodes/{room_id}/qr في livekit_routes.py
راجع الخطة في _INTEGRA_DOCS/14_QR_INTEGRATION.md واتبعها.
```

**لإصلاح nodes.py:**
```
أريد ترحيل nodes.py من nodes_buffer.json إلى Supabase.
الجدول اسمه nodes وعمود الـ PK هو room_id.
الـ SUPABASE_URL و SUPABASE_SERVICE_ROLE_KEY موجودان في .env
```

**لإضافة Stripe Webhook:**
```
أريد إضافة POST /webhook/stripe في main.py.
عند payment_intent.succeeded → أنشئ سجل في invoices وحدّث subscriptions.
الـ STRIPE_WEBHOOK_SECRET في .env
```

**لبناء profile.html:**
```
أبنِ صفحة profile.html للمستخدم تعرض:
- اسمه وإيميله من Supabase Auth
- خطة اشتراكه من جدول subscriptions
- زر إلغاء الاشتراك
راجع _INTEGRA_DOCS/13_MISSING_PAGES.md للتصميم والكود.
```
