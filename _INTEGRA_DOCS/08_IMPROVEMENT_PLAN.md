# 🚀 خطة التحسين المرحلية

## المرحلة 1 — الإصلاحات الحرجة (أسبوع 1)

### 1.1 ربط nodes.py بـ Supabase (BUG-001)

**الأولوية:** 🔴 أعلى أولوية

**الخطوات:**
1. أضف `SUPABASE_URL` و `SUPABASE_SERVICE_ROLE_KEY` في `.env`
2. أعد كتابة دوال `nodes.py`:

```python
import json
import urllib.request
from utils import get_env_safe

SUPABASE_URL = get_env_safe("SUPABASE_URL")
# استخدم Service Role Key للكتابة من Backend
SUPABASE_SERVICE_KEY = get_env_safe("SUPABASE_SERVICE_ROLE_KEY")

def _supabase_request(method: str, path: str, body=None):
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

def create_neural_node(node: NodeProtocol, user_id: str):
    body = {**node.dict(), "user_id": user_id, "room_id": str(uuid.uuid4())}
    result = _supabase_request("POST", "nodes", body)
    return result[0] if result else body

def get_active_streams(user_id: str = None):
    path = "nodes?order=created_at.desc"
    if user_id:
        path += f"&user_id=eq.{user_id}"
    return _supabase_request("GET", path)

def delete_node(room_id: str):
    _supabase_request("DELETE", f"nodes?room_id=eq.{room_id}")
    return True
```

3. حدّث `main.py` لتمرير `user_id` من JWT:
```python
@app.post("/api/nodes")
async def create_node(node: NodeProtocol, user: dict = Depends(get_current_user)):
    result = create_neural_node(node, user_id=user["sub"])
    return result
```

**الوقت المقدر:** 2-3 ساعات

---

### 1.2 إضافة SUPABASE_JWT_SECRET (BUG-003)

**الخطوات:**
1. اذهب لـ Supabase Dashboard → Settings → API
2. انسخ `JWT Secret`
3. أضفه في `.env`:
```env
SUPABASE_JWT_SECRET=your-jwt-secret-from-supabase
```

**الوقت المقدر:** 15 دقيقة

---

### 1.3 حفظ Chat Logs (BUG-004)

ضع في `integra-session.js` بعد حدث `stt:final`:

```javascript
window.addEventListener('stt:final', async (e) => {
    const { text, name } = e.detail;
    
    // عرض في الـ UI (موجود بالفعل)
    appendTranscript(name, text);
    
    // ✅ حفظ في Supabase
    try {
        await supabase.from('chat_logs').insert({
            room_id: currentRoomId,
            sender: name,
            message: text
        });
    } catch(err) {
        console.warn('Chat log save failed:', err);
    }
});
```

**الوقت المقدر:** 1 ساعة

---

## المرحلة 2 — المدفوعات والاشتراكات (أسبوع 2)

### 2.1 Stripe Webhook (BUG-002)

```python
# في main.py:
@app.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    
    event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    
    if event["type"] == "payment_intent.succeeded":
        intent = event["data"]["object"]
        await on_payment_success(intent)
    
    return {"ok": True}

async def on_payment_success(intent):
    user_email = intent["metadata"].get("user_email")
    plan_id = intent["metadata"].get("plan_id")
    mode = intent["metadata"].get("mode", "monthly")  # monthly/yearly
    
    # 1. جلب user_id من Supabase
    users = _supabase_request("GET", f"..../auth/users?email=eq.{user_email}")
    user_id = users[0]["id"]
    
    # 2. إنشاء invoice
    _supabase_request("POST", "invoices", {
        "user_id": user_id,
        "amount": intent["amount"],
        "plan_id": plan_id,
        "payment_intent_id": intent["id"],
        "status": "PAID"
    })
    
    # 3. تحديث subscription
    _supabase_request("POST", "subscriptions", {
        "user_id": user_id,
        "plan_id": plan_id,
        "status": "active",
        "interviews_limit": get_plan_limit(plan_id)
    })
```

---

### 2.2 صفحة الفواتير في Profile

```javascript
// في profile.html:
const { data: invoices } = await supabase
    .from('invoices')
    .select('*')
    .eq('user_id', user.id)
    .order('created_at', { ascending: false });

renderInvoices(invoices);
```

---

## المرحلة 3 — التقارير الذكية (أسبوع 3)

### 3.1 Web AI Analysis بعد انتهاء المقابلة

```javascript
// في integra-session.js عند الضغط على End Session:
async function endSession() {
    // 1. جلب transcript من chat_logs
    const { data: logs } = await supabase.from('chat_logs')
        .select('sender, message, created_at')
        .eq('room_id', currentRoomId)
        .order('created_at');
    
    // 2. إرسال لـ Backend لتحليله
    const analysis = await fetch('/api/analyze-interview', {
        method: 'POST',
        body: JSON.stringify({ room_id: currentRoomId, transcript: logs }),
        headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${session.access_token}`
        }
    });
    
    // 3. حفظ التقرير في interview_reports
}
```

```python
# في main.py:
@app.post("/api/analyze-interview")
async def analyze_interview(data: dict, user: dict = Depends(get_current_user)):
    transcript = data.get("transcript", [])
    room_id = data.get("room_id")
    
    # يمكن هنا استخدام Gemini API أو GPT لتحليل الـ transcript
    # analysis = call_gemini_api(transcript)
    
    # حالياً: تحليل بسيط
    analysis = {
        "score": 85,
        "strengths": ["Communication", "Technical Knowledge"],
        "weaknesses": ["Time management"],
        "ai_summary": "Strong candidate with technical proficiency..."
    }
    
    _supabase_request("POST", "interview_reports", {
        "room_id": room_id,
        "user_id": user["sub"],
        "score": analysis["score"],
        "strengths": analysis["strengths"],
        "weaknesses": analysis["weaknesses"],
        "ai_summary": analysis["ai_summary"]
    })
    
    return analysis
```

---

## المرحلة 4 — تحسينات الجودة (أسبوع 4)

### 4.1 تحديث scheduled_at في DB
```sql
-- Migration: تحويل نوع scheduled_at
ALTER TABLE nodes ALTER COLUMN scheduled_at TYPE TIMESTAMPTZ 
USING scheduled_at::TIMESTAMPTZ;
```

### 4.2 إضافة status constraint
```sql
ALTER TABLE nodes ADD CONSTRAINT nodes_status_check 
CHECK (status IN ('PENDING', 'ACTIVE', 'COMPLETED', 'CANCELLED'));
```

### 4.3 تقييد CORS في production
```python
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000").split(",")
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, ...)
```

### 4.4 Rate Limiting
```python
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@app.post("/api/nodes")
@limiter.limit("10/minute")
async def create_node(...):
    ...
```

### 4.5 Token Auto-Refresh في LiveKit
```javascript
// قبل انتهاء التوكن بـ 5 دقائق:
const refreshAt = (TOKEN_TTL - 300) * 1000;
setTimeout(async () => {
    const { token } = await fetchLivekitToken(roomId, participantName, role);
    // LiveKit SDK يدعم token refresh
}, refreshAt);
```

---

## الجدول الزمني الموجز

| الأسبوع | المهام | الأثر |
|---------|--------|-------|
| 1 | ربط nodes بـ Supabase + JWT Secret + Chat Logs | 🔴 حرج |
| 2 | Stripe Webhook + Invoices + Subscription Check | 💰 مالي |
| 3 | AI Analysis + Interview Reports | 🧠 Core Feature |
| 4 | تحسينات الأمان والأداء | 🛡️ جودة |
