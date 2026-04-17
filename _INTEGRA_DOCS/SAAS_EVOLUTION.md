# 🚀 Integra SaaS Evolution Report

## 🔍 Codebase Analysis

### 1. Backend Architecture (Current)
*   **Entry Point**: `main.py` is the monolithic hub.
*   **Database**: Mix of `urllib.request` (sync) and `httpx` (async).
*   **Auth**: Hardened with caching, but still has some legacy patterns.
*   **Agent**: Uses `LangChain` with persistent memory in `agent_memories` table.
*   **Scaling Risk**: Synchronous DB calls in `nodes.py` and `integra_mcp.py` will cause performance bottlenecks with 100+ users.

### 2. Frontend Architecture (Current)
*   **Structure**: All files in root.
*   **JS/HTML**: Tight coupling. Hardcoded paths.
*   **Maintenance**: Hard to manage as the project grows.

---

## 🛠️ SaaS Optimization Plan

### Phase A: Performance & Scaling (High Priority)
1.  **Async Refactor**: Convert `nodes.py` to use `SupabaseClient.request` (async) instead of `urllib`.
2.  **Connection Pooling**: Update `SupabaseClient` to use a persistent `httpx.AsyncClient`.
3.  **Caching Expansion**: Implement caching for `get_node_stats` and `list_active_streams` (short TTL).

### Phase B: Security Hardening
1.  **Tool Lockdown**: Restrict `analyze_local_file` to specific non-sensitive directories.
2.  **User Scoping**: Verify all database queries in `nodes.py` and `integra_mcp.py` strictly enforce `user_id` filtering.
3.  **JWT Validation**: Transition to fully dynamic JWKS validation without requiring a local PEM file.

### Phase C: Modularization (Folder Structure)
1.  **Backend Migration**: Move Python files to `backend/`.
2.  **Frontend Migration**: Move HTML/JS/CSS to `frontend/`.
3.  **Asset Consolidation**: Move images/video/design to `assets/`.

---

## 📈 Next Steps (Immediate)
1.  **Refactor `nodes.py`**: Migrate to async `SupabaseClient`.
2.  **Update `SupabaseClient`**: Implement persistent client session.
3.  **Restructure Core**: Begin moving backend files.

> [!IMPORTANT]
> Since the terminal environment is experiencing path issues for `powershell`, I will perform reorganization via direct file creation and invite the user to cleanup the old files once verified.
