# 💳 تحليل Stripe Integration

## الوضع الحالي

### ملفات ذات صلة:
- `payments.py` — Backend (إنشاء PaymentIntent)
- `checkout.js` / `checkout.html` — Frontend (Stripe Elements)
- `pricing.js` / `pricing.html` — صفحة الأسعار
- `pricing.json` — بيانات الأسعار

---

## خطة الأسعار الحالية

| الخطة | شهري | سنوي | الحد |
|-------|------|------|------|
| Starter | $99/mo | $79/mo | 500 مقابلة |
| Professional | $299/mo | $239/mo | Unlimited |
| Enterprise | Custom | Custom | مخصص |

---

## تدفق الدفع الحالي

```
[pricing.html]
     │
     │ selectPlan('starter', 'monthly')
     ▼
[checkout.html?plan=starter&mode=monthly]
     │
     │ 1. GET /config → Stripe Publishable Key
     │ 2. POST /create-payment-intent → clientSecret
     ▼
[Stripe Elements Card Form]
     │
     │ stripe.confirmCardPayment(clientSecret)
     ▼
✅ Payment Succeeded
     │
     │ ← ❌ لا يوجد إشعار لـ Backend!
     │ ← ❌ لا يُحدَّث subscriptions
     │ ← ❌ لا تُنشأ invoice
     ▼
redirect to profile.html
```

---

## الكود الحالي في `payments.py`

```python
@app.post("/create-payment-intent")
async def create_payment_intent(payment_req: PaymentRequest, user: dict = Depends(get_current_user)):
    intent = stripe.PaymentIntent.create(
        amount=payment_req.amount,      # بالسنتات
        currency=payment_req.currency,  # "usd"
        payment_method_types=["card"],
        metadata={
            "plan_id": payment_req.plan_id,  # "starter"
            "user_email": user.get("email") or "unknown"
        }
    )
    return {"clientSecret": intent.client_secret}
```

---

## المشاكل الحالية

| المشكلة | الخطورة | الأثر |
|---------|--------|-------|
| ❌ لا يوجد Webhook (payment confirmation) | 🔴 حرج | الدفع قد يتم دون تفعيل الاشتراك |
| ❌ لا يُكتب في `invoices` table | 🔴 حرج | لا توجد فواتير للمستخدم |
| ❌ لا يُحدَّث `subscriptions` table | 🔴 حرج | المستخدم يدفع لكن لا يحصل على الخدمة |
| ⚠️ STRIPE_SECRET_KEY في .env | 🟡 متوسط | يجب عدم كشفه في الـ logs |
| ⚠️ لا يتحقق من اشتراك موجود | 🟡 متوسط | قد يدفع المستخدم مرتين |

---

## الحل الصحيح (Webhook-Based)

### الخطوة 1: أضف Stripe Webhook endpoint

```python
# في main.py:
@app.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.getenv("STRIPE_WEBHOOK_SECRET")
        )
    except:
        raise HTTPException(400, "Invalid signature")
    
    if event["type"] == "payment_intent.succeeded":
        intent = event["data"]["object"]
        user_email = intent["metadata"].get("user_email")
        plan_id = intent["metadata"].get("plan_id")
        amount = intent["amount"]
        
        # 1. جلب user_id من Supabase
        # 2. إضافة سجل في invoices
        # 3. تحديث/إنشاء subscriptions
        await handle_successful_payment(user_email, plan_id, amount, intent["id"])
    
    return {"received": True}
```

### الخطوة 2: دالة تحديث DB

```python
async def handle_successful_payment(email: str, plan_id: str, amount: int, intent_id: str):
    # جلب user_id
    user_resp = supabase_client.from_("auth.users")... # يحتاج service role key
    
    # إضافة invoice
    supabase_client.from_("invoices").insert({
        "user_id": user_id,
        "amount": amount,
        "plan_id": plan_id,
        "payment_intent_id": intent_id,
        "status": "PAID"
    }).execute()
    
    # تحديث subscription
    limits = {"starter": 500, "professional": 99999}
    supabase_client.from_("subscriptions").upsert({
        "user_id": user_id,
        "plan_id": plan_id,
        "status": "active",
        "interviews_limit": limits.get(plan_id, 10),
        "payment_intent_id": intent_id,
        "next_billing_date": (datetime.now() + timedelta(days=30)).isoformat()
    }, on_conflict="user_id").execute()
```

---

## env vars المطلوبة لـ Stripe

```env
STRIPE_SECRET_KEY=sk_live_...    # أو sk_test_... للتطوير
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...  # من Stripe Dashboard → Webhooks
```

---

## Products و Prices في Stripe Dashboard

يُنصح بإنشاء Products و Prices في Stripe:

```
Product: "Integra Starter"
  Price: $99/month (recurring) → price_starter_monthly
  Price: $79/month (annual)   → price_starter_yearly

Product: "Integra Professional"
  Price: $299/month → price_pro_monthly
  Price: $239/month → price_pro_yearly
```

ثم استخدام `price_id` في الـ Checkout بدلاً من `amount` يدوياً.

---

## خارطة طريق Stripe الكاملة

- [ ] إضافة Webhook endpoint و STRIPE_WEBHOOK_SECRET
- [ ] تفعيل الكتابة في `invoices` و `subscriptions` عند الدفع
- [ ] إضافة Check للاشتراك الحالي قبل الدفع
- [ ] إضافة صفحة فواتير (billing history)
- [ ] Cancel Subscription logic
- [ ] Refund workflow عبر Stripe Dashboard أو API
