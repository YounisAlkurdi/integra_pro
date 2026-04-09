# ✨ الميزات الناقصة — Missing Features

## 🔴 ميزات غائبة تؤثر على المنتج الأساسي

### FEAT-001: AI Interview Analysis (المحرك الأهم!)
**الوصف:** بعد انتهاء كل مقابلة، يجب أن يُحلِّل الذكاء الاصطناعي نص المحادثة ويولّد تقريراً حقيقياً.

**حالة:** `interview_reports` table موجودة لكن **لا شيء يكتب فيها**.

**ما يجب بناؤه:**
- endpoint: `POST /api/analyze-interview`
- يُرسل transcript من `chat_logs` لنموذج AI (Gemini/GPT)
- يُخزن النتيجة في `interview_reports`
- `reports.js` يقرأ من `interview_reports` بدلاً من أرقام عشوائية

**التكامل المقترح:** Google Gemini API (pro أو flash)
```python
import google.generativeai as genai

def analyze_transcript(transcript: list):
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""
    أنت محلل مقابلات متخصص. حلّل هذه المقابلة وأعطِ:
    1. درجة من 100
    2. نقاط القوة (3)
    3. نقاط الضعف (3)
    4. ملخص تنفيذي (100 كلمة)
    
    المقابلة:
    {format_transcript(transcript)}
    
    أرجع JSON فقط.
    """
    result = model.generate_content(prompt)
    return json.loads(result.text)
```

---

### FEAT-002: صفحة الفواتير (Billing History)
**الوصف:** يحتاج المستخدم لمكان يرى فيه فواتيره السابقة.

**الجدول:** `invoices` (موجود لكن فارغ ولا صفحة تعرضه)

**ما يجب بناؤه:**
- صفحة `billing.html` أو قسم في `profile.html`
- تعرض: التاريخ، المبلغ، الخطة، الحالة
- زر تحميل PDF للفاتورة (Stripe يوفر هذا)

---

### FEAT-003: Real-time Dashboard Updates
**الوصف:** لوحة التحكم لا تتحدث تلقائياً عند إضافة مقابلة جديدة.

**الحل:** Supabase Realtime subscriptions:
```javascript
supabase.channel('nodes')
    .on('postgres_changes', { 
        event: 'INSERT', schema: 'public', table: 'nodes' 
    }, (payload) => {
        addNodeCard(payload.new);
    })
    .subscribe();
```

---

### FEAT-004: Subscription Limit Enforcement
**الوصف:** لا يوجد شيء يمنع المستخدم من تجاوز حد مقابلاته.

**ما يجب بناؤه:**
- قبل `POST /api/nodes`، تحقق من `interviews_computed < interviews_limit`
- إذا وصل الحد → أرجع 403 وأخبر المستخدم بالترقية
- `interviews_computed` يتزايد تلقائياً عند إنشاء node جديد

---

### FEAT-005: Cancel Subscription
**الوصف:** لا يوجد طريقة للمستخدم لإلغاء اشتراكه.

**ما يجب بناؤه:**
- زر "Cancel Subscription" في بروفايل
- `DELETE /api/subscription` → يلغي اشتراك Stripe

---

## 🟡 ميزات تحسّن التجربة

### FEAT-006: Email Notifications
- إيميل تأكيد الاشتراك
- إيميل قبل المقابلة بـ 24 ساعة
- إيميل ملخص التقرير بعد المقابلة

**الأدوات:** Supabase Edge Functions + Resend.com أو SendGrid

---

### FEAT-007: Candidate Portal (بوابة المرشح)
**الوصف:** المرشح يحتاج صفحة منفصلة (لا `dashboard.html`) بدون صلاحيات HR.

**ما يجب بناؤه:**
- `candidate.html` — صفحة بسيطة للمرشح
- تعرض: معلومات المقابلة، رابط للانضمام
- لا تعرض: بيانات مرشحين آخرين أو أدوات HR

---

### FEAT-008: Recording المقابلة
**الوصف:** تسجيل فيديو/صوت للمقابلة للمراجعة لاحقاً.

**الأدوات:** LiveKit Cloud يوفر Recording API:
```python
from livekit.api import LiveKitAPI, StartEgressRequest
await lk_api.egress.start_room_composite_egress(
    StartEgressRequest(
        room_name=room_name,
        file=EncodedFileOutput(filepath="s3://bucket/recording.mp4")
    )
)
```

---

### FEAT-009: متعدد المقيّمين (Co-Interviewers)
**الوصف:** السماح لأكثر من HR بالانضمام لنفس المقابلة.

**ما يجب تعديله:**
- في `nodes` table: إضافة `interviewers: uuid[]`
- في `livekit_routes.py`: السماح لأكثر من `hr` role

---

### FEAT-010: لوحة تحكم إدارية (Super Admin)
**الوصف:** صفحة لإدارة كل المستخدمين والاشتراكات.

**ما تحتاجه:**
- جدول `admins` أو قيد في `auth.users.metadata`
- صفحة `admin.html` مع Supabase service role
- إحصائيات: إجمالي الإيرادات، المستخدمين النشطين، المقابلات اليوم

---

## 🟢 ميزات تعزّز القيمة التنافسية

### FEAT-011: استيراد أسئلة بالـ AI
- المستخدم يُدخل الوظيفة → AI تولّد أسئلة مناسبة

### FEAT-012: مقارنة المرشحين
- عرض تقارير مرشحين متعددين جنباً إلى جنب

### FEAT-013: API للمطورين
- REST API مع توثيق Swagger لدمج Integra في أنظمة HR الأخرى

### FEAT-014: Mobile App
- React Native app للـ HR للمراجعة والجدولة من هاتفهم

### FEAT-015: تحليل لغة الجسد (Vision AI)
- تحليل تعابير الوجه خلال المقابلة باستخدام Google Vision API

---

## ملخص الميزات

| الفئة | العدد | الأولوية |
|-------|-------|---------|
| 🔴 غائبة حرجة | 5 | يجب بناؤها فوراً |
| 🟡 تحسّن التجربة | 5 | خلال شهر |
| 🟢 تنافسية | 5 | المرحلة القادمة |
