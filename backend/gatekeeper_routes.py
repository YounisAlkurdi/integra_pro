from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
import os
import uuid
import shutil
import tempfile
from engine.deepfake_Video.processor import FullDeepfakeDetector
from nodes import _supabase_request

router = APIRouter(tags=["Gatekeeper"])

# Initialize the detector once to save memory and time
print("🛡️ Gatekeeper: Initializing Deepfake Verification Engine...")
detector = FullDeepfakeDetector()

def process_video_and_update_db(request_id: str, video_path: str):
    """
    Background task to process video and update Supabase.
    """
    try:
        print(f"🔍 Gatekeeper: Analyzing video for request {request_id}...")
        
        # 1. Run Analysis
        results = detector.analyze(video_path)
        
        if "error" in results:
            _supabase_request("PATCH", f"join_requests?id=eq.{request_id}", {
                "liveness_status": "FAILED"
            })
            return

        # 2. Extract results
        verdict = results.get("verdict", "UNCERTAIN")
        score = results.get("final_score", 0.0)
        report_b64 = results.get("report_image", "") # This is the base64 plot

        # 3. Determine Database Status
        # We use 'VERIFIED' only if REAL, otherwise 'FAILED' or 'UNCERTAIN'
        db_status = "VERIFIED" if verdict == "REAL" else "FAILED"
        if verdict == "UNCERTAIN": db_status = "UNCERTAIN"

        # 4. Update Supabase
        update_data = {
            "liveness_status": db_status,
            "deepfake_score": float(score),
            "forensic_report_url": report_b64
        }
        
        print(f"✅ Gatekeeper: Analysis complete. Result: {verdict} ({score:.2f})")
        _supabase_request("PATCH", f"join_requests?id=eq.{request_id}", update_data)

    except Exception as e:
        print(f"❌ Gatekeeper Error: {str(e)}")
        _supabase_request("PATCH", f"join_requests?id=eq.{request_id}", {
            "liveness_status": "ERROR"
        })
    finally:
        # Cleanup: Delete the temp video file
        if os.path.exists(video_path):
            os.remove(video_path)

@router.post("/api/verify-candidate/{request_id}")
async def upload_verification_video(
    request_id: str, 
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Endpoint for candidates to upload their 10s verification video.
    Returns immediately while processing happens in the background.
    """
    # 1. Check if join request exists
    request_data = _supabase_request("GET", f"join_requests?id=eq.{request_id}")
    if not request_data:
        raise HTTPException(status_code=404, detail="Join request not found")

    # 2. Save uploaded file to a temporary location
    temp_dir = tempfile.gettempdir()
    file_extension = os.path.splitext(file.filename)[1] or ".mp4"
    temp_video_path = os.path.join(temp_dir, f"verify_{uuid.uuid4()}{file_extension}")

    with open(temp_video_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 3. Update status to 'VERIFYING'
    _supabase_request("PATCH", f"join_requests?id=eq.{request_id}", {
        "liveness_status": "VERIFYING"
    })

    # 4. Start background processing
    background_tasks.add_task(process_video_and_update_db, request_id, temp_video_path)

    return {
        "status": "PROCESSING",
        "message": "Video uploaded successfully. Forensic analysis started.",
        "request_id": request_id
    }
