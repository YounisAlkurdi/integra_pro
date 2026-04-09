# 🏗️ معمارية مشروع Integra — النظرة الشاملة

## 1. الطبقات الثلاث للنظام

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                             │
│   HTML Pages → Vanilla JS → TailwindCSS → Lucide Icons         │
│   login | dashboard | session | reports | appointments | pricing│
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP / REST
┌───────────────────────────▼─────────────────────────────────────┐
│                        API LAYER                                │
│   FastAPI (Python) — uvicorn — PORT 8000                        │
│   main.py → nodes.py → auth.py → livekit_routes.py → payments.py│
└──────────────┬──────────────────────────┬───────────────────────┘
               │                          │
┌──────────────▼──────────┐  ┌────────────▼───────────────────────┐
│   SUPABASE (DB + Auth)  │  │   EXTERNAL SERVICES                │
│   PostgreSQL + GoTrue   │  │   LiveKit (WebRTC Video)           │
│   5 Tables + RLS        │  │   Stripe (Payments)                │
│   Google OAuth + OTP    │  │   Web Speech API (STT)             │
└─────────────────────────┘  └────────────────────────────────────┘
```

---

## 2. تدفق مسار المستخدم الكامل

```
[index.html] → [login.html] → [dashboard.html]
                                     │
              ┌──────────────────────┼──────────────────────┐
              │                      │                      │
     [reports.html]      [appointments.html]      [pricing.html]
                                                       │
                                               [checkout.html]
                                                       │
                                              Stripe Payment
                                                       ↓
                                            [profile.html] (subscription)
              
[dashboard.html] → CREATE NODE → [integra-session.html?room=X&role=hr]
                                          │
                               LiveKit Room (Video+Audio)
                                          │
                                    STT Engine (stt.js)
                                          │
                               Chat Logs → Supabase
```

---

## 3. خريطة الملفات

### 🐍 Python Backend (FastAPI)
| الملف | الدور | المسارات |
|-------|-------|----------|
| `main.py` | المدخل الرئيسي، CORSو Router | `/api/nodes`, `/api/stats`, `/config`, `/create-payment-intent` |
| `nodes.py` | إدارة جلسات المقابلات | `create_neural_node`, `get_active_streams`, `delete_node` |
| `auth.py` | التحقق من JWT الـ Supabase | `get_current_user()` |
| `livekit_routes.py` | توليد تذاكر الفيديو | `POST /api/livekit/token`, `DELETE /api/livekit/room/{id}` |
| `payments.py` | معالجة Stripe | `execute_payment()` |
| `utils.py` | استخراج env vars | `get_env_safe()` |

### 🌐 Frontend HTML Pages
| الصفحة | الوصف | ملف JS المرتبط |
|--------|-------|----------------|
| `index.html` | Landing page (Marketing) | `script.js` |
| `login.html` | تسجيل الدخول (Google + OTP) | `login.js` |
| `dashboard.html` | لوحة التحكم الرئيسية | `dashboard.js` |
| `integra-session.html` | غرفة المقابلة الفيديو | `integra-session.js` + `livekit-session.js` |
| `reports.html` | أرشيف التقارير | `reports.js` |
| `appointments.html` | جدول المواعيد (تقويم) | `appointments.js` |
| `pricing.html` | صفحة الأسعار | `pricing.js` |
| `checkout.html` | صفحة الدفع بالبطاقة | `checkout.js` |
| `profile.html` | ملف المستخدم | (inline script) |

### 🗄️ Supabase Tables
| الجدول | الغرض | الصفوف الحالية |
|--------|--------|---------------|
| `nodes` | جلسات/مقابلات | 0 (JSON buffer) |
| `subscriptions` | اشتراكات المستخدمين | 2 |
| `invoices` | فواتير الدفع | 0 |
| `interview_reports` | تقارير AI | 0 |
| `chat_logs` | نصوص المحادثات | 0 |

---

## 4. Environment Variables المطلوبة

```env
# Supabase
SUPABASE_URL=https://ljnclcivnbhjjofsfyzm.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_JWT_SECRET=     # ← مطلوب للإنتاج!

# LiveKit
LIVEKIT_URL=wss://...
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...

# Stripe
STRIPE_SECRET_KEY=sk_...
STRIPE_PUBLISHABLE_KEY=pk_...
```

---

## 5. حالة المشروع الحالية

| المكون | الحالة |
|--------|--------|
| Auth (Login/Logout) | ✅ يعمل |
| Dashboard (عرض المقابلات) | ⚠️ يعمل (JSON Buffer لا Supabase) |
| LiveKit (الفيديو) | ✅ يعمل |
| STT (تحويل الصوت) | ✅ يعمل |
| Stripe (الدفع) | ⚠️ جزئي (لا يُحدّث DB) |
| Reports (التقارير) | ⚠️ بيانات وهمية (Random) |
| Supabase nodes | ⚠️ الجدول موجود لكن Backend لا يستخدمه |
| JWT Verification | ⚠️ disabled في dev mode |
