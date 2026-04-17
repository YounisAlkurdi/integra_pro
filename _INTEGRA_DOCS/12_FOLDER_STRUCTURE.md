# 📁 2026 SaaS Modular Architecture — Project Structure

## The SaaS Vision
Integra has been evolved from a flat prototype into a scalable, modular SaaS architecture. This structure supports multi-tenancy, high performance, and rapid deployment.

```
c:\tist_integra\
│
├── 📂 backend/                      ← Global Backend Container
│   ├── main.py                      ← Unified FastAPI Entry Point
│   ├── 📂 core/                     ← SaaS Business Logic
│   │   ├── auth.py                  ← Secure JWT & Identity
│   │   ├── cache.py                 ← Hybrid Memory/Redis Cache
│   │   ├── rate_limit.py            ← SaaS Rate Limiting
│   │   └── supabase_client.py       ← Async Supabase Bridge
│   │
│   ├── 📂 routes/                   ← API Endpoint Definitions
│   │   ├── agent_routes.py          ← Neural Agent endpoints
│   │   ├── livekit_routes.py        ← WebRTC Session Control
│   │   ├── nodes.py                 ← Interview Node logic
│   │   ├── payments.py              ← Stripe SaaS Billing
│   │   └── system.py                ← Telemetry & Health
│   │
│   └── 📂 services/                 ← Internal Logic Providers
│       ├── agent_tools.py           ← LangChain Agent Toolset
│       ├── audit_logger.py          ← Security Event Logging
│       ├── integra_mcp.py           ← FastMCP Tools Provider
│       ├── mailer.py                ← SMTP/Communication service
│       └── api_bridge.py            ← External Matrix Connector
│
├── 📂 frontend/                     ← Production Web Interface
│   ├── 📂 pages/                    ← High-performance HTML
│   │   ├── dashboard.html
│   │   ├── integra-session.html
│   │   └── ...
│   ├── 📂 js/
│   │   ├── 📂 core/                 ← Global State & Clients
│   │   ├── 📂 pages/                ← Page Controllers
│   │   └── 📂 utils/                ← UI/API helpers
│   └── 📂 css/                      ← Premium Design System
│
├── 📂 _INTEGRA_DOCS/                ← System Documentation
├── .env                             ← Secrets
└── requirements.txt                 ← Dependencies
```

## Migration Status
- [x] Backend Restructuring (Modular routes & services)
- [x] Hybrid Caching (Redis-ready)
- [x] SaaS Rate Limiting (Applied to all endpoints)
- [x] Centralized Audit Logging (To Supabase)
- [x] Documentation Sync

## Design Principles
1. **Separation of Concerns**: UI, API, and Core Logic are isolated.
2. **Statelessness**: The backend remains stateless for horizontal scaling.
3. **Agentic Autonomy**: The engine is designed to think before calling tools.
4. **Performance First**: LRU Caching implemented for frequent lookups.
