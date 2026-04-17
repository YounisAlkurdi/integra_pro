import os
import shutil

# Files to keep in root (Essential configuration)
KEEP = {
    ".env", ".gitignore", "vercel.json", "requirements.txt", 
    "mcp_config.json", "GMAIL_GUIDE.md", "cleanup_root.py",
    "README.md", "LICENSE"
}

# Directories to ignore
IGNORE_DIRS = {"backend", "frontend", "static", "Images", "_INTEGRA_DOCS", ".git", ".vscode", "llm", "awesome-claude-skills", "frames", "video"}

ARCHIVE = "_LEGACY_ARCHIVE"
if not os.path.exists(ARCHIVE):
    os.makedirs(ARCHIVE)

# Cleanup Root
for item in os.listdir("."):
    if os.path.isfile(item):
        if item in KEEP or item.startswith("."):
            continue
        
        print(f"Archiving: {item} -> {ARCHIVE}")
        try:
            shutil.move(item, os.path.join(ARCHIVE, item))
        except Exception as e:
            print(f"Error archiving {item}: {e}")

# Cleanup Backend Root (Sub-archive)
BACKEND_DIR = "backend"
BACKEND_ARCHIVE = os.path.join(BACKEND_DIR, "_LEGACY_ARCHIVE")
BACKEND_KEEP = {"__init__.py", "main.py", "requirements.txt"}

if os.path.exists(BACKEND_DIR):
    if not os.path.exists(BACKEND_ARCHIVE):
        os.makedirs(BACKEND_ARCHIVE)
        
    for item in os.listdir(BACKEND_DIR):
        item_path = os.path.join(BACKEND_DIR, item)
        if os.path.isfile(item_path):
            if item in BACKEND_KEEP or item.startswith("."):
                continue
            
            print(f"Archiving Backend: {item} -> {BACKEND_ARCHIVE}")
            try:
                shutil.move(item_path, os.path.join(BACKEND_ARCHIVE, item))
            except Exception as e:
                print(f"Error archiving backend file {item}: {e}")

print("\n--- CLEANUP COMPLETE ---")
print("All legacy files have been moved to _LEGACY_ARCHIVE.")
print("Run the server with: uvicorn backend.main:app --reload")
