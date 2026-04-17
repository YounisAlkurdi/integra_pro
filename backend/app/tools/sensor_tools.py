from langchain_core.tools import tool
import json
import os
import httpx

@tool
def analyze_web_link(url: str) -> str:
    """
    THE WEB SENSOR: Fetches a URL and returns a summary. Use for dealing with links output.
    """
    try:
        res = httpx.get(url, timeout=10.0, follow_redirects=True)
        html = res.text
        
        # Simple extraction logic (avoiding heavy deps if possible, or use them if available)
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            title = soup.title.string.strip() if soup.title else "Unknown Title"
            paragraphs = [p.get_text().strip() for p in soup.find_all('p') if len(p.get_text().strip()) > 50]
            summary = " ".join(paragraphs[:2]) if paragraphs else "No content summary found."
        except ImportError:
            import re
            m = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
            title = m.group(1) if m else "Unknown Title"
            summary = html[:300].strip() + "..."
            
        summary = summary[:300] + "..." if len(summary) > 300 else summary
        
        payload = {"type": "link", "url": url, "title": title, "summary": summary}
        return f"[INTEGRA_UI_CARD: {json.dumps(payload)}]"
    except Exception as e:
        return f"Web Sensor Failure: {str(e)}"

@tool
def analyze_image(image_path_or_url: str) -> str:
    """
    THE VISION SENSOR: Downloads an image, extracts tech data, and returns path for display.
    """
    try:
        file_path = image_path_or_url
        if image_path_or_url.startswith("http"):
            temp_dir = os.path.abspath(os.path.join(os.getcwd(), 'frontend', 'static', 'temp_images'))
            os.makedirs(temp_dir, exist_ok=True)
            filename = image_path_or_url.split("/")[-1] or "downloaded_img.jpg"
            if "?" in filename: filename = filename.split("?")[0]
            file_path = os.path.join(temp_dir, filename)
            
            res = httpx.get(image_path_or_url, follow_redirects=True)
            with open(file_path, 'wb') as f:
                f.write(res.content)
            serve_path = f"/static/temp_images/{filename}"
        else:
            serve_path = image_path_or_url
            
        try:
            from PIL import Image
            img = Image.open(file_path)
            tech_data = {"format": img.format, "size": f"{img.size[0]}x{img.size[1]}", "mode": img.mode}
        except Exception:
            tech_data = {"status": "Metadata unavailable"}

        payload = {"type": "image", "path": serve_path, "tech_data": tech_data}
        return f"[INTEGRA_UI_CARD: {json.dumps(payload)}]"
    except Exception as e:
        return f"Vision Sensor Failure: {str(e)}"

@tool
def analyze_local_file(filepath: str) -> str:
    """
    THE DOCUMENT SENSOR: Reads a local file up to 500KB. Fails securely if reading sensitive env files.
    """
    try:
        # Secure block
        name = filepath.lower()
        if any(x in name for x in [".env", "secret", ".pem", "key"]):
            return "SECURITY ERROR: Prevented neural read on highly sensitive file."
            
        if not os.path.exists(filepath):
            return f"Document Sensor Error: {filepath} not found."
            
        sz = os.path.getsize(filepath)
        if sz > 500 * 1024:
            return "Document Sensor Error: File exceeds 500KB strict limit."
            
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        payload = {
            "type": "file",
            "filepath": filepath,
            "content": content
        }
        return f"[INTEGRA_UI_CARD: {json.dumps(filepath)}]" # Using filepath as reference
    except Exception as e:
        return f"Document Sensor Failure: {str(e)}"

SENSOR_TOOLS = [
    analyze_web_link,
    analyze_image,
    analyze_local_file
]
