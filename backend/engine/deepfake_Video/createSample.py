import cv2
import time

# إعدادات الكاميرا
cap = cv2.VideoCapture(0)

# تعريف الكوديك للصيغة mp4 (H.264)
# ملاحظة: إذا لم يعمل avc1، جرب تبديله بـ 'mp4v'
fourcc = cv2.VideoWriter_fourcc(*'mp4v') 
out = cv2.VideoWriter('integra_sample.mp4', fourcc, 20.0, (640, 480))

if not cap.isOpened():
    print("❌ خطأ: لا يمكن فتح الكاميرا")
    exit()

print("🔴 بدأ التسجيل الآن (المطلوب 10 ثواني)...")
start_time = time.time()

while True:
    ret, frame = cap.read()
    if ret:
        # كتابة الفريم في الملف
        out.write(frame)
        
        # عرض الكاميرا أمامك
        cv2.imshow('Recording MP4 for Integra', frame)
        
        # حساب الوقت
        elapsed_time = time.time() - start_time
        if elapsed_time >= 10:
            break
            
        # الخروج إذا ضغطت Esc
        if cv2.waitKey(1) & 0xFF == 27:
            break
    else:
        break

# تنظيف الموارد
cap.release()
out.release()
cv2.destroyAllWindows()

print(f"✅ تم بنجاح! الفيديو جاهز باسم: integra_sample.mp4")
print(f"⏱️ الوقت الفعلي المستغرق: {elapsed_time:.2f} ثانية")