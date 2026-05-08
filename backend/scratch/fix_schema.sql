-- Fix for missing forensic columns in interview_reports
ALTER TABLE public.interview_reports 
ADD COLUMN IF NOT EXISTS focus_score_avg FLOAT8,
ADD COLUMN IF NOT EXISTS gaze_stability FLOAT8,
ADD COLUMN IF NOT EXISTS integrity_risk_score FLOAT8,
ADD COLUMN IF NOT EXISTS threat_level_final TEXT,
ADD COLUMN IF NOT EXISTS ai_generated_prob INTEGER,
ADD COLUMN IF NOT EXISTS forensic_data_series JSONB,
ADD COLUMN IF NOT EXISTS last_telemetry_sync TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS telemetry_metadata JSONB,
ADD COLUMN IF NOT EXISTS overall_forensic_score FLOAT8;

-- Ensure room_id has a unique constraint if we use it for upsert
-- Check if constraint exists first or just use a generic name
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'interview_reports_room_id_key') THEN
        ALTER TABLE public.interview_reports ADD CONSTRAINT interview_reports_room_id_key UNIQUE (room_id);
    END IF;
END $$;
