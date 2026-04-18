import os
import shutil
import sys

def move_file(src, dst):
    if os.path.exists(src):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.exists(dst):
            print(f"Warning: {dst} already exists. Overwriting.")
            os.remove(dst)
        shutil.move(src, dst)
        print(f"Moved: {src} -> {dst}")
    else:
        print(f"Skipped: {src} not found.")

def move_dir(src, dst):
    if os.path.exists(src):
        if os.path.exists(dst):
            print(f"Warning: {dst} already exists. Removing old directory.")
            shutil.rmtree(dst)
        shutil.move(src, dst)
        print(f"Moved Dir: {src} -> {dst}")
    else:
        print(f"Skipped: {src} not found.")

def main():
    root = "C:\\tist_integra"
    
    # Backend files
    move_file(os.path.join(root, "agent_routes.py"), os.path.join(root, "backend", "agent_routes.py"))
    move_file(os.path.join(root, "agent_tools.py"), os.path.join(root, "backend", "agent_tools.py"))
    move_file(os.path.join(root, "api_bridge.py"), os.path.join(root, "backend", "api_bridge.py"))
    move_file(os.path.join(root, "integra_mcp.py"), os.path.join(root, "backend", "integra_mcp.py"))
    move_file(os.path.join(root, "nodes.py"), os.path.join(root, "backend", "nodes.py"))
    
    # LLM directory -> backend/llm
    move_dir(os.path.join(root, "llm"), os.path.join(root, "backend", "llm"))
    
    # Frontend files
    move_file(os.path.join(root, "chat-widget.js"), os.path.join(root, "frontend", "js", "components", "chat-widget.js"))
    move_file(os.path.join(root, "llm-config.html"), os.path.join(root, "frontend", "pages", "llm-config.html"))
    move_file(os.path.join(root, "llm-config.js"), os.path.join(root, "frontend", "js", "pages", "llm-config.js"))
    move_file(os.path.join(root, "models.config.js"), os.path.join(root, "frontend", "js", "core", "models.config.js"))

    print("\n✅ File organization complete!")

if __name__ == "__main__":
    main()
