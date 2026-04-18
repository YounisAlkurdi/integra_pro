/**
 * Supabase Client Configuration
 * Uses centralized INTEGRA_SETTINGS for easier management.
 * Exports to window.supabase for global access in non-module scripts.
 */
import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js/+esm';

const SUPABASE_URL = window.INTEGRA_SETTINGS.SUPABASE_URL;
const SUPABASE_ANON_KEY = window.INTEGRA_SETTINGS.SUPABASE_ANON_KEY;

// Create and expose globally
window.supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// Export for module-based scripts
export const supabase = window.supabase;
