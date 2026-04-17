# 🔌 MCP Server — خطة متكاملة للمشروع

## الخطوة 1 — تحليل فولدرات المشروع

شغّل هذا في root المشروع عشان تشوف الـ structure:

```bash
find . -type f -name "*.py" | head -50
find . -type f -name "*.json" | grep -E "(package|config|mcp)"
find . -type f -name "*.env*"
find . -type f -name "docker-compose*"
```

ابحث عن:
- `requirements.txt` أو `pyproject.toml` → شوف الـ dependencies
- `.env` → شوف شو API keys موجودة
- `docker-compose.yml` → شوف شو services مربوطة

---

## الخطوة 2 — كشف الـ MCPs الحالية في المشروع

### ابحث عن MCP config في Claude Desktop (لو موجود):
```bash
# Mac
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Windows
cat %APPDATA%\Claude\claude_desktop_config.json
```

### ابحث داخل كود المشروع:
```bash
grep -r "mcp" . --include="*.py" -l
grep -r "mcp" . --include="*.json" -l
grep -r "mcp_servers" . --include="*.py"
grep -r "fastapi-mcp\|mcp\[" requirements.txt
```

---

## الخطوة 3 — جرد كل الـ Services في المشروع

بناءً على تحليل الفولدرات، حدد:

| Service | موجود؟ | MCP رسمي؟ | رابط |
|---------|--------|-----------|------|
| Supabase | ☐ | ✅ | `@supabase/mcp-server-supabase` |
| Stripe | ☐ | ✅ | `@stripe/agent-toolkit` |
| GitHub | ☐ | ✅ | `@modelcontextprotocol/server-github` |
| Gmail | ☐ | ✅ | `https://gmail.mcp.claude.com/mcp` |
| Google Calendar | ☐ | ✅ | `https://gcal.mcp.claude.com/mcp` |
| Custom DB | ☐ | ❌ | تبني بنفسك |
| Custom Logic | ☐ | ❌ | تبني بنفسك |

---

## الخطوة 4 — تحديد شو تبني بنفسك

أي logic خاص بمشروعك = تبني MCP Server خاص، مثلاً في **Integra**:

```
integra-mcp-server/
├── tools/
│   ├── interview_tools.py      # create_interview, get_results
│   ├── fraud_tools.py          # get_fraud_score, flag_candidate
│   ├── candidate_tools.py      # list_candidates, get_profile
│   └── report_tools.py         # generate_pdf_report
├── server.py                   # FastAPI + MCP setup
└── requirements.txt
```

---

## الخطوة 5 — Architecture المقترحة

```
┌─────────────────────────────────────┐
│          Frontend / Bot             │
└────────────────┬────────────────────┘
                 │
┌────────────────▼────────────────────┐
│           AI Agent (FastAPI)        │
│                                     │
│  يربط الـ MCPs التالية:             │
│                                     │
│  ┌──────────┐  ┌──────────────────┐ │
│  │ Supabase │  │  Stripe MCP      │ │
│  │   MCP    │  │                  │ │
│  └──────────┘  └──────────────────┘ │
│                                     │
│  ┌──────────────────────────────┐   │
│  │     Custom MCP Server        │   │
│  │  (logic خاص بالمشروع)       │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
```

---

## الخطوة 6 — Starter Code للـ Custom MCP Server

```python
# server.py
from mcp.server.fastmcp import FastMCP
from supabase import create_client
import os

mcp = FastMCP("integra-mcp")
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

@mcp.tool()
def get_interview_results(interview_id: str) -> dict:
    """جيب نتائج انترفيو معين"""
    result = supabase.table("interviews").select("*").eq("id", interview_id).execute()
    return result.data

@mcp.tool()
def flag_candidate(candidate_id: str, reason: str) -> dict:
    """فلاغ مرشح بسبب fraud"""
    result = supabase.table("candidates").update({"flagged": True, "flag_reason": reason}).eq("id", candidate_id).execute()
    return result.data

@mcp.tool()
def list_active_interviews(company_id: str, limit: int = 10) -> list:
    """جيب الانترفيوز الشغّالة لشركة معينة"""
    result = supabase.table("interviews").select("*").eq("company_id", company_id).eq("status", "active").limit(limit).execute()
    return result.data

if __name__ == "__main__":
    # لوكال
    mcp.run(transport="stdio")

    # للسيرفر: غيّر لـ
    # mcp.run(transport="streamable-http", host="0.0.0.0", port=8001)
```

---

## الخطوة 7 — ربط الـ MCPs بالـ Agent

```python
# agent.py
import anthropic

client = anthropic.Anthropic()

response = client.beta.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1000,
    mcp_servers=[
        {
            "type": "url",
            "url": "https://your-integra-mcp.onrender.com/mcp",
            "name": "integra-mcp"
        },
        {
            "type": "url", 
            "url": "https://mcp.supabase.com/sse",
            "name": "supabase-mcp"
        }
    ],
    messages=[{"role": "user", "content": "جيب آخر 5 انترفيوز وافحص وجود fraud"}]
)
```

---

## الخطوة 8 — Deployment Checklist

```
☐ بنيت الـ Custom MCP Server
☐ تيستته لوكال بـ stdio
☐ غيّرت الـ transport لـ streamable-http
☐ رفعته على Render / Railway
☐ حطيت الـ ENV variables على السيرفر
☐ تيستت الـ URL يرد صح
☐ ربطت الـ URL بالـ Agent
☐ اختبرت الـ Agent end-to-end
```

---

## ملاحظات مهمة

- **MCP رسمي موجود؟** استخدمه، لا تعيد الاختراع
- **Logic خاص بمشروعك؟** ابني custom MCP
- **سيرفر واحد يكفي** يجمع كل الـ custom tools
- **الـ ENV variables** ما تحطها في الكود أبداً، بس في `.env`
