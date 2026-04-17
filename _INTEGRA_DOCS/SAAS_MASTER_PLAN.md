# Integra SaaS Evolution & Modularization Plan

This document outlines the strategic roadmap to transform the current Integra prototype into a high-performance, scalable SaaS platform capable of handling 100+ active users with minimal latency and robust security.

## 1. Structural Reorganization (Architecture Cleanup)
Currently, the codebase has significant fragmentation between the root directory and the `frontend/backend` subdirectories.

### 1.1 Mandatory Moves (Based on _INTEGRA_DOCS/12_FOLDER_STRUCTURE.md)
| Asset Type | Current Location | Target Location |
| :--- | :--- | :--- |
| **HTML Pages** | Root (`/`) | `frontend/pages/` |
| **JS Logic** | Root (`/`) | `frontend/js/` |
| **CSS Styles** | Root (`/`) | `frontend/css/` |
| **Python Logic** | Root (`/`) | `backend/app/` |
| **Shared Assets** | `Images/`, `frames/` | `static/` |

### 1.2 Action Items
- [ ] Move all `.html` files to `frontend/pages/`.
- [ ] Move all `.js` files to `frontend/js/`.
- [ ] Move all `.css` files to `frontend/css/`.
- [ ] Move all `.py` files to `backend/app/`.
- [ ] Update `main.py` (entry point) to correctly import from the new modular locations.
- [ ] Update all `<script src="...">` and `<link href="...">` in HTML files.
- [ ] Update asset paths in `script.js` and `integra-session.js`.

---

## 2. Agent Intelligence & Memory Optimization
To reduce "neural saturation" and improve response speed for a SaaS environment.

### 2.1 "Neural Cache" Logic
- [ ] **Supabase Caching**: Implement a TTL-based in-memory cache for `user_settings` and `subscriptions` to reduce the number of direct Supabase hits per request.
- [ ] **Tool Optimization**: Shorten and clarify tool descriptions in `agent_tools.py` to reduce token consumption during tool selection.
- [ ] **Memory Summarization**: Instead of fetching the last 10 messages raw, implement a logic to "summarize" older history into a single context block if the conversation exceeds a threshold.

### 2.2 Advanced Agent Thinking
- [ ] **Proactive Matrix Discovery**: Agent should automatically check `get_external_matrix_nodes` on its first turn in a session to understand what tools it actually has available.
- [ ] **Error-Resilient Tooling**: Enhance the `matrix_gateway` to provide better debugging feedback to the agent when an API fails.

---

## 3. SaaS Scalability & Security (100+ Active Users)
### 3.1 Concurrency & Performance
- [ ] **Async Supabase Calls**: Ensure all Supabase interactions use `httpx` asynchronously (currently some might be synchronous via `nodes.py`).
- [ ] **FastAPI Background Tasks**: Offload non-blocking operations like sending invitations (`mailer.py`) and saving logs to `BackgroundTasks`.

### 3.2 Multi-Tenancy & Data Privacy
- [ ] **RLS Audit**: Verify that all Supabase RLS policies are strictly enforcing `user_id` checks.
- [ ] **Encryption**: Implement encryption for sensitive data like `llm_api_key` in the `user_settings` table (at rest).

---

## 4. Visual Excellence (Premium UX)
- [ ] **Dynamic Pricing UI**: Update `pricing.js` to fetch plans directly from the Supabase `pricing` table in `integra-vault`.
- [ ] **Zero-Latency Interactions**: Integrate the `FramePlayer` engine into the main dashboard for smoother transitions between UI states.
- [ ] **Chat Widget 2.0**: Enhance `chat-widget.js` to support streaming chunks and better rendering of vision/link cards.

## 5. Maintenance & Observability
- [ ] **Centralized Logging**: Consolidate `logs.py` to write both to Supabase and a local high-performance log file for debugging.
- [ ] **Sentry/Telemetry Integration**: Prepare hooks for error tracking and performance monitoring.
