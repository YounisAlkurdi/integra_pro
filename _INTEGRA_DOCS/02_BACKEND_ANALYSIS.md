# 🐍 تحليل Backend — Python (FastAPI)

## ملف `main.py` — نقطة الدخول الرئيسية

### ما يفعله:
- يُشغّل FastAPI app
- يضيف CORS Middleware (يسمح لـ أي origin حالياً)
- يعرّف endpoints لـ: nodes, stats, payments, config

### الكود الحالي والتحليل:

```python
app = FastAPI(title="Integra | Core Control Node")

app.add_middleware(CORSMiddleware,
    allow_origins=["*"],   # ⚠️ مشكلة أمنية في الإنتاج!
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)
```

### نقاط الضعف:
| المشكلة | الخطورة | الحل |
|---------|--------|------|
| `allow_origins=["*"]` مع `allow_credentials=True` | 🔴 خطر | قيّد الـ origins بالنطاق الفعلي |
| لا يوجد Rate Limiting | 🟡 متوسط | أضف SlowAPI أو middleware مخصص |
| لا يوجد Logging منظم | 🟡 متوسط | أضف Python logging module |

### Endpoints:

| المسار | الطريقة | الوصف |
|--------|---------|-------|
| `/` | GET | Health check |
| `/api/nodes` | GET | جلب كل المقابلات (من JSON Buffer!) |
| `/api/nodes` | POST | إنشاء مقابلة جديدة |
| `/api/nodes/{room_id}` | DELETE | حذف مقابلة |
| `/api/stats` | GET | إحصائيات إجمالية |
| `/api/livekit/token` | POST | توليد JWT للفيديو |
| `/api/livekit/room/{id}` | DELETE | إنهاء غرفة الفيديو |
| `/config` | GET | إرسال Stripe Publishable Key |
| `/create-payment-intent` | POST | معالجة الدفع |

---

## ملف `nodes.py` — إدارة جلسات المقابلات

### ⚠️ المشكلة الكبيرة الحالية:
```python
BUFFER_FILE = "nodes_buffer.json"  # ❌ يحفظ في ملف JSON محلي!
```

**المشكلة:** النظام يستخدم `nodes_buffer.json` بدلاً من Supabase رغم وجود جدول `nodes` في DB.

### Schema الـ Node الحالي:
```python
class NodeProtocol(BaseModel):
    candidate_name: str
    candidate_email: Optional[str] = None
    position: str
    questions: List[str]        # ← لا يُستخدم فعلاً في الـ UI
    scheduled_at: str
    room_id: Optional[str] = None
    status: str = "PENDING"
```

### الدوال:
| الدالة | ما تفعل | المشكلة |
|--------|---------|---------|
| `create_neural_node()` | تكتب في JSON | يجب أن تكتب في Supabase |
| `get_active_streams()` | تقرأ من JSON | يجب أن تقرأ من Supabase |
| `delete_node()` | تحذف من JSON | يجب أن تحذف من Supabase |
| `get_node_stats()` | تحسب من JSON | يجب أن تحسب من Supabase |

### الإصلاح المطلوب:
```python
# بدلاً من JSON Buffer، استخدم Supabase REST API
import urllib.request

SUPABASE_URL = get_env_safe("SUPABASE_URL")
SUPABASE_KEY = get_env_safe("SUPABASE_ANON_KEY")

def create_neural_node(node: NodeProtocol, user_id: str):
    node.room_id = str(uuid.uuid4())
    data = {**node.dict(), "user_id": user_id}
    # POST to Supabase REST
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/nodes",
        method="POST",
        headers={"apikey": SUPABASE_KEY, "Content-Type": "application/json"},
        data=json.dumps(data).encode()
    )
    # ...
```

---

## ملف `auth.py` — التحقق من الهوية

### كيف يعمل:
```python
async def get_current_user(authorization: Optional[str] = Header(None)):
    token = authorization.split(" ")[1]
    
    if not SUPABASE_JWT_SECRET:
        # ⚠️ يتجاوز التحقق في dev mode!
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload
    
    payload = jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=["HS256"])
    return payload
```

### المشاكل:
| المشكلة | الخطورة |
|---------|--------|
| `SUPABASE_JWT_SECRET` فارغ → لا تحقق من التوقيع! | 🔴 خطر في الإنتاج |
| يحاول Bypass عند كل خطأ (fallback unsecure) | 🔴 خطر |
| لا يوجد blacklist للـ tokens | 🟡 متوسط |

### الإصلاح:
```python
# في .env أضف:
# SUPABASE_JWT_SECRET=your_actual_jwt_secret_from_supabase_settings

# ولا تسمح بـ bypass في الإنتاج:
if not SUPABASE_JWT_SECRET and os.getenv("ENVIRONMENT") == "production":
    raise RuntimeError("SUPABASE_JWT_SECRET is required in production!")
```

---

## ملف `livekit_routes.py` — توليد تذاكر الفيديو

### كيف يعمل (ممتاز!):
1. يتحقق من صلاحية الـ roomName و participantName
2. يقرأ API Key و Secret من .env فقط (لا يُرسلها للعميل أبداً)
3. يتحقق من وقت الجدولة (يمنع الدخول قبل 5 دقائق من الموعد)
4. يولّد JWT موقّع مؤقت (30 دقيقة)
5. يتيح حذف الغرفة عن بُعد

### نقطة قوة:
```python
TOKEN_TTL_SEC = 1800  # ✅ 30 دقيقة فقط — منع إساءة الاستخدام

# ✅ التحقق من وقت الجدولة:
if scheduled_time > (now + buffer):
    raise HTTPException(403, "Access not yet allowed...")
```

### ⚠️ مشكلة في `livekit_routes.py`:
```python
from nodes import NODE_STORAGE  # يستورد من JSON Buffer!
# بدلاً من استعلام Supabase
```

---

## ملف `payments.py` — معالجة الدفع (الوضع الحالي)

### الكود الحالي (بعد الـ Revert):
```python
async def execute_payment(payment_req: PaymentRequest):
    intent = stripe.PaymentIntent.create(
        amount=payment_req.amount,
        currency=payment_req.currency,
        payment_method_types=["card"],
        metadata={"plan_id": payment_req.plan_id}
    )
    return {"clientSecret": intent.client_secret}
```

### المشكلة الكبيرة:
- ✅ Stripe PaymentIntent يُنشأ
- ❌ عند نجاح الدفع لا يُسجَّل شيء في `invoices` table
- ❌ لا يُحدَّث `subscriptions` table
- ❌ المستخدم يدفع لكن النظام لا يعرف!

### الحل المطلوب (مع Supabase):
```python
# بعد نجاح الدفع، أضف في invoices:
if intent.status == "succeeded":
    # 1. Insert invoice
    insert_invoice(user_id, amount, plan_id, intent.id)
    # 2. Upsert subscription
    upsert_subscription(user_id, plan_id)
```

---

## ملف `utils.py` — أدوات مساعدة

```python
def get_env_safe(key: str):
    val = os.getenv(key)
    if not val: return ""
    return val.strip().replace('"', '').replace("'", "")  # ✅ تنظيف جيد
```

**ملاحظة:** `requirements.txt` لا يحتوي `supabase` library — يُستخدم `urllib.request` مباشرة.

---

## ملف `requirements.txt`

```
fastapi
uvicorn
PyJWT       ← للتحقق من JWT
python-dotenv
stripe
pydantic
livekit-api ← لتوليد tokens وحذف الغرف
```

**مفقودون:**
- `httpx` ← للـ async HTTP requests
- `supabase` ← SDK رسمي (أو الاكتفاء بـ urllib)
- `slowapi` ← Rate limiting
