import os
import shutil
import time
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from processor import FullDeepfakeDetector
import uvicorn

app = FastAPI()

# تحميل الموديلات عند التشغيل (مثل الخلية 3)
print("⏳ Loading Models... Please wait...")
detector = FullDeepfakeDetector()
print("✅ Server Ready!")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/analyze")
async def analyze_video(file: UploadFile = File(...)):
    # إنشاء ملف مؤقت محمي
    temp_path = f"temp_{int(time.time())}_{file.filename}"
    
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # استدعاء التحليل بنفس المنطق الأصلي
        result = detector.analyze(temp_path)
        return result
    except Exception as e:
        return {"error": str(e)}
    finally:
        # حل مشكلة الصلاحيات في ويندوز (تأخير الحذف قليلاً)
        if os.path.exists(temp_path):
            try:
                time.sleep(0.7)
                os.remove(temp_path)
            except:
                pass

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)