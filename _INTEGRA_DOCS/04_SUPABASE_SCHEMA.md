# 🗄️ توثيق Supabase — قاعدة البيانات الكاملة

**Project ID:** `ljnclcivnbhjjofsfyzm`
**Project URL:** `https://ljnclcivnbhjjofsfyzm.supabase.co`

---

## الجداول الموجودة حالياً (5 جداول)

### 1. جدول `nodes` — جلسات المقابلات

| العمود | النوع | الوصف |
|--------|-------|-------|
| `room_id` | `uuid` (PK) | معرف الغرفة الفريد |
| `candidate_name` | `text NOT NULL` | اسم المرشح |
| `candidate_email` | `text (nullable)` | إيميل المرشح |
| `position` | `text NOT NULL` | الوظيفة |
| `questions` | `jsonb (nullable)` | قائمة الأسئلة |
| `scheduled_at` | `text NOT NULL` | وقت الجدولة (نص!) |
| `status` | `text` (default: 'PENDING') | حالة المقابلة |
| `created_at` | `timestamptz` | وقت الإنشاء |
| `user_id` | `uuid (FK → auth.users.id)` | مالك الجلسة |

**RLS مفعّل:** ✅  
**صفوف حالية:** 0 (البيانات في JSON Buffer!)

**مشاكل التصميم:**
- `scheduled_at` يجب أن يكون `timestamptz` لا `text` (لإتاحة queries بالتاريخ)
- `status` يجب قيوده بـ CHECK constraint: `IN ('PENDING', 'ACTIVE', 'COMPLETED', 'CANCELLED')`

**SQL لإصلاح scheduled_at:**
```sql
ALTER TABLE nodes 
ADD COLUMN scheduled_at_ts TIMESTAMPTZ 
GENERATED ALWAYS AS (scheduled_at::TIMESTAMPTZ) STORED;
-- أو تحويل العمود مباشرة (بعد migration البيانات)
```

---

### 2. جدول `subscriptions` — اشتراكات المستخدمين

| العمود | النوع | الوصف |
|--------|-------|-------|
| `id` | `uuid` (PK) | معرف الاشتراك |
| `user_id` | `uuid (FK)` | المستخدم |
| `plan_id` | `text` | معرف الخطة (starter/professional/enterprise) |
| `status` | `text` | الحالة (active/cancelled/expired) |
| `interviews_computed` | `int4` (default: 0) | عدد المقابلات المُنجزة |
| `interviews_limit` | `int4` (default: 10) | الحد الأقصى |
| `start_date` | `timestamptz` | تاريخ بدء الاشتراك |
| `next_billing_date` | `timestamptz` | موعد الفاتورة القادمة |
| `payment_intent_id` | `text` | معرف دفع Stripe |
| `created_at` | `timestamptz` | وقت الإنشاء |

**RLS مفعّل:** ✅  
**صفوف حالية:** 2

**المشكلة:** backend لا يحدّث هذا الجدول عند نجاح الدفع!

---

### 3. جدول `invoices` — الفواتير

| العمود | النوع | الوصف |
|--------|-------|-------|
| `id` | `uuid` (PK) | معرف الفاتورة |
| `user_id` | `uuid (FK)` | المستخدم |
| `amount` | `int4` | المبلغ (بالسنتات) |
| `plan_id` | `text` | نوع الخطة |
| `payment_intent_id` | `text` | معرف Stripe |
| `status` | `text` (default: 'PAID') | الحالة |
| `created_at` | `timestamptz` | وقت الإنشاء |

**RLS مفعّل:** ✅  
**صفوف حالية:** 0 (لا يُكتب فيه حالياً!)

**ما ينقصه:**
- `currency` (USD/SAR/etc.)
- `description` — وصف الفاتورة
- `stripe_invoice_id` — ربط مع Stripe Invoices

---

### 4. جدول `interview_reports` — تقارير المقابلات

| العمود | النوع | الوصف |
|--------|-------|-------|
| `id` | `uuid` (PK) | معرف التقرير |
| `room_id` | `text` | معرف غرفة المقابلة |
| `score` | `int4` | درجة المرشح |
| `strengths` | `jsonb` | نقاط القوة |
| `weaknesses` | `jsonb` | نقاط الضعف |
| `ai_summary` | `text` | ملخص الذكاء الاصطناعي |
| `user_id` | `uuid (FK)` | المُقيِّم |
| `candidate_name` | `text` | اسم المرشح |
| `created_at` / `updated_at` | `timestamptz` | التوقيتات |

**RLS مفعّل:** ✅  
**صفوف حالية:** 0

**المشكلة:** يجب أن يُملأ بعد انتهاء كل مقابلة (لا يوجد كود يفعل ذلك حالياً).

---

### 5. جدول `chat_logs` — سجل المحادثة النصية

| العمود | النوع | الوصف |
|--------|-------|-------|
| `id` | `uuid` (PK) | معرف الرسالة |
| `room_id` | `text` | معرف الغرفة |
| `sender` | `text` | اسم المتحدث |
| `message` | `text` | النص المنطوق |
| `user_id` | `uuid (FK)` | مالك الجلسة |
| `created_at` | `timestamptz` | وقت الرسالة |

**RLS مفعّل:** ✅  
**صفوف حالية:** 0 (STT يعمل لكن لا يُحفظ!)

---

## RLS Policies (المطلوبة)

يجب التحقق من وجود هذه سياسات RLS:

```sql
-- للمستخدمين: يرون بياناتهم فقط
CREATE POLICY "Users can read own nodes" ON nodes
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own nodes" ON nodes
  FOR INSERT WITH CHECK (auth.uid() = user_id);

-- للاشتراكات
CREATE POLICY "Users can read own subscription" ON subscriptions
  FOR SELECT USING (auth.uid() = user_id);

-- للفواتير
CREATE POLICY "Users can read own invoices" ON invoices
  FOR SELECT USING (auth.uid() = user_id);

-- للتقارير
CREATE POLICY "Users can read own reports" ON interview_reports
  FOR SELECT USING (auth.uid() = user_id);

-- للمحادثات
CREATE POLICY "Users can read own chat logs" ON chat_logs
  FOR SELECT USING (auth.uid() = user_id);
```

---

## مخطط العلاقات (ERD)

```
auth.users (Supabase built-in)
    │
    ├──→ nodes (user_id FK)
    │         └──→ interview_reports (room_id)
    │         └──→ chat_logs (room_id)
    │
    ├──→ subscriptions (user_id FK)
    │
    └──→ invoices (user_id FK)
```

---

## حالة الجداول

| الجدول | يُكتب فيه؟ | يُقرأ منه؟ | RLS | حالة |
|--------|-----------|-----------|-----|------|
| `nodes` | ❌ (JSON) | ⚠️ (reports.js فقط) | ✅ | 🔴 |
| `subscriptions` | ❌ | ❌ | ✅ | 🟡 |
| `invoices` | ❌ | ❌ | ✅ | 🔴 |
| `interview_reports` | ❌ | ❌ | ✅ | 🔴 |
| `chat_logs` | ❌ | ❌ | ✅ | 🔴 |
