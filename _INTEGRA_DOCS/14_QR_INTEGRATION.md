# 📱 نظام QR Code — Complete QR Integration Guide

## الفكرة الكاملة

```
[HR ينشئ مقابلة] → [Backend يولّد QR] → [HR يرسله للمرشح]
→ [المرشح يمسح QR] → [join.html تُفتح تلقائياً]
→ [المرشح ينضم للمقابلة فوراً بدون تسجيل دخول]
```

---

## 1. توليد QR في الـ Backend

### تثبيت المكتبة:
```bash
pip install qrcode[pil]
```

أضف لـ `requirements.txt`:
```
qrcode[pil]==7.4.2
Pillow==10.3.0
```

### Backend Endpoint:
```python
# في livekit_routes.py أو routes/qr.py (ملف جديد):
import qrcode
import qrcode.image.svg
from io import BytesIO
import base64
import secrets
import time

QR_TOKENS = {}  # مؤقت — لاحقاً يُحفظ في Supabase

@router.get("/api/nodes/{room_id}/qr")
async def generate_qr(room_id: str, user: dict = Depends(get_current_user)):
    """
    يولّد QR Code لمقابلة محددة.
    المرشح يمسحه ويُفتح له join.html مباشرة.
    """
    # 1. تحقق أن الـ room تخص هذا المستخدم
    node = get_node_by_room_id(room_id)  # من nodes.py
    if not node:
        raise HTTPException(404, "Room not found")
    
    # 2. أنشئ access token مؤقت (صالح 24 ساعة)
    access_token = secrets.token_urlsafe(32)
    expire_at = int(time.time()) + (24 * 60 * 60)  # 24 ساعة
    
    QR_TOKENS[access_token] = {
        "room_id": room_id,
        "expire_at": expire_at,
        "candidate_name": node.get("candidate_name", ""),
        "candidate_email": node.get("candidate_email", "")
    }
    
    # 3. بناء الـ Join URL
    base_url = get_env_safe("APP_BASE_URL", "http://localhost:5500")
    candidate_name_encoded = node.get("candidate_name", "").replace(" ", "+")
    join_url = (
        f"{base_url}/join.html"
        f"?room={room_id}"
        f"&token={access_token}"
        f"&name={candidate_name_encoded}"
    )
    
    # 4. توليد QR Image (PNG)
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # High error correction
        box_size=10,
        border=4,
    )
    qr.add_data(join_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="#6C63FF", back_color="white")  # لون Integra
    
    # 5. إرجاع الصورة كـ base64
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    return {
        "qr_image": f"data:image/png;base64,{img_base64}",
        "join_url": join_url,
        "expires_at": expire_at,
        "candidate_name": node.get("candidate_name"),
        "room_id": room_id
    }


@router.get("/api/livekit/guest-info")
async def guest_room_info(room: str, token: str):
    """
    تحقق من صحة QR token وإرجاع معلومات الغرفة.
    لا يحتاج JWT — للمرشح بدون تسجيل دخول.
    """
    token_data = QR_TOKENS.get(token)
    
    if not token_data:
        raise HTTPException(404, "Invalid or expired QR code")
    
    if int(time.time()) > token_data["expire_at"]:
        del QR_TOKENS[token]
        raise HTTPException(410, "QR code has expired")
    
    if token_data["room_id"] != room:
        raise HTTPException(403, "Token mismatch")
    
    node = get_node_by_room_id(room)
    if not node:
        raise HTTPException(404, "Interview room not found")
    
    return {
        "valid": True,
        "candidate_name": token_data["candidate_name"],
        "position": node.get("position", "Interview"),
        "scheduled_at": node.get("scheduled_at"),
        "interviewer": node.get("interviewer_name", "HR Team")
    }


@router.post("/api/livekit/guest-token")
async def generate_guest_livekit_token(data: dict):
    """
    يولّد LiveKit token للمرشح بعد التحقق من QR.
    لا يحتاج JWT.
    """
    room_id = data.get("room_id")
    candidate_name = data.get("candidate_name", "Candidate")
    access_token = data.get("access_token")
    
    # تحقق من QR token
    token_data = QR_TOKENS.get(access_token)
    if not token_data or token_data["room_id"] != room_id:
        raise HTTPException(403, "Invalid access token")
    
    if int(time.time()) > token_data["expire_at"]:
        raise HTTPException(410, "Access token expired")
    
    # ولّد LiveKit token للمرشح
    from livekit.api import AccessToken, VideoGrants
    import datetime
    
    lk_token = (
        AccessToken(
            get_env_safe("LIVEKIT_API_KEY"),
            get_env_safe("LIVEKIT_API_SECRET")
        )
        .with_identity(f"candidate_{candidate_name.replace(' ', '_')}")
        .with_name(candidate_name)
        .with_ttl(datetime.timedelta(hours=2))  # مقابلة ≤ ساعتين
        .with_grants(VideoGrants(
            room_join=True,
            room=room_id,
            can_publish=True,
            can_subscribe=True,
        ))
        .to_jwt()
    )
    
    return {"livekit_token": lk_token, "room_id": room_id}
```

---

## 2. عرض QR في Dashboard

### في `dashboard.js` — أضف زر QR لكل كارت:
```javascript
function createNodeCard(node) {
    // ... الكود الحالي ...
    
    // أضف زر QR
    const qrBtn = document.createElement('button');
    qrBtn.className = 'qr-btn';
    qrBtn.textContent = '📱 QR Code';
    qrBtn.addEventListener('click', () => showQRModal(node.room_id));
    
    card.appendChild(qrBtn);
    return card;
}

async function showQRModal(roomId) {
    // فتح modal
    const modal = document.getElementById('qr-modal');
    const qrImg = document.getElementById('qr-image');
    const qrLink = document.getElementById('qr-join-link');
    const loading = document.getElementById('qr-loading');
    
    modal.style.display = 'flex';
    loading.style.display = 'block';
    qrImg.style.display = 'none';
    
    try {
        const res = await fetch(`/api/nodes/${roomId}/qr`, {
            headers: { Authorization: `Bearer ${session.access_token}` }
        });
        const data = await res.json();
        
        qrImg.src = data.qr_image;
        qrImg.style.display = 'block';
        qrLink.href = data.join_url;
        qrLink.textContent = data.join_url;
        
        // زر نسخ الرابط
        document.getElementById('copy-link-btn').onclick = () => {
            navigator.clipboard.writeText(data.join_url);
            showToast('Link copied!', 'success');
        };
        
        // زر تحميل QR صورة
        document.getElementById('download-qr-btn').onclick = () => {
            const a = document.createElement('a');
            a.download = `integra-qr-${roomId}.png`;
            a.href = data.qr_image;
            a.click();
        };
        
    } catch (err) {
        showToast('Failed to generate QR', 'error');
    } finally {
        loading.style.display = 'none';
    }
}
```

### HTML Modal في `dashboard.html`:
```html
<!-- QR Modal -->
<div id="qr-modal" class="modal-overlay" style="display:none">
    <div class="modal-box qr-modal-box">
        <button class="modal-close-btn" onclick="closeQRModal()">✕</button>
        
        <h2 class="modal-title">📱 Interview QR Code</h2>
        <p class="modal-subtitle">Share this with the candidate to join the interview</p>
        
        <div id="qr-loading">Generating QR...</div>
        <img id="qr-image" src="" alt="QR Code" class="qr-image-large">
        
        <div class="qr-link-container">
            <a id="qr-join-link" href="#" target="_blank" class="qr-link-text"></a>
        </div>
        
        <div class="qr-actions">
            <button id="copy-link-btn" class="btn btn-secondary">📋 Copy Link</button>
            <button id="download-qr-btn" class="btn btn-primary">📥 Download QR</button>
        </div>
        
        <p class="qr-expire-note">⚠️ This QR code expires in 24 hours</p>
    </div>
</div>
```

### CSS للـ Modal:
```css
.qr-modal-box {
    background: #1a1a2e;
    border: 1px solid rgba(108, 99, 255, 0.3);
    border-radius: 20px;
    padding: 2rem;
    max-width: 420px;
    width: 90%;
    text-align: center;
    animation: slideUp 0.3s ease;
}

.qr-image-large {
    width: 240px;
    height: 240px;
    border-radius: 12px;
    border: 4px solid rgba(108, 99, 255, 0.5);
    margin: 1rem auto;
    display: block;
}

.qr-link-text {
    font-size: 0.75rem;
    color: #888;
    word-break: break-all;
    text-decoration: underline;
}

.qr-actions {
    display: flex;
    gap: 1rem;
    justify-content: center;
    margin-top: 1rem;
}

.qr-expire-note {
    color: #ff6b6b;
    font-size: 0.8rem;
    margin-top: 1rem;
}
```

---

## 3. صفحة `join.html` — الكود الكامل

```html
<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Join Interview — INTEGRA</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Inter', sans-serif;
            background: radial-gradient(ellipse at top, #1a1a3e 0%, #0d0d1a 70%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
        }
        
        .join-card {
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(108, 99, 255, 0.3);
            border-radius: 24px;
            padding: 3rem 2.5rem;
            max-width: 460px;
            width: 90%;
            text-align: center;
        }
        
        .logo {
            font-size: 1.2rem;
            font-weight: 700;
            color: #6C63FF;
            letter-spacing: 3px;
            margin-bottom: 2rem;
        }

        .interview-icon {
            font-size: 3rem;
            margin-bottom: 1rem;
        }
        
        h1 {
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
        }
        
        .meta-info {
            color: rgba(255,255,255,0.5);
            font-size: 0.9rem;
            margin-bottom: 2rem;
        }
        
        .meta-row {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            margin: 0.4rem 0;
        }
        
        .divider {
            height: 1px;
            background: rgba(255,255,255,0.1);
            margin: 1.5rem 0;
        }
        
        label {
            display: block;
            text-align: left;
            font-size: 0.85rem;
            color: rgba(255,255,255,0.6);
            margin-bottom: 0.5rem;
        }
        
        input {
            width: 100%;
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(108, 99, 255, 0.4);
            border-radius: 12px;
            padding: 0.9rem 1rem;
            color: white;
            font-family: inherit;
            font-size: 1rem;
            outline: none;
            transition: border-color 0.2s;
        }
        
        input:focus {
            border-color: #6C63FF;
            background: rgba(108, 99, 255, 0.1);
        }
        
        .join-btn {
            width: 100%;
            background: linear-gradient(135deg, #6C63FF, #5046E5);
            color: white;
            border: none;
            border-radius: 12px;
            padding: 1rem;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            margin-top: 1.5rem;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
        }
        
        .join-btn:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(108, 99, 255, 0.4);
        }
        
        .join-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        
        .tips {
            margin-top: 1.5rem;
            padding: 1rem;
            background: rgba(255,255,255,0.03);
            border-radius: 12px;
            font-size: 0.8rem;
            color: rgba(255,255,255,0.4);
            text-align: left;
        }
        
        .tips ul { padding-left: 1rem; }
        .tips li { margin: 0.3rem 0; }
        
        .error-msg {
            background: rgba(255, 100, 100, 0.15);
            border: 1px solid rgba(255, 100, 100, 0.3);
            border-radius: 10px;
            padding: 0.8rem;
            color: #ff6b6b;
            font-size: 0.85rem;
            margin-top: 1rem;
            display: none;
        }
        
        .loading-overlay {
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.7);
            place-items: center;
            font-size: 1.1rem;
        }
        
        .spinner {
            width: 40px;
            height: 40px;
            border: 3px solid rgba(108, 99, 255, 0.3);
            border-top-color: #6C63FF;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }
        
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>
</head>
<body>

<div class="join-card">
    <div class="logo">INTEGRA</div>
    
    <div class="interview-icon">🎙️</div>
    <h1 id="position-title">Loading Interview...</h1>
    
    <div class="meta-info">
        <div class="meta-row">📅 <span id="scheduled-time">—</span></div>
        <div class="meta-row">👤 <span id="interviewer-name">—</span></div>
    </div>
    
    <div class="divider"></div>
    
    <label for="candidate-name-input">Your Full Name</label>
    <input 
        type="text" 
        id="candidate-name-input" 
        placeholder="Enter your name"
        autocomplete="name"
    >
    
    <div class="error-msg" id="error-msg"></div>
    
    <button class="join-btn" id="join-btn" disabled>
        <span>🎤</span> Join Interview Now
    </button>
    
    <div class="tips">
        <ul>
            <li>Allow camera and microphone access when prompted</li>
            <li>Use Chrome or Edge for best experience</li>
            <li>Find a quiet environment with good lighting</li>
        </ul>
    </div>
</div>

<div class="loading-overlay" id="loading-overlay">
    <div style="text-align:center;">
        <div class="spinner" style="margin:0 auto 1rem;"></div>
        <div>Connecting to interview room...</div>
    </div>
</div>

<script>
const BACKEND_URL = 'http://localhost:8000';

async function init() {
    const params = new URLSearchParams(window.location.search);
    const roomId = params.get('room');
    const token = params.get('token');
    const prefillName = params.get('name');
    
    if (!roomId || !token) {
        showError('Invalid interview link. Please contact your interviewer.');
        return;
    }
    
    if (prefillName) {
        document.getElementById('candidate-name-input').value = 
            decodeURIComponent(prefillName.replace(/\+/g, ' '));
    }
    
    try {
        const res = await fetch(
            `${BACKEND_URL}/api/livekit/guest-info?room=${roomId}&token=${token}`
        );
        
        if (!res.ok) {
            const err = await res.json();
            showError(err.detail || 'This interview link is invalid or has expired.');
            return;
        }
        
        const info = await res.json();
        
        document.getElementById('position-title').textContent = info.position;
        document.getElementById('scheduled-time').textContent = 
            info.scheduled_at ? new Date(info.scheduled_at).toLocaleString() : 'Flexible';
        document.getElementById('interviewer-name').textContent = info.interviewer || 'Interviewer';
        
        document.getElementById('join-btn').disabled = false;
        document.getElementById('join-btn').textContent = '🎤 Join Interview Now';
        
        // Store for join handler
        window._roomData = { roomId, token, info };
        
    } catch (err) {
        showError('Could not load interview details. Check your connection.');
    }
}

document.getElementById('join-btn').addEventListener('click', async () => {
    const name = document.getElementById('candidate-name-input').value.trim();
    if (!name) { showError('Please enter your full name.'); return; }
    
    const { roomId, token } = window._roomData;
    const btn = document.getElementById('join-btn');
    btn.disabled = true;
    btn.textContent = 'Connecting...';
    
    document.getElementById('loading-overlay').style.display = 'grid';
    
    try {
        const res = await fetch(`${BACKEND_URL}/api/livekit/guest-token`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                room_id: roomId,
                candidate_name: name,
                access_token: token
            })
        });
        
        if (!res.ok) throw new Error('Failed to get session token');
        
        const { livekit_token } = await res.json();
        
        // انتقل لصفحة الجلسة
        const dest = `integra-session.html?token=${encodeURIComponent(livekit_token)}&room=${roomId}&role=candidate&name=${encodeURIComponent(name)}`;
        window.location.href = dest;
        
    } catch (err) {
        document.getElementById('loading-overlay').style.display = 'none';
        btn.disabled = false;
        btn.textContent = '🎤 Join Interview Now';
        showError('Failed to connect. Please try again or contact your interviewer.');
    }
});

function showError(msg) {
    const el = document.getElementById('error-msg');
    el.textContent = msg;
    el.style.display = 'block';
    document.getElementById('join-btn').disabled = true;
    document.getElementById('join-btn').textContent = '⚠️ Cannot Join';
}

init();
</script>
</body>
</html>
```

---

## 4. إضافة قرار "إرسال QR بالإيميل"

### إرسال QR عبر Supabase Edge Function:
```typescript
// supabase/functions/send-qr-email/index.ts
import { serve } from "https://deno.land/std/http/server.ts";
import { Resend } from "npm:resend";

serve(async (req) => {
    const { candidateEmail, candidateName, qrImageBase64, joinUrl, position } = await req.json();
    
    const resend = new Resend(Deno.env.get("RESEND_API_KEY"));
    
    await resend.emails.send({
        from: "interviews@integra.ai",
        to: candidateEmail,
        subject: `You're invited to interview for ${position}`,
        html: `
            <h2>Hello ${candidateName}! 👋</h2>
            <p>You have been invited to interview for <strong>${position}</strong>.</p>
            
            <h3>To join the interview:</h3>
            <ol>
                <li>Scan the QR code below with your phone</li>
                <li>Or click this link: <a href="${joinUrl}">${joinUrl}</a></li>
            </ol>
            
            <img src="${qrImageBase64}" alt="Interview QR Code" width="200">
            
            <p><em>This link expires in 24 hours.</em></p>
            <p>Good luck! 🍀</p>
            
            <hr>
            <small>Powered by INTEGRA — AI Interview Platform</small>
        `
    });
    
    return new Response(JSON.stringify({ sent: true }), {
        headers: { "Content-Type": "application/json" }
    });
});
```

---

## 5. خلاصة التكامل الكامل

```
HR Dashboard
    │
    ├─ [📱 QR Code] زر في كل كارت مقابلة
    │       │
    │       ▼
    │   GET /api/nodes/{room_id}/qr
    │       │
    │       ├─ ينشئ access_token (24h)
    │       ├─ يبني Join URL
    │       └─ يولّد QR PNG ← يُعرض في Modal
    │
    │   [📋 Copy Link] [📥 Download QR] [📧 Email to Candidate]
    │
Candidate Phone
    │
    ├─ يمسح QR
    │       │
    │       ▼
    │   join.html?room=UUID&token=TOKEN&name=Ahmed
    │       │
    │       ├─ GET /api/livekit/guest-info ← يتحقق من token
    │       ├─ يعرض: Position, Time, Interviewer
    │       └─ [Join Interview Now] →
    │               │
    │               ▼
    │       POST /api/livekit/guest-token
    │               │
    │               └─ integra-session.html?token=LK_TOKEN&role=candidate
```
