# 🌐 تحليل Frontend — صفحة بصفحة

## 1. `index.html` — Landing Page (الصفحة الرئيسية)

### الوصف:
صفحة تسويقية تعرض المنصة بأسلوب سيبراني/مستقبلي مع Glassmorphism.

### ما تحتويه:
- Hero Section مع نصوص متحركة
- Features Section
- خلفية متحركة بالـ Canvas (نقاط متصلة)
- زر "Begin Protocol" → يوجه لـ login.html
- Pricing Section (تعرض من `pricing.json`)

### المشاكل:
- لا يوجد SEO Meta tags كافية
- الـ Canvas animation قد تستهلك CPU على mobile

---

## 2. `login.html` + `login.js` — تسجيل الدخول

### Auth Methods المدعومة:
| الطريقة | الحالة |
|---------|--------|
| Google OAuth (PKCE flow) | ✅ يعمل |
| Email Magic Link (OTP) | ✅ يعمل |

### تدفق المصادقة:
```
1. المستخدم يُدخل Email
2. Supabase يُرسل OTP (6-رقم)
3. المستخدم يُدخل OTP
4. Supabase يُرجع Session
5. يُحوَّل لـ dashboard.html (مع Bearer token)
```

### كود التحقق من الجلسة عند التحميل:
```javascript
const { data: { session } } = await supabase.auth.getSession();
if (session) window.location.href = 'dashboard.html'; // ✅ منع الدخول المكرر
```

### المشاكل:
- ⚠️ `redirectTo: window.location.origin + '/dashboard.html'` — في بيئة local `window.location.origin` قد يكون `null`
- ⚠️ `shouldCreateUser: true` — أي شخص يمكنه إنشاء حساب (ربما مقصود)

---

## 3. `dashboard.html` + `dashboard.js` — لوحة التحكم الرئيسية

### القسم 1: عرض بطاقات المقابلات
- يجلب من `/api/nodes` (يقرأ من `nodes_buffer.json`)
- يعرض: اسم المرشح، الوظيفة، الوقت، الحالة (PENDING/ACTIVE)

### القسم 2: إنشاء مقابلة جديدة (Modal)
- نموذج يحتوي: اسم، إيميل، وظيفة، وقت الجدولة، أسئلة
- يُرسل POST لـ `/api/nodes`
- يُعيد رسم البطاقات

### القسم 3: إحصائيات (Stats Cards)
- يجلب من `/api/stats`
- يعرض: إجمالي، نشطة، مكتملة، تهديدات (= 0 دائماً)

### المشاكل:
- ⚠️ البيانات تأتي من JSON file لا Supabase (فقدان البيانات عند restart السيرفر)
- ⚠️ لا يوجد Real-time updates (لا Supabase subscription)
- ⚠️ لا يوجد Pagination للمقابلات الكثيرة
- ⚠️ لا تحقق من حد الاشتراك (`interviews_limit`)

---

## 4. `integra-session.html` + `integra-session.js` — غرفة المقابلة

### أكثر الصفحات تعقيداً في المشروع!

### المميزات:
| الميزة | الحالة |
|--------|--------|
| Video Grid متعدد المشاركين | ✅ يعمل |
| Audio Tracks | ✅ يعمل |
| STT مباشر (محلي/Web Speech API) | ✅ يعمل |
| مؤشر المتكلم الحالي | ✅ يعمل |
| شريط نص المحادثة (Transcript) | ✅ يعمل |
| زر إنهاء الجلسة | ✅ يعمل |
| Reconnection Logic | ✅ يعمل |
| قائمة الأسئلة | ✅ يعمل |

### تدفق الاتصال:
```
1. يقرأ roomId من URL params
2. يطلب JWT من /api/livekit/token
3. يتصل بـ LiveKit room عبر WebRTC
4. يُنشئ audio/video tracks  
5. يُشغّل STTEngine لكل مشارك
6. يُرسل stt:final events → يُحدّث transcript
```

### `stt.js` — محرك تحويل الصوت:
```javascript
const STTEngine = (() => {
    // ✅ Exponential Backoff (300ms → 600ms → ... → 5000ms)
    // ✅ Noise gate (يتجاهل النصوص < 2 أحرف)
    // ✅ Mute/Unmute بدون إعادة تهيئة
    // ✅ دعم العربي والإنجليزي (lang: 'ar-SA')
})();
```

### المشاكل:
- ❌ لا يُحفظ transcript في `chat_logs` Supabase table
- ⚠️ Web Speech API لا تعمل على Firefox و Safari (Chromium فقط)
- ⚠️ لا يوجد AI analysis بعد انتهاء الجلسة (لا يُنشئ `interview_reports`)
- ⚠️ الأسئلة تأتي من URL params (غير آمن، ممكن التلاعب)

---

## 5. `reports.html` + `reports.js` — صفحة التقارير

### ما تفعله:
```javascript
// يجلب من Supabase مباشرة (✅ صحيح!)
const { data: nodes } = await supabase.from('nodes').select('*')

// لكن يولّد تقارير وهمية! ❌
function generateAnalysisCluster() {
    return {
        overall: Math.floor(Math.random() * 20) + 78, // ← عشوائي!
        confidence: 81 + Math.floor(Math.random() * 15),
        fraud: 2 + Math.floor(Math.random() * 15),
        // ...
    };
}
```

### المشاكل الكبيرة:
- ❌ **التقارير كلها وهمية (Random numbers)** — لا يوجد AI analysis حقيقي
- ❌ جدول `interview_reports` موجود في Supabase لكن لا يُقرأ منه
- ❌ جدول `chat_logs` موجود لكن لا يُعرض في التقارير
- ⚠️ يقرأ من `nodes` table لكن `nodes` في Supabase فارغة (البيانات في JSON)

---

## 6. `appointments.html` + `appointments.js` — صفحة الجدول الزمني

### أروع صفحة UX في المشروع! (Calendar View)

### ما تفعله:
- تقويم أسبوعي تفاعلي (08:00 → 22:00)
- يعرض المقابلات كـ blocks في الوقت الصحيح
- Real-time "Now Line" يتحرك مع الوقت
- قائمة مقابلات اليوم في Sidebar

### المشكلة:
```javascript
// يجلب من Backend API (JSON Buffer) لا Supabase مباشرة
const res = await fetch(window.INTEGRA_SETTINGS.endpoint('/api/nodes'), {
    headers: { 'Authorization': `Bearer ${session.access_token}` }
});
```
- ❌ لا يوجد real-time sync (لا تحديث تلقائي)
- ❌ لا يمكن إنشاء مواعيد من هذه الصفحة

---

## 7. `pricing.html` + `pricing.js` — صفحة الأسعار

### المميزات:
- تبديل Monthly/Yearly مع Animation للأسعار
- 3D Tilt effect على بطاقات الأسعار (Neat!)
- يقرأ الأسعار مباشرة من HTML (hardcoded)

### عند الاختيار:
```javascript
window.selectPlan = (planId) => {
    window.location.href = `checkout.html?plan=${planId}&mode=${mode}`;
};
```

### المشكلة:
- ⚠️ الأسعار Hardcoded في HTML (ليست من `pricing.json`)
- ⚠️ لا يتحقق من الاشتراك الحالي (قد يدفع مستخدم مشترك مسبقاً)

---

## 8. `checkout.html` + `checkout.js` — صفحة الدفع

### يستخدم Stripe Elements (Frontend):
```javascript
const stripe = Stripe(INTEGRA_SETTINGS.STRIPE_PK);
const elements = stripe.elements();
const cardElement = elements.create('card');
```

### تدفق الدفع:
```
1. يقرأ plan + mode من URL params
2. يجلب Stripe PK من /config
3. يُنشئ PaymentIntent من /create-payment-intent
4. يعرض Stripe Card Element
5. عند Submit → stripe.confirmCardPayment()
6. عند النجاح → يوجّه لـ success page
```

### المشاكل:
- ❌ **عند نجاح الدفع، لا يُحدَّث subscriptions أو invoices في Supabase**
- ❌ لا يوجد Webhook من Stripe (الأمان ضعيف)
- ❌ يُعيد success الـ URL إلى `profile.html` لكن صفحة profile لا تعرف أن الدفع نجح

---

## 9. `settings.js` — الإعدادات المركزية

```javascript
window.INTEGRA_SETTINGS = {
    BASE_URL: "http://localhost:8000",  // ⚠️ Hardcoded localhost!
    SUPABASE_URL: 'https://...',
    SUPABASE_ANON_KEY: 'eyJ...',       // ⚠️ مفتاح مكشوف في كل الملفات
};
```

### مشكلة كشف المفاتيح:
- `SUPABASE_ANON_KEY` في ملفات frontend هو أمر متوقع لكن يجب تقييد الـ Row Level Security
- ⚠️ `BASE_URL` يجب أن يتغير في الإنتاج

---

## 10. `supabase-client.js` — تهيئة Supabase Client

```javascript
import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js/+esm';

window.supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
export const supabase = window.supabase;
```

**ملاحظة:** يستخدم CDN (لا npm) — مناسب لـ Vanilla JS بدون bundler.
