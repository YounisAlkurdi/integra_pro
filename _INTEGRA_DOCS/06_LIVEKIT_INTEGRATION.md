# 📹 تحليل LiveKit Integration

## ما هو LiveKit؟
منصة WebRTC مفتوحة المصدر توفر:
- غرف فيديو/صوت متعددة المشاركين
- SDK لـ JavaScript و Python
- SFU (Selective Forwarding Unit) لأداء عالٍ

---

## الملفات المرتبطة

| الملف | الدور |
|-------|-------|
| `livekit_routes.py` | Backend: توليد JWT وحذف الغرف |
| `integra-session.js` | Frontend: الاتصال بغرفة الفيديو |
| `stt.js` | محرك التحويل الصوتي |
| `.env` | LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET |

---

## تدفق الاتصال الكامل

```
[integra-session.html?room=UUID&role=hr]
     │
     │ 1. يقرأ roomName و participantName من URL
     ▼
POST /api/livekit/token
{roomName, participantName, role}
     │
     │ 2. Backend يتحقق من الجدولة
     │    إذا كان قبل الموعد بأكثر من 5 دقائق → 403
     │
     │ 3. Backend يولّد JWT (30 دقيقة)
     ▼
{ token, url, roomName, ... }
     │
     │ 4. Frontend يستخدم livekit-client SDK
     ▼
LiveKitRoom.connect(url, token)
     │
     │ 5. يُنشئ audio/video tracks
     │ 6. يستمع لـ participant events
     │
     ├── ParticipantConnected → يُضيف video panel
     ├── ParticipantDisconnected → يُزيل video panel
     ├── TrackPublished → يعرض video/audio
     └── DataReceived → رسائل مباشرة بين المشاركين
```

---

## `livekit_routes.py` — تفصيل

### JWT Token Structure:
```python
token = (
    AccessToken(api_key, api_secret)
    .with_identity(req.participantName)      # الاسم الفريد
    .with_name(req.participantName)           # الاسم المعروض
    .with_ttl(timedelta(seconds=1800))        # 30 دقيقة
    .with_metadata('{"role":"hr"}')           # بيانات إضافية
    .with_grants(VideoGrants(
        room_join=True,
        room=req.roomName,
        can_publish=True,      # يبث
        can_subscribe=True,    # يشاهد الآخرين
        can_publish_data=True  # يرسل data messages
    ))
    .to_jwt()
)
```

### الأدوار المدعومة:
| الدور | الصلاحيات |
|-------|-----------|
| `hr` | كامل (بث + مشاهدة + data) |
| `candidate` | كامل (بث + مشاهدة + data) |

> ملاحظة: كلا الدورين لهم نفس الصلاحيات حالياً. في الإنتاج يجب تقييد `candidate` من بعض الأفعال.

### Delete Room:
```python
@router.delete("/room/{room_name}")
async def end_room(room_name: str):
    async with LiveKitAPI(livekit_url, api_key, api_secret) as lk_api:
        await lk_api.room.delete_room(DeleteRoomRequest(room=room_name))
    return {"deleted": True}
```

---

## `stt.js` — محرك التحويل الصوتي

### تقنية: Web Speech API (Browser-native)

**المميزات الحالية:**
```javascript
✅ Continuous mode (يظل مفعلاً)
✅ Interim results (نصوص فورية)
✅ Exponential backoff (300ms → 5000ms)
✅ Noise gate (يتجاهل < 2 أحرف)
✅ Mute/Unmute بدون reset
✅ دعم العربي: lang='ar-SA'
```

### توافق المتصفحات:
| المتصفح | يعمل؟ |
|---------|--------|
| Chrome/Edge | ✅ |
| Firefox | ❌ |
| Safari | ⚠️ جزئي |
| Mobile Chrome | ✅ |

### دمج STT مع Session:
```javascript
// عند انضمام مشارك:
STTEngine.start({
    identity: participant.identity,
    name: participant.name,
    lang: 'ar-SA'  // دعم عربي
});

// عند خروجه:
STTEngine.stop();

// عند اكتمال كلمة:
window.addEventListener('stt:final', (e) => {
    const { text, identity, name } = e.detail;
    appendTranscript(name, text);
    // ⚠️ يجب هنا: saveToSupabase(roomId, identity, text)
});
```

---

## المشاكل الحالية

| المشكلة | التأثير |
|---------|--------|
| ❌ STT لا يُحفظ في `chat_logs` | فقدان كل ما قيل في المقابلة |
| ❌ لا يوجد AI analysis بعد المقابلة | `interview_reports` ظل فارغاً |
| ⚠️ Token لا يتجدد (30 دقيقة فقط) | قد تنتهي المقابلة ويُقطع الاتصال |
| ⚠️ `nodes` table لا يُحدَّث status إلى ACTIVE | لا يعرف النظام أن المقابلة بدأت |
| ⚠️ لا يوجد Recording | لا يمكن مراجعة المقابلة لاحقاً |

---

## تحسينات مقترحة

### 1. حفظ STT في Supabase (أهم شيء!)
```javascript
// في stt.js أو integra-session.js:
window.addEventListener('stt:final', async (e) => {
    await supabase.from('chat_logs').insert({
        room_id: roomId,
        sender: e.detail.name,
        message: e.detail.text,
        user_id: session.user.id  // user_id المُقيِّم (HR)
    });
});
```

### 2. تحديث status العقدة عند بدء المقابلة
```javascript
// في integra-session.js عند الانضمام:
await fetch(`/api/nodes/${roomId}/activate`, { method: 'PATCH' });
```

### 3. توليد تقرير AI بعد انتهاء الجلسة
```javascript
// عند الضغط على "End Session":
const transcript = getAllTranscript();
const aiReport = await generateAIReport(transcript);
await supabase.from('interview_reports').insert({
    room_id: roomId,
    candidate_name: candidateName,
    score: aiReport.score,
    strengths: aiReport.strengths,
    ai_summary: aiReport.summary
});
```

### 4. Token Auto-Refresh (للمقابلات الطويلة > 30 دقيقة)
```javascript
// قبل انتهاء التوكن بـ 5 دقائق:
setTimeout(async () => {
    const newToken = await fetchNewToken();
    await room.reconnect(livekitUrl, newToken);
}, (TOKEN_TTL - 300) * 1000);
```

---

## env vars المطلوبة للـ LiveKit

```env
LIVEKIT_URL=wss://your-project.livekit.cloud   # أو self-hosted
LIVEKIT_API_KEY=APIxxxxxxxxxxxxxxx
LIVEKIT_API_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```
