import os
from dotenv import load_dotenv

load_dotenv()

def get_env_safe(key: str):
    """
    Secure Key Extraction & Sanitization.
    Extracts environment variables and removes problematic characters.
    """
    val = os.getenv(key)
    if not val:
        return ""
    return val.strip().replace('"', '').replace("'", "")
