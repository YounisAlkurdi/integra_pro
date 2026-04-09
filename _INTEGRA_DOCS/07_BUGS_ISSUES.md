# 🐛 قائمة المشاكل والثغرات — Bugs & Issues

## 🔴 مشاكل حرجة (Critical)

### BUG-001: nodes_buffer.json بدلاً من Supabase
- **الملفات:** `nodes.py`, `livekit_routes.py`
- **التأثير:** فقدان كل البيانات عند إعادة تشغيل السيرفر
- **الأعراض:** المقابلات تختفي بعد kill للخادم
- **الحل:** تحويل `nodes.py` للكتابة في Supabase table `nodes`

```python
# المشكلة:
BUFFER_FILE = "nodes_buffer.json"
def create_neural_node(node):
    save_buffer(NODE_STORAGE)  # ❌ كتابة في ملف

# الحل:
def create_neural_node(node, user_id):
    response = supabase_http_post("/rest/v1/nodes", {..., "user_id": user_id})
```

### BUG-002: Stripe Webhook غير موجود
- **الملفات:** `payments.py`, `checkout.js`
- **التأثير:** المستخدم يدفع لكن لا يحصل على اشتراك
- **الأعراض:** `invoices` و `subscriptions` دائماً فارغتان بعد الدفع
- **الحل:** إضافة `/webhook/stripe` endpoint

### BUG-003: JWT Verification معطّل
- **الملفات:** `auth.py`
- **التأثير:** أي شخص يمكنه الوصول بتوكن غير صالح في dev mode
- **الأعراض:** `WARNING: SUPABASE_JWT_SECRET is empty` في كل request
- **الحل:** ضع `SUPABASE_JWT_SECRET` في `.env`
```env
# من Supabase Dashboard → Settings → API → JWT Secret
SUPABASE_JWT_SECRET=your-super-secret-jwt-token-here
```

### BUG-004: chat_logs لا تُحفظ
- **الملفات:** `integra-session.js`, `stt.js`
- **التأثير:** كل ما قيل في المقابلة يُفقد
- **الأعراض:** جدول `chat_logs` في Supabase ظل فارغاً
- **الحل:**
```javascript
window.addEventListener('stt:final', async (e) => {
    await supabase.from('chat_logs').insert({
        room_id: currentRoomId,
        sender: e.detail.name,
        message: e.detail.text
    });
});
```

### BUG-005: interview_reports لا تُنشأ
- **الملفات:** `integra-session.js`, `reports.js`
- **التأثير:** التقارير وهمية (random numbers)
- **الأعراض:** `generateAnalysisCluster()` يُرجع أرقام عشوائية
- **الحل:** إنشاء `POST /api/reports` endpoint مع تحليل الـ transcript

---

## 🟡 مشاكل متوسطة (Warning)

### BUG-006: Dashboard لا يقرأ من Supabase
- **الملفات:** `dashboard.js`
- **التأثير:** لا يعرض المقابلات الموجودة في Supabase
- **الحل:** استبدال `fetch('/api/nodes')` بـ:
```javascript
const { data } = await supabase.from('nodes').select('*')
    .eq('user_id', session.user.id).order('created_at', {ascending: false});
```

### BUG-007: CORS غير مقيّد
- **الملفات:** `main.py`
- **التأثير:** أي موقع يمكنه الاتصال بالـ API
- **الحل:**
```python
allow_origins=["https://your-domain.com", "http://localhost:8000"]
```

### BUG-008: scheduled_at من نوع TEXT
- **الملفات:** `nodes` table في Supabase
- **التأثير:** لا يمكن عمل queries بالتاريخ (`WHERE scheduled_at > NOW()`)
- **الحل:** تحويل العمود لـ `TIMESTAMPTZ`

### BUG-009: tokens تنتهي بعد 30 دقيقة بدون تجديد
- **الملفات:** `livekit_routes.py`, `integra-session.js`
- **التأثير:** المقابلات الطويلة تُقطع فجأة
- **الحل:** إضافة Token Auto-Refresh منطق قبل الانتهاء

### BUG-010: Reports تقرأ من `nodes` لكن nodes.room_id = room_id في Supabase
- **الملفات:** `reports.js`
- **التأثير:** يقرأ من `nodes.id` لكن الـ Primary Key هو `room_id`
```javascript
// مشكلة:
.select('*').eq('id', nodeId)  // ❌ الـ PK اسمه room_id لا id!
// الحل:
.select('*').eq('room_id', nodeId)
```

### BUG-011: لا يتحقق من حد الاشتراك
- **الملفات:** `dashboard.js`, `nodes.py`
- **التأثير:** المستخدم قد يتجاوز `interviews_limit`
- **الحل:** قبل إنشاء Node، تحقق من:
```javascript
const { data: sub } = await supabase.from('subscriptions')
    .select('interviews_computed, interviews_limit')
    .eq('user_id', user.id).single();
if (sub.interviews_computed >= sub.interviews_limit) {
    showUpgradeDialog();
    return;
}
```

---

## 🟢 مشاكل صغيرة (Minor)

### BUG-012: status Enum غير مقيّد في DB
```sql
-- يجب إضافة:
ALTER TABLE nodes ADD CONSTRAINT nodes_status_check 
    CHECK (status IN ('PENDING', 'ACTIVE', 'COMPLETED', 'CANCELLED'));
```

### BUG-013: لا RLS policies محددة
- يجب التحقق من وجود RLS policies في Supabase Dashboard

### BUG-014: `pricing.html` Hardcoded prices
- الأسعار في HTML مكررة مع `pricing.json`

### BUG-015: BASE_URL hardcoded
```javascript
BASE_URL: "http://localhost:8000",  // ← لن يعمل في الإنتاج
```

### BUG-016: Web Speech API على Firefox تفشل صامتة
- لا يوجد fallback أو رسالة واضحة للمستخدم

---

## ملخص

| الفئة | العدد |
|-------|-------|
| 🔴 حرج | 5 |
| 🟡 متوسط | 6 |
| 🟢 صغير | 5 |
| **المجموع** | **16** |
