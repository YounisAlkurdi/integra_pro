-- ==========================================
-- INTEGRA PRO | Full Database Schema v5.2
-- Forensic Intelligence & RTC Infrastructure
-- ==========================================

-- 1. NODES (Interview Rooms)
CREATE TABLE IF NOT EXISTS public.nodes (
    room_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id), -- The HR / Owner
    candidate_name TEXT NOT NULL,
    candidate_email TEXT,
    position TEXT NOT NULL,
    questions JSONB,
    scheduled_at TEXT NOT NULL,
    status TEXT DEFAULT 'PENDING',
    max_duration_mins INTEGER DEFAULT 10,
    max_participants INTEGER DEFAULT 2,
    is_deleted BOOLEAN DEFAULT false,
    started_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 2. JOIN REQUESTS (Candidates & Gatekeeper Logic)
CREATE TABLE IF NOT EXISTS public.join_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    room_id UUID REFERENCES public.nodes(room_id) ON DELETE CASCADE,
    participant_name TEXT NOT NULL,
    status TEXT DEFAULT 'PENDING', -- PENDING, ACCEPTED, REJECTED
    
    -- Deepfake & Liveness Columns (New Integration)
    liveness_status TEXT DEFAULT 'NOT_STARTED', -- NOT_STARTED, VERIFYING, VERIFIED, FAILED
    deepfake_score FLOAT8 DEFAULT 0.0,
    forensic_report_url TEXT, -- Base64 or Storage URL for the ViT plot
    verification_video_path TEXT,
    
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 3. INTERVIEW REPORTS (Post-Analysis Results)
CREATE TABLE IF NOT EXISTS public.interview_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    room_id TEXT NOT NULL,
    user_id UUID REFERENCES auth.users(id),
    candidate_name TEXT,
    score INTEGER,
    ai_summary TEXT,
    strengths JSONB,
    weaknesses JSONB,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now())
);

-- 4. CHAT LOGS (STT Transcripts)
CREATE TABLE IF NOT EXISTS public.chat_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    room_id TEXT NOT NULL,
    user_id UUID REFERENCES auth.users(id),
    sender TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 5. SUBSCRIPTIONS (Billing Control)
CREATE TABLE IF NOT EXISTS public.subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    plan_id TEXT NOT NULL,
    status TEXT NOT NULL,
    interviews_limit INTEGER DEFAULT 10,
    interviews_used INTEGER DEFAULT 0,
    max_duration_mins INTEGER DEFAULT 10,
    max_participants INTEGER DEFAULT 2,
    stripe_customer_id TEXT,
    next_billing_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 6. USER SETTINGS (LLM & Provider Config)
CREATE TABLE IF NOT EXISTS public.user_settings (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id),
    llm_api_key TEXT,
    llm_provider TEXT DEFAULT 'openai',
    llm_model TEXT DEFAULT 'gpt-4o',
    system_prompt_override TEXT,
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 7. AUDIT LOGS (Security Monitoring)
CREATE TABLE IF NOT EXISTS public.audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    action TEXT NOT NULL,
    target_resource TEXT NOT NULL,
    resource_id TEXT,
    details JSONB DEFAULT '{}'::jsonb,
    status TEXT DEFAULT 'SUCCESS',
    severity TEXT DEFAULT 'INFO',
    ip_address TEXT DEFAULT 'unknown',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 8. ROOM INVITES (Secure Links)
CREATE TABLE IF NOT EXISTS public.room_invites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    room_id TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'CANDIDATE',
    status TEXT DEFAULT 'PENDING',
    used BOOLEAN DEFAULT false,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ==========================================
-- INDEXING FOR PERFORMANCE
-- ==========================================
CREATE INDEX IF NOT EXISTS idx_nodes_user_id ON public.nodes(user_id);
CREATE INDEX IF NOT EXISTS idx_join_requests_room_id ON public.join_requests(room_id);
CREATE INDEX IF NOT EXISTS idx_chat_logs_room_id ON public.chat_logs(room_id);
