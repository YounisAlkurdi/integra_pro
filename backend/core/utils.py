import os
from typing import Any, Optional

def get_env_safe(key: str, default: Any = None) -> Any:
    """Safely retrieve environment variables."""
    val = os.getenv(key)
    if val is None:
        if default is not None:
            return default
        return ""
    return val
