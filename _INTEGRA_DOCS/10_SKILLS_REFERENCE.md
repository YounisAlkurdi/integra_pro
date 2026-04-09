# 🛠️ مرجع المطور — Skills & Technical Reference

## 1. FastAPI Cheatsheet للمشروع

### إضافة Endpoint جديد:
```python
# في main.py:
from fastapi import Depends
from auth import get_current_user

@app.post("/api/my-endpoint")
async def my_endpoint(
    body: MyModel,
    user: dict = Depends(get_current_user)  # يتطلب تسجيل دخول
):
    user_id = user["sub"]  # معرف المستخدم من JWT
    user_email = user.get("email")
    return {"ok": True}
```

### Pydantic Model:
```python
from pydantic import BaseModel
from typing import Optional, List

class MyModel(BaseModel):
    name: str
    email: Optional[str] = None
    tags: List[str] = []
```

---

## 2. Supabase من Python (بدون SDK)

```python
import json, urllib.request
from utils import get_env_safe

SUPABASE_URL = get_env_safe("SUPABASE_URL")
SERVICE_KEY = get_env_safe("SUPABASE_SERVICE_ROLE_KEY")

def supabase_query(method, table, body=None, params=""):
    url = f"{SUPABASE_URL}/rest/v1/{table}{params}"
    headers = {
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

# أمثلة:
# SELECT:   supabase_query("GET", "nodes", params="?user_id=eq.UUID&order=created_at.desc")
# INSERT:   supabase_query("POST", "nodes", {"name": "Ahmed"})
# UPDATE:   supabase_query("PATCH", "nodes", {"status": "ACTIVE"}, "?room_id=eq.UUID")
# DELETE:   supabase_query("DELETE", "nodes", params="?room_id=eq.UUID")
```

---

## 3. Supabase من JavaScript

```javascript
// في أي صفحة HTML، بعد تضمين supabase-client.js + settings.js:

// SELECT
const { data, error } = await supabase
    .from('nodes')
    .select('room_id, candidate_name, status')
    .eq('user_id', session.user.id)
    .order('created_at', { ascending: false })
    .limit(20);

// INSERT
const { data, error } = await supabase
    .from('chat_logs')
    .insert({ room_id: 'UUID', sender: 'Ahmed', message: 'Hello' });

// UPDATE
const { error } = await supabase
    .from('nodes')
    .update({ status: 'COMPLETED' })
    .eq('room_id', roomId);

// DELETE
const { error } = await supabase
    .from('nodes')
    .delete()
    .eq('room_id', roomId);

// REALTIME
supabase.channel('my-channel')
    .on('postgres_changes', {
        event: 'INSERT',
        schema: 'public',
        table: 'nodes'
    }, (payload) => {
        console.log('New node:', payload.new);
    })
    .subscribe();
```

---

## 4. Stripe Cheatsheet

### Backend — إنشاء PaymentIntent:
```python
import stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

intent = stripe.PaymentIntent.create(
    amount=9900,          # $99.00 (بالسنتات)
    currency="usd",
    metadata={
        "plan_id": "starter",
        "user_id": user_id,
        "mode": "monthly"
    }
)
return {"clientSecret": intent.client_secret}
```

### Frontend — تأكيد الدفع:
```javascript
const stripe = Stripe(PUBLISHABLE_KEY);
const result = await stripe.confirmCardPayment(clientSecret, {
    payment_method: {
        card: cardElement,
        billing_details: { email: userEmail }
    }
});

if (result.paymentIntent?.status === 'succeeded') {
    // ✅ نجح الدفع
} else if (result.error) {
    // ❌ فشل: result.error.message
}
```

### حساب المبالغ:
| الخطة | شهري (cents) | سنوي (cents) |
|-------|-------------|-------------|
| Starter | 9900 | 94800 ($79×12) |
| Professional | 29900 | 286800 ($239×12) |

---

## 5. LiveKit Cheatsheet

### Backend — توليد Token:
```python
from livekit.api import AccessToken, VideoGrants
import datetime

token = (
    AccessToken(api_key, api_secret)
    .with_identity("Ahmed_HR")
    .with_name("Ahmed")
    .with_ttl(datetime.timedelta(seconds=1800))
    .with_grants(VideoGrants(
        room_join=True,
        room="room-uuid",
        can_publish=True,
        can_subscribe=True,
    ))
    .to_jwt()
)
```

### Frontend — الاتصال بالغرفة:
```javascript
import { Room, RoomEvent, Track } from 'livekit-client';

const room = new Room({ adaptiveStream: true, dynacast: true });

await room.connect(livekitUrl, token);
await room.localParticipant.enableCameraAndMicrophone();

room.on(RoomEvent.ParticipantConnected, (participant) => {
    console.log('Joined:', participant.identity);
});

room.on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
    if (track.kind === Track.Kind.Video) {
        const el = track.attach(); // <video> element
        document.getElementById('video-grid').appendChild(el);
    }
});
```

---

## 6. STT Engine — كيفية الاستخدام

```javascript
// بدء الاستماع:
STTEngine.start({
    identity: 'ahmed@company.com',
    name: 'Ahmed HR',
    lang: 'ar-SA'  // أو 'en-US'
});

// الاستماع للنتائج:
window.addEventListener('stt:final', (e) => {
    const { text, name } = e.detail;
    // text = الجملة الكاملة
});

window.addEventListener('stt:interim', (e) => {
    const { text } = e.detail;
    // text = نص مؤقت (قيد الكلام)
});

// كتم الصوت:
STTEngine.setMuted(true);

// إيقاف:
STTEngine.stop();
```

---

## 7. Auth Flow Reference

```javascript
// التحقق من الجلسة عند تحميل أي صفحة:
const { data: { session } } = await supabase.auth.getSession();
if (!session) {
    window.location.href = 'index.html';
    return;
}
const user = session.user;
const token = session.access_token; // يُرسل في Authorization header

// تسجيل الخروج:
await supabase.auth.signOut();
window.location.href = 'index.html';

// جلب بيانات المستخدم:
const { data: { user } } = await supabase.auth.getUser();
const email = user.email;
const fullName = user.user_metadata?.full_name;
```

---

## 8. هيكل .env الكامل

```env
# ===== SUPABASE =====
SUPABASE_URL=https://ljnclcivnbhjjofsfyzm.supabase.co
SUPABASE_ANON_KEY=eyJhbGci...  # للـ frontend (مكشوف)
SUPABASE_SERVICE_ROLE_KEY=eyJhbGci...  # للـ backend فقط (سري!)
SUPABASE_JWT_SECRET=your-jwt-secret  # من Settings → API

# ===== LIVEKIT =====
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=APIxxxxxxxxxxxxxxx
LIVEKIT_API_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# ===== STRIPE =====
STRIPE_SECRET_KEY=sk_test_...  # أو sk_live_ في الإنتاج
STRIPE_PUBLISHABLE_KEY=pk_test_...  # آمن للـ frontend
STRIPE_WEBHOOK_SECRET=whsec_...  # من Stripe Dashboard Webhooks

# ===== APP =====
ENVIRONMENT=development  # أو production
ALLOWED_ORIGINS=http://localhost:8000,https://your-domain.com
```

---

## 9. أوامر تشغيل المشروع

```bash
# تثبيت المتطلبات:
pip install -r requirements.txt

# تشغيل السيرفر:
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# تشغيل مكشوف للشبكة (للتجربة على الـ mobile):
uvicorn main:app --reload --host 0.0.0.0 --port 8000
# ثم استخدام IP الكمبيوتر في settings.js
```

---

## 10. SQL Migrations المطلوبة

```sql
-- 1. تصحيح نوع scheduled_at
ALTER TABLE nodes ALTER COLUMN scheduled_at TYPE TIMESTAMPTZ 
USING scheduled_at::TIMESTAMPTZ;

-- 2. إضافة status constraint
ALTER TABLE nodes ADD CONSTRAINT nodes_status_check 
CHECK (status IN ('PENDING', 'ACTIVE', 'COMPLETED', 'CANCELLED'));

-- 3. RLS policies
-- nodes
CREATE POLICY "Users manage own nodes" ON nodes
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- invoices (read only)
CREATE POLICY "Users read own invoices" ON invoices
FOR SELECT USING (auth.uid() = user_id);

-- subscriptions (read only)
CREATE POLICY "Users read own subscription" ON subscriptions
FOR SELECT USING (auth.uid() = user_id);

-- interview_reports
CREATE POLICY "Users manage own reports" ON interview_reports
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- chat_logs
CREATE POLICY "Users manage own chat logs" ON chat_logs
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);
```
