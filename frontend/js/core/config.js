/**
 * config.js — Frontend Configuration
 * 
 * ✅ Safe to change:  backendUrl (your Python server address)
 * ✅ Safe here:       LiveKit WSS URL (it's a public endpoint, not a secret)
 * ❌ NEVER put here:  LIVEKIT_API_KEY, LIVEKIT_API_SECRET, STRIPE_SECRET_KEY
 *
 * Usage:  Add <script src="config.js"></script> BEFORE any other scripts.
 *         All modules read from window.APP_CONFIG automatically.
 */

window.APP_CONFIG = {
    // Auto-detect: if on localhost use :8000, otherwise use current domain
    backendUrl: window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost' 
                ? 'http://127.0.0.1:8000' 
                : window.location.origin,

    // Supabase (public anon key — safe to be here)
    supabaseUrl:  'https://ljnclcivnbhjjofsfyzm.supabase.co',
    supabaseAnon: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxqbmNsY2l2bmJoampvZnNmeXptIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU1ODY5NjAsImV4cCI6MjA5MTE2Mjk2MH0.QveyJDvJuOeNPJHFwYZx-XD_UeJ5SqsDRdUPI61CbDk',

    // LiveKit public WSS URL (not a secret — just an address)
    livekitUrl: 'wss://youness-elysip4f.livekit.cloud',

    // STT default language
    sttLang: 'ar-SA',

    // Forensic NLP Engine (Research-Grade)
    nlpUrl: window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost' 
            ? 'http://127.0.0.1:8001' 
            : 'https://integra-nlp.vercel.app', 
};
