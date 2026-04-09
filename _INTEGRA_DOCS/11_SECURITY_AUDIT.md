# 🔐 تحليل الأمان الشامل — Security Audit

## نتيجة الـ Audit الإجمالية: ⚠️ متوسط الخطورة (7/10 مشاكل)

---

## 🔴 ثغرات حرجة (يجب إصلاحها قبل الإنتاج)

### SEC-001: JWT Bypass في Auth
**الملف:** `auth.py`
**الخطورة:** 🔴 CRITICAL

```python
# المشكلة الحالية:
if not SUPABASE_JWT_SECRET:
    # أي توكن يمر! حتى مزوّر أو منتهي الصلاحية
    payload = jwt.decode(token, options={"verify_signature": False})
    return payload  # ❌ لا تحقق من الصحة

# Fallback خطير جداً:
except Exception:
    payload = jwt.decode(token, options={"verify_signature": False})
    return payload  # ❌ يتجاهل كل أخطاء التحقق
```

**الإصلاح:**
```python
async def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing token")
    
    token = authorization.split(" ")[1]
    
    if not SUPABASE_JWT_SECRET:
        # في dev mode فقط — اطبع تحذيراً ولا تتجاهل التحقق نهائياً
        if os.getenv("ENVIRONMENT") == "production":
            raise HTTPException(500, "JWT secret not configured")
        # fallback للـ dev فقط
        try:
            return jwt.decode(token, options={"verify_signature": False})
        except:
            raise HTTPException(401, "Invalid token")
    
    try:
        return jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=["HS256"], audience="authenticated")
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except Exception:
        raise HTTPException(401, "Invalid token")  # ← لا fallback هنا!
```

---

### SEC-002: SUPABASE_ANON_KEY مكشوف في `settings.js`
**الملف:** `settings.js`
**الخطورة:** 🟡 متوسط (مقبول بشروط)

```javascript
SUPABASE_ANON_KEY: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'  // مكشوف في كل HTML page!
```

**الحقيقة:** anon key مصمم ليكون مكشوفاً في frontend **لكن** يجب ضمان:
- ✅ RLS مفعّل على **كل الجداول**
- ✅ كل SELECT مقيّد بـ `auth.uid() = user_id`
- ❌ لا تكتب بيانات حساسة بدون فحص RLS

**للتحقق من RLS:**
```sql
-- تأكد من تفعيل RLS:
SELECT schemaname, tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public';
-- يجب أن rowsecurity = true لكل الجداول
```

---

### SEC-003: Price Tampering Detection في Log ملف محلي
**الملف:** `payments.py`
**الخطورة:** 🟡 متوسط

```python
# حالياً يُحفظ في ملف نصي محلي:
with open('security_threats.log', 'a') as log:
    log.write(f"PROXIED_THREAT: [Plan:{plan_id}] [IP:{client_ip}]...\n")
```

**المشكلة:** الملف يتراكم بدون حذف، لا يوجد alert، قد يمتلئ الـ disk.

**الإصلاح:**
```python
import logging

security_logger = logging.getLogger("security")
# أضف handler لـ Supabase أو خدمة monitoring

def log_security_threat(plan_id, client_ip, attempted, required):
    security_logger.warning(
        f"PRICE_TAMPER | ip={client_ip} | plan={plan_id} | "
        f"attempted={attempted} | required={required}"
    )
    # اختياري: أرسل webhook لـ Slack أو Discord
```

---

### SEC-004: CORS مفتوح بجزء كبير
**الملف:** `main.py`
**الخطورة:** 🟡 متوسط

```python
# الوضع الحالي:
allow_origins=[
    "http://localhost:5500", "http://127.0.0.1:5500",
    "http://localhost:5501", "http://127.0.0.1:5501",
    "http://localhost:8080", "http://127.0.0.1:8080",
    "http://localhost:3000", "http://127.0.0.1:3000",
],
allow_headers=["*"],  # ← يقبل أي header
```

**الإصلاح للإنتاج:**
```python
import os
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5500").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],  # ← محددة
    allow_credentials=True,
)
```

---

### SEC-005: لا يوجد Rate Limiting
**الخطورة:** 🟡 متوسط

```
✗ /create-payment-intent — يمكن استدعاؤه آلاف المرات
✗ /api/livekit/token — يمكن توليد tokens بلا حدود
✗ /api/nodes — يمكن إنشاء مقابلات لا نهائية
```

**الإصلاح:**
```python
# requirements.txt: أضف slowapi
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/create-payment-intent")
@limiter.limit("5/minute")  # 5 محاولات في الدقيقة
async def create_payment_intent(...):
    ...

@app.post("/api/livekit/token")
@limiter.limit("20/minute")
async def get_token(...):
    ...
```

---

### SEC-006: `nodes_buffer.json` غير محمي
**الملف:** `nodes_buffer.json`
**الخطورة:** 🟠 خطر

```json
// يحتوي على بيانات شخصية مكشوفة على القرص:
{
    "candidate_name": "اسم ما",
    "candidate_email": "email@example.com",
    "position": "CTO"
}
```

**لا تحمير بـ encryption، ظاهر لأي شخص له وصول للسيرفر.**

**الإصلاح:** ترحيل كامل لـ Supabase (الحل الوحيد الصحيح).

---

### SEC-007: PaymentIntent بدون Webhook Verification
**الملف:** `payments.py`
**الخطورة:** 🔴 عالي

```python
# الآن: Frontend يقول "دفعت" ← Backend يصدّق
# الصحيح: Stripe يرسل Webhook ← Backend يتحقق من التوقيع

# خطر: شخص يمكنه تجاوز checkout.js وإرسال:
POST /create-payment-intent
{"payment_method_id": "valid_card", "amount": 1, "plan_id": "professional"}
# ويحصل على professional مقابل $0.01!
```

**الإصلاح:** Stripe Webhook + STRIPE_WEBHOOK_SECRET (انظر STRIPE_INTEGRATION.md)

---

### SEC-008: `livekit_error.txt` يُكتب في المشروع
**الملف:** `livekit_routes.py`
**الخطورة:** 🟢 منخفض

```python
with open("livekit_error.txt", "w") as f:
    f.write(err_out)  # ← يكتب stack trace في الـ repo!
```

**الإصلاح:**
```python
import logging
logger = logging.getLogger("livekit")
logger.error("Token generation failed", exc_info=True)
# أو: raise HTTPException دون كتابة ملف
```

---

## ✅ ما هو آمن فعلاً

| الأمر | الحالة |
|-------|--------|
| LiveKit API keys لا تُرسل للـ client | ✅ |
| Stripe amount validation من `pricing.json` | ✅ |
| Price Tamper Detection مع IP logging | ✅ |
| Token TTL محدود بـ 30 دقيقة | ✅ |
| Delete endpoint يتطلب Authentication | ✅ |
| CORS مقيّد بـ origins محددة (لا `*`) | ✅ |
| Supabase RLS مفعّل على كل الجداول | ✅ |

---

## Security Checklist قبل الإنتاج

```
□ ضع SUPABASE_JWT_SECRET في .env
□ ضع ENVIRONMENT=production في .env
□ أزل JWT bypass fallback
□ أضف slowapi للـ rate limiting
□ أضف STRIPE_WEBHOOK_SECRET وأنشئ webhook endpoint
□ اضبط ALLOWED_ORIGINS بدقة
□ احذف nodes_buffer.json وارحّل لـ Supabase
□ احذف livekit_error.txt من logging وأضف proper logger
□ تحقق من RLS policies على كل الجداول
□ أضف .env لـ .gitignore (تأكد!)
□ لا ترفع SUPABASE_SERVICE_ROLE_KEY في أي HTML
□ فعّل 2FA على Supabase Dashboard
□ فعّل 2FA على Stripe Dashboard
```

---

## تقييم الأمان

| المجال | التقييم |
|--------|---------|
| Authentication | 5/10 (JWT bypass) |
| Authorization (RLS) | 8/10 (مفعّل) |
| Payment Security | 6/10 (لا webhook) |
| Data Protection | 4/10 (JSON buffer) |
| API Security | 6/10 (لا rate limiting) |
| **المجموع** | **5.8/10** |
