# ⚡ INTEGRA — Quick Start Prompt

## انسخ هذا كاملاً في بداية الجلسة الجديدة:

---

```
أنا أعمل على مشروع Integra في المسار: C:\tist_integra

قبل أي شيء، اقرأ وثائق المشروع من هذا الفولدر:
C:\tist_integra\_INTEGRA_DOCS\

ابدأ بـ:
1. 00_README.md — الفهرس والحالة الحالية
2. 07_BUGS_ISSUES.md — المشاكل الحرجة
3. 08_IMPROVEMENT_PLAN.md — خطة التطوير

بعد ما تقرأ، نفذ هذه المهمة:

[اكتب هنا المهمة]
```

---

## أمثلة جاهزة للنسخ:

### 🔴 لإصلاح البيانات (nodes → Supabase):
```
أنا أعمل على مشروع Integra في المسار: C:\tist_integra
اقرأ: C:\tist_integra\_INTEGRA_DOCS\08_IMPROVEMENT_PLAN.md
ثم اقرأ الملف الحالي: C:\tist_integra\nodes.py
ونفذ المرحلة 1.1 — ربط nodes.py بـ Supabase بدلاً من nodes_buffer.json
```

### 📱 لبناء QR + join.html:
```
أنا أعمل على مشروع Integra في المسار: C:\tist_integra
اقرأ: C:\tist_integra\_INTEGRA_DOCS\14_QR_INTEGRATION.md
ثم:
1. أضف endpoint /api/nodes/{room_id}/qr في livekit_routes.py
2. أنشئ ملف join.html في جذر المشروع
```

### 💳 لإضافة Stripe Webhook:
```
أنا أعمل على مشروع Integra في المسار: C:\tist_integra
اقرأ: C:\tist_integra\_INTEGRA_DOCS\05_STRIPE_INTEGRATION.md
ثم اقرأ: C:\tist_integra\payments.py و C:\tist_integra\main.py
ونفذ: أضف POST /webhook/stripe endpoint يحدّث جدولي invoices و subscriptions في Supabase
```

### 👤 لبناء profile.html:
```
أنا أعمل على مشروع Integra في المسار: C:\tist_integra
اقرأ: C:\tist_integra\_INTEGRA_DOCS\13_MISSING_PAGES.md القسم PAGE-001
ثم اقرأ: C:\tist_integra\dashboard.html (للstyle) و C:\tist_integra\settings.js
وأنشئ: C:\tist_integra\profile.html مع profile.js
```

### 🔐 لإصلاح الأمان:
```
أنا أعمل على مشروع Integra في المسار: C:\tist_integra
اقرأ: C:\tist_integra\_INTEGRA_DOCS\11_SECURITY_AUDIT.md
ثم اقرأ: C:\tist_integra\auth.py
ونفذ: إصلاح SEC-001 (JWT bypass) و SEC-004 (CORS)
```
