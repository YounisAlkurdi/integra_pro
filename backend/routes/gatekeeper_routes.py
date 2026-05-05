from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
import os
import uuid
import shutil
import tempfile
import asyncio
from ..engine.deepfake_Video.processor import FullDeepfakeDetector
from ..nodes import upload_to_supabase_storage
from ..services.database_service import db

router = APIRouter(tags=["Gatekeeper"])

# Initialize the detector once to save memory and time
print("🛡️ Gatekeeper: Initializing Deepfake Verification Engine...")
detector = FullDeepfakeDetector()

async def process_video_and_update_db(request_id: str, video_path: str):
    """
    Background task to process video and update Supabase asynchronously.
    """
    try:
        print(f"🔍 Gatekeeper: Analyzing video for request {request_id}...")
        
        # 1. Upload Video to Storage first (Now async)
        video_filename = os.path.basename(video_path)
        storage_path = f"{request_id}/{video_filename}"
        video_url = await upload_to_supabase_storage("verification_videos", storage_path, video_path)
        
        # 2. Run Analysis (Heavy CPU task, run in thread)
        try:
            results = await asyncio.to_thread(detector.analyze, video_path)
        except Exception as e:
            results = {"error": "SYSTEM_OFFLINE", "message": str(e)}
        
        # 3. Determine Database Status and Error Details
        verdict = results.get("verdict", "UNCERTAIN")
        score = results.get("final_score", 0.0)
        report_b64 = results.get("report_image", "") 
        
        # 4. Handle Specific Failure Scenarios
        db_status = "FAILED" # Default to failed if uncertain and no specific error
        error_msg = None

        if verdict == "REAL":
            db_status = "VERIFIED"
        elif verdict == "FAKE":
            db_status = "FAILED"
        
        # Check for technical errors (No face, lighting, etc.)
        if "error" in results or verdict == "UNCERTAIN":
            db_status = "ERROR"
            # Map common error strings to user-friendly codes
            raw_err = str(results.get("error", "UNCERTAIN")).upper()
            if "NO FACE" in raw_err or "NOT FOUND" in raw_err:
                error_msg = "NO_FACE_DETECTED"
            elif "LIGHTING" in raw_err or "DARK" in raw_err:
                error_msg = "POOR_LIGHTING"
            elif "OFFLINE" in raw_err or "CONNECTION" in raw_err:
                error_msg = "SYSTEM_OFFLINE"
            else:
                error_msg = raw_err or "TECHNICAL_TIMEOUT"

        # 5. Update Supabase (Async)
        update_data = {
            "liveness_status": db_status,
            "deepfake_score": float(score),
            "forensic_report_url": f"data:image/png;base64,{report_b64}" if report_b64 else None,
            "verification_video_path": video_url,
            "error_details": error_msg
        }
        
        print(f"✅ Gatekeeper: Analysis complete. Result: {db_status} | Reason: {error_msg or 'N/A'}")
        await db.client.table("join_requests").update(update_data).eq("id", request_id).execute()

    except Exception as e:
        print(f"❌ Gatekeeper Error: {str(e)}")
        try:
            await db.client.table("join_requests").update({"liveness_status": "ERROR"}).eq("id", request_id).execute()
        except: pass
    finally:
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
    try:
        request_resp = await db.client.table("join_requests").select("*").eq("id", request_id).execute()
        if not request_resp.data:
            raise HTTPException(status_code=404, detail="Join request not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connectivity error: {str(e)}")

    # 2. Save uploaded file to a temporary location
    temp_dir = tempfile.gettempdir()
    file_extension = os.path.splitext(file.filename)[1] or ".mp4"
    temp_video_path = os.path.join(temp_dir, f"verify_{uuid.uuid4()}{file_extension}")

    with open(temp_video_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 3. Update status to 'VERIFYING'
    await db.client.table("join_requests").update({"liveness_status": "VERIFYING"}).eq("id", request_id).execute()

    # 4. Start background processing
    background_tasks.add_task(process_video_and_update_db, request_id, temp_video_path)

    return {
        "status": "PROCESSING",
        "message": "Video uploaded successfully. Forensic analysis started.",
        "request_id": request_id
    }
