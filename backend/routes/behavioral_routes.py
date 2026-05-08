from fastapi import APIRouter, WebSocket, WebSocketDisconnect

try:
    from tracker import BehavioralTracker
except ImportError:
    from ..tracker import BehavioralTracker
import asyncio
import cv2
import numpy as np
import json

from ..auth import verify_token
from ..services.session_manager import session_manager
import jwt

router = APIRouter(tags=["Behavioral Analysis"])

# Dictionary to hold per-room trackers (to avoid global state mixing)
# { room_id: BehavioralTracker }
room_trackers = {}

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):  return int(obj)
        if isinstance(obj, np.floating): return float(obj)
        if isinstance(obj, np.ndarray):  return obj.tolist()
        if isinstance(obj, np.bool_):    return bool(obj)
        return super().default(obj)

from ..auth import verify_token
import jwt

@router.websocket("/ws/behavioral/{room_id}")
@router.websocket("/ws/behavioral")
async def behavioral_websocket(websocket: WebSocket, room_id: str = None, token: str = None):
    """
    WebSocket endpoint for real-time gaze and behavioral tracking.
    Uses room_id to isolate session data and RAM buffering.
    """
    # If room_id/token are not in path, check query parameters
    if room_id is None:
        room_id = websocket.query_params.get("room_id")
    if token is None:
        token = websocket.query_params.get("token")

    if not token:
        await websocket.close(code=4001)
        return

    # Verify Token
    user = await verify_token(token)
    if not user:
        print(f"📡 Behavioral WS: Auth Failed for room {room_id}")
        await websocket.close(code=4002)
        return

    # Strict Validation: room_id is MANDATORY for forensic tracking
    if not room_id:
        print("📡 Behavioral WS: Connection rejected - missing room_id")
        await websocket.close(code=4003)
        return


    # Ensure sync worker is running
    await session_manager.start_sync_worker()

    # Initialize tracker for this room if not exists
    if room_id not in room_trackers:
        print(f"👁️ Initializing Tracker for Room: {room_id}")
        room_trackers[room_id] = BehavioralTracker()

    await websocket.accept()
    
    try:
        # Create session in manager
        user_id = user.get("sub")
        await session_manager.get_or_create_session(room_id, user_id=user_id)

        while True:
            try:
                message = await websocket.receive()
            except WebSocketDisconnect:
                print(f"📡 Behavioral WS: Client disconnected [Room {room_id}]")
                break
            except Exception as e:
                if "disconnect" in str(e).lower(): break
                raise e


            if "text" in message:
                data = json.loads(message["text"])
                if data.get("type") == "PING":
                    await websocket.send_text(json.dumps({"type": "PONG"}))
                continue

            raw = message.get("bytes")
            if not raw:
                continue

            # Process frame
            nparr = np.frombuffer(raw, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if frame is None:
                continue

            # Get the room's specific tracker
            tracker = room_trackers[room_id]

            # Heavy AI processing in a separate thread
            result = await asyncio.to_thread(tracker.analyze, frame)

            # 📊 Add to RAM-efficient Session Manager
            focus_score = result.get("metrics", {}).get("focus_score", 0)
            
            # Threat level is derived from suspicion duration and distraction status
            is_suspicious = result.get("status") == "SUSPICIOUS"
            threat = 0
            if is_suspicious:
                threat = 100 - focus_score # Higher distraction = higher threat
            elif result.get("status") == "DISTRACTED":
                threat = (100 - focus_score) * 0.5 # Lower threat for minor distractions

            telemetry_point = {
                "gaze_score": abs(result.get("gaze", {}).get("x", 0)), # Stability metric
                "focus_score": focus_score,
                "threat_level": threat,
                "ai_probability": result.get("ai_generated_prob", 0) # Placeholder for deepfake
            }
            await session_manager.add_telemetry(room_id, telemetry_point)

            # Send back to client for UI overlay
            await websocket.send_text(json.dumps(result, cls=NumpyEncoder))

    except Exception as e:
        print(f"📡 Behavioral WS Error [Room {room_id}]: {e}")
    finally:
        # 🔒 Final Sync and Cleanup
        # This block is GUARANTEED to run on disconnect
        await session_manager.close_session(room_id)
        if room_id in room_trackers:
            del room_trackers[room_id]
        
        try:
            await websocket.close()
        except Exception:
            pass
