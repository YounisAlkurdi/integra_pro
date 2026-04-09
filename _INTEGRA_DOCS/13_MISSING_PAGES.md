# 📄 الصفحات الإضافية المطلوبة — Missing Pages

## ملخص الصفحات الموجودة والناقصة

| الصفحة | الحالة | الأولوية |
|--------|--------|---------|
| `index.html` | ✅ موجودة | — |
| `login.html` | ✅ موجودة | — |
| `dashboard.html` | ✅ موجودة | — |
| `appointments.html` | ✅ موجودة | — |
| `reports.html` | ✅ موجودة | — |
| `pricing.html` | ✅ موجودة | — |
| `checkout.html` | ✅ موجودة | — |
| `integra-session.html` | ✅ موجودة | — |
| `profile.html` | ❌ **ناقصة** | 🔴 عالي |
| `billing.html` | ❌ **ناقصة** | 🔴 عالي |
| `join.html` | ❌ **ناقصة** | 🔴 عالي (QR) |
| `candidate.html` | ❌ **ناقصة** | 🟡 متوسط |
| `admin.html` | ❌ **ناقصة** | 🟢 منخفض |

---

## 📄 PAGE-001: `profile.html` — صفحة الملف الشخصي

### ما يجب أن تحتوي عليه:
```
┌─────────────────────────────────────────────────────┐
│  INTEGRA                                            │
├─────────────────────────────────────────────────────┤
│                                                     │
│  👤 Ahmed Al-Rashidi                                │
│     ahmed@company.com                               │
│     Member since: Jan 2025                          │
│                                                     │
│  ┌─────────────────┐  ┌─────────────────────────┐  │
│  │  Account Info   │  │   Subscription Plan     │  │
│  │  ─────────────  │  │  ─────────────────────  │  │
│  │  Full Name      │  │  📦 Professional Plan   │  │
│  │  [Ahmed Al-R..]│  │  Next billing: May 2025 │  │
│  │                 │  │  Interviews: 23/50      │  │
│  │  Company        │  │  [Upgrade Plan ↑]       │  │
│  │  [Tech Corp]    │  │  [Cancel Subscription]  │  │
│  │                 │  └─────────────────────────┘  │
│  │  [Save Changes] │                               │
│  └─────────────────┘                               │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### الكود الأساسي (`profile.js`):
```javascript
// auth-guard
const { data: { session } } = await supabase.auth.getSession();
if (!session) window.location.href = 'login.html';
const user = session.user;

// عرض معلومات المستخدم
document.getElementById('user-name').textContent = user.user_metadata?.full_name || 'User';
document.getElementById('user-email').textContent = user.email;

// جلب الاشتراك
const { data: sub } = await supabase.from('subscriptions')
    .select('*').eq('user_id', user.id).single();

if (sub) {
    document.getElementById('plan-name').textContent = sub.plan_id;
    document.getElementById('interviews-count').textContent = 
        `${sub.interviews_computed}/${sub.interviews_limit}`;
}

// تحديث الاسم
document.getElementById('update-profile-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fullName = document.getElementById('full-name-input').value;
    await supabase.auth.updateUser({ data: { full_name: fullName } });
    showToast('Profile updated!', 'success');
});

// إلغاء الاشتراك
document.getElementById('cancel-sub-btn').addEventListener('click', async () => {
    if (!confirm('Are you sure you want to cancel your subscription?')) return;
    const res = await fetch('/api/subscription/cancel', {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${session.access_token}` }
    });
    if (res.ok) showToast('Subscription cancelled', 'info');
});
```

### Backend endpoint مطلوب:
```python
# في main.py:
@app.delete("/api/subscription/cancel")
async def cancel_subscription(user: dict = Depends(get_current_user)):
    # 1. جلب subscription_id من Supabase
    # 2. إلغاء في Stripe: stripe.Subscription.cancel(sub_id)
    # 3. تحديث الحالة في DB
    return {"status": "cancelled"}
```

---

## 📄 PAGE-002: `billing.html` — الفواتير والمدفوعات

### ما يجب أن تحتوي عليه:
```
┌─────────────────────────────────────────────────────┐
│  💳 Billing History                                 │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────────────────────────────────────┐   │
│  │  Date        │  Plan         │  Amount │ PDF │   │
│  │─────────────────────────────────────────────│   │
│  │  May 1, 2025 │  Professional │  $29.99 │ 📥  │   │
│  │  Apr 1, 2025 │  Professional │  $29.99 │ 📥  │   │
│  │  Mar 1, 2025 │  Starter      │  $9.99  │ 📥  │   │
│  └──────────────────────────────────────────────┘   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### الكود (`billing.js`):
```javascript
const { data: invoices } = await supabase
    .from('invoices')
    .select('*')
    .eq('user_id', user.id)
    .order('created_at', { ascending: false });

const tbody = document.getElementById('invoices-tbody');
invoices.forEach(inv => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
        <td>${new Date(inv.created_at).toLocaleDateString()}</td>
        <td>${inv.plan_id}</td>
        <td>$${(inv.amount / 100).toFixed(2)}</td>
        <td>
            <a href="https://stripe.com/invoice/${inv.payment_intent_id}" 
               target="_blank">📥 PDF</a>
        </td>
    `;
    tbody.appendChild(tr);
});
```

---

## 📄 PAGE-003: `join.html` — صفحة انضمام المقابلة (القلب الضارب للـ QR)

### الغرض:
المرشح يستلم QR Code، يمسحه بهاتفه → يُفتح `join.html?room=UUID&name=Ahmed` → ينضم مباشرة للمقابلة **بدون تسجيل دخول**.

### التصميم:
```
┌───────────────────────────────────────────────────┐
│              🎙️ INTEGRA                           │
├───────────────────────────────────────────────────┤
│                                                   │
│           You're invited to                       │
│         Senior Developer Interview                │
│                                                   │
│          📅 Today at 3:00 PM                      │
│          🏢 TechCorp Inc.                         │
│          ⏳ Duration: ~45 minutes                  │
│                                                   │
│   ┌─────────────────────────────────────────┐     │
│   │  Your name                              │     │
│   │  [Ahmed Al-Rashidi                     ]│     │
│   └─────────────────────────────────────────┘     │
│                                                   │
│   [ 🎤 Join Interview Now ]                       │
│                                                   │
│   💡 Make sure your camera and mic are ready      │
│                                                   │
└───────────────────────────────────────────────────┘
```

### الكود (`join.js`):
```javascript
// قراءة params من URL
const params = new URLSearchParams(window.location.search);
const roomId = params.get('room');
const candidateName = params.get('name');  // من QR (prefilled)
const token = params.get('token');          // توكن مؤقت للتحقق

// التحقق من صحة الغرفة
const res = await fetch(`/api/livekit/guest-info?room=${roomId}&token=${token}`);
if (!res.ok) {
    showError('This interview link has expired or is invalid.');
    return;
}
const { roomName, scheduledAt, position } = await res.json();

// عرض المعلومات
document.getElementById('position-title').textContent = position;
document.getElementById('scheduled-time').textContent = 
    new Date(scheduledAt).toLocaleString('ar-SA');

if (candidateName) {
    document.getElementById('candidate-name-input').value = candidateName;
}

// انضمام
document.getElementById('join-btn').addEventListener('click', async () => {
    const name = document.getElementById('candidate-name-input').value.trim();
    if (!name) { showError('Please enter your name'); return; }
    
    // طلب token كـ "candidate" role (بدون تسجيل دخول)
    const tokenRes = await fetch('/api/livekit/guest-token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ room_id: roomId, candidate_name: name, access_token: token })
    });
    
    const { livekit_token } = await tokenRes.json();
    
    // الانضمام للمقابلة
    window.location.href = `integra-session.html?token=${livekit_token}&room=${roomId}&role=candidate&name=${name}`;
});
```

### Backend endpoints مطلوبة:
```python
@app.get("/api/livekit/guest-info")
async def guest_room_info(room: str, token: str):
    """لا يحتاج JWT — يتحقق بـ short-lived token"""
    # تحقق من token المؤقت (حفظ في Redis أو Supabase table)
    node = get_node_by_room_id(room)
    if not node: raise HTTPException(404, "Room not found")
    return {
        "roomName": node["candidate_name"],
        "position": node["position"],
        "scheduledAt": node["scheduled_at"]
    }

@app.post("/api/livekit/guest-token")
async def generate_guest_token(data: dict):
    """يُولّد token للمرشح بدون تسجيل دخول"""
    room_id = data.get("room_id")
    candidate_name = data.get("candidate_name")
    access_token = data.get("access_token")
    
    # تحقق من الـ access_token المؤقت
    # ثم أنشئ LiveKit token بصلاحية can_publish فقط (لا can_publish_data)
    token = generate_livekit_token(room_id, f"candidate_{candidate_name}", role="candidate")
    return {"livekit_token": token}
```

---

## 📄 PAGE-004: `candidate.html` — بوابة المرشح البسيطة

### الغرض:
إذا احتاج المرشح لرابط دائم (بدون QR) — صفحة بسيطة جداً.

**الفرق عن `join.html`:** لا تتطلب room ID في الـ URL، بدلاً من ذلك تعرض جدولاً بمقابلاته المجدولة.

```javascript
// يسجل دخول بـ email فقط (لا password)
const { error } = await supabase.auth.signInWithOtp({ email });
// بعد التحقق → يرى مقابلاته
const { data: myInterviews } = await supabase
    .from('nodes')
    .select('*')
    .eq('candidate_email', user.email)
    .eq('status', 'PENDING');
```

---

## 📄 PAGE-005: `admin.html` — لوحة الإدارة (مستقبلي)

### يحتوي على:
- إجمالي المستخدمين النشطين
- الإيرادات الشهرية
- أكثر الخطط مبيعاً
- المقابلات المجدولة اليوم
- إدارة المستخدمين (تعطيل/تفعيل)

### الحماية:
```python
@app.get("/api/admin/stats")
async def admin_stats(user: dict = Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(403, "Not authorized")
    # ...
```

---

## ترتيب التنفيذ

```
1. join.html      ← مطلوب فوراً للـ QR
2. profile.html   ← مطلوب للمنتج الكامل
3. billing.html   ← مطلوب مع Stripe Webhook
4. candidate.html ← بعد الأساسيات
5. admin.html     ← مرحلة لاحقة
```
