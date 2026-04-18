import os
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(dotenv_path=env_path)

def get_env_safe(key: str):
    """
    Secure Key Extraction & Sanitization.
    Extracts environment variables and removes problematic characters.
    """
    val = os.getenv(key)
    if not val:
        return ""
    return val.strip().replace('"', '').replace("'", "")
