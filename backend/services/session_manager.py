import time
import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from backend.services.database_service import db
from backend.services.forensic_service import perform_forensic_analysis

class ForensicSessionManager:
    _instance: Optional['ForensicSessionManager'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ForensicSessionManager, cls).__new__(cls)
            cls._instance._init_manager()
        return cls._instance

    def _init_manager(self):
        # Memory-efficient session storage using running totals
        # { room_id: { "gaze": {"sum": 0, "count": 0, "min": 1, "max": 0}, ... } }
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.lock = asyncio.Lock()
        self._sync_task = None

    async def start_sync_worker(self):
        """Starts the background worker for periodic DB synchronization."""
        if self._sync_task is None:
            self._sync_task = asyncio.create_task(self._periodic_sync())
            print("🚀 Forensic Session Manager: Sync Worker Active.")

    async def _periodic_sync(self):
        """Background loop to sync data to Supabase every 60 seconds."""
        while True:
            await asyncio.sleep(60) # Increased to 60s for efficiency
            try:
                await self.sync_all_active_sessions()
            except Exception as e:
                print(f"⚠️ Session Manager Sync Error: {e}")

    async def get_or_create_session(self, room_id: str, user_id: str = None):
        async with self.lock:
            if room_id not in self.sessions:
                # Initialize running metrics
                metric_template = {"sum": 0.0, "count": 0, "min": 1.0, "max": 0.0}
                self.sessions[room_id] = {
                    "user_id": user_id,
                    "gaze": metric_template.copy(),
                    "focus": metric_template.copy(),
                    "threat": metric_template.copy(),
                    "ai_score": metric_template.copy(),
                    "timeline": [], # Store snapshots every few seconds for the chart
                    "start_time": time.time(),
                    "last_snapshot": time.time(),
                    "last_sync": time.time()
                }
                print(f"💠 Session Created: {room_id} for user {user_id}")
            return self.sessions[room_id]

    async def add_telemetry(self, room_id: str, data: Dict[str, Any]):
        """Updates cumulative telemetry metrics (Memory Efficient)."""
        session = await self.get_or_create_session(room_id)
        
        mapping = {
            "gaze_score": "gaze",
            "focus_score": "focus",
            "threat_level": "threat",
            "ai_probability": "ai_score"
        }

        for key, metric_name in mapping.items():
            if key in data:
                val = float(data[key])
                m = session[metric_name]
                m["sum"] += val
                m["count"] += 1
                m["min"] = min(m["min"], val)
                m["max"] = max(m["max"], val)

        # 🕒 Capture snapshot every 5 seconds for the forensic timeline chart
        now = time.time()
        if now - session["last_snapshot"] >= 5:
            summary = self.calculate_summary(room_id)
            snapshot = {
                "t": int(now - session["start_time"]),
                "focus": summary["focus_avg"],
                "threat": summary["threat_avg"]
            }
            session["timeline"].append(snapshot)
            session["last_snapshot"] = now
            
            # Keep timeline size reasonable (max 120 snapshots = 10 mins)
            if len(session["timeline"]) > 120:
                session["timeline"].pop(0)

    def calculate_summary(self, room_id: str) -> Dict[str, Any]:
        """Calculates averages from cumulative totals."""
        if room_id not in self.sessions:
            return {}
        
        s = self.sessions[room_id]
        
        def get_metric(m):
            avg = round(m["sum"] / m["count"], 2) if m["count"] > 0 else 0
            return avg, m["count"], m["min"], m["max"]
        
        focus_avg, count, f_min, f_max = get_metric(s["focus"])
        gaze_avg, _, _, _ = get_metric(s["gaze"])
        threat_avg, _, _, _ = get_metric(s["threat"])
        ai_avg, _, _, _ = get_metric(s["ai_score"])

        # Determine Threat Level Category
        threat_cat = "LOW"
        if threat_avg > 60: threat_cat = "HIGH"
        elif threat_avg > 25: threat_cat = "MEDIUM"
        
        return {
            "user_id": s.get("user_id"),
            "focus_avg": focus_avg,
            "gaze_stability": gaze_avg,
            "threat_avg": threat_avg,
            "threat_level": threat_cat,
            "ai_prob_avg": ai_avg,
            "data_points": count,
            "timeline": s["timeline"],
            "duration": time.time() - s["start_time"],
            "metadata": {
                "focus_range": [f_min, f_max],
                "points": count,
                "session_duration": round(time.time() - s["start_time"], 1)
            }
        }

    async def sync_all_active_sessions(self):
        """Syncs all active sessions to Supabase without closing them."""
        async with self.lock:
            rooms = list(self.sessions.keys())
            
        for room_id in rooms:
            await self.sync_session_to_db(room_id)

    async def sync_session_to_db(self, room_id: str):
        """Writes current session summary to the database."""
        summary = self.calculate_summary(room_id)
        if not summary or summary["data_points"] == 0:
            return

        # Supabase interview_reports schema alignment:
        # ai_generated_prob is an integer (0-100)
        ai_prob = int(summary["ai_prob_avg"] * 100) if summary["ai_prob_avg"] <= 1.0 else int(summary["ai_prob_avg"])
        
        # --- REAL FORENSIC LINGUISTIC ANALYSIS ---
        # 1. Fetch Transcripts from chat_logs
        chat_logs = await db.select("chat_logs", columns="message, role", filters={"room_id": str(room_id)})
        
        # Concatenate candidate messages
        candidate_text = " ".join([
            msg["message"] for msg in chat_logs 
            if msg.get("role") == "candidate" and msg.get("message")
        ])
        
        nlp_results = {
            "nlp_scores": {},
            "linguistic_consistency": 0,
            "syntax_variance": 0,
            "metadata_integrity": 99.0, # High by default for system integrity
            "analysis_status": "PENDING"
        }

        if candidate_text.strip():
            try:
                print(f"🧠 Forensic Engine: Analyzing {len(candidate_text)} chars for Room {room_id}")
                analysis = await perform_forensic_analysis(candidate_text)
                comp = analysis.get("component_scores", {})
                
                nlp_results.update({
                    "nlp_scores": comp,
                    "linguistic_consistency": float(comp.get("semantic", 0.8) * 100),
                    "syntax_variance": float(comp.get("syntactic", 0.7) * 100),
                    "analysis_status": "COMPLETED",
                    "transcript_text": candidate_text
                })
            except Exception as e:
                print(f"⚠️ Forensic Engine Error: {e}")

        # --- DATA ASSEMBLY ---
        data = {
            "room_id": str(room_id),
            "user_id": summary.get("user_id"),
            "focus_score_avg": float(summary["focus_avg"]),
            "gaze_stability": float(summary["gaze_stability"]),
            "integrity_risk_score": float(summary["threat_avg"]),
            "threat_level_final": summary["threat_level"],
            "ai_generated_prob": ai_prob,
            "forensic_data_series": summary["timeline"],
            "last_telemetry_sync": datetime.now().isoformat(),
            "telemetry_metadata": summary["metadata"],
            "overall_forensic_score": float(100 - summary["threat_avg"]),
            
            # NLP Fields
            "nlp_scores": nlp_results["nlp_scores"],
            "linguistic_consistency": nlp_results["linguistic_consistency"],
            "syntax_variance": nlp_results["syntax_variance"],
            "metadata_integrity": nlp_results["metadata_integrity"],
            "analysis_status": nlp_results["analysis_status"]
        }
        
        if "transcript_text" in nlp_results:
            data["transcript_text"] = nlp_results["transcript_text"]
        
        # Mandatory Upsert based on room_id constraint
        await db.upsert("interview_reports", data, on_conflict="room_id")

    async def close_session(self, room_id: str):
        """Final sync and cleanup of session data."""
        # Small sleep to allow final frames to hit add_telemetry
        await asyncio.sleep(0.5) 
        
        print(f"🔒 Finalizing Session: {room_id}")
        await self.sync_session_to_db(room_id)
        
        async with self.lock:
            if room_id in self.sessions:
                del self.sessions[room_id]
                print(f"🧹 Session memory cleared: {room_id}")

# Global Singleton Instance
session_manager = ForensicSessionManager()
