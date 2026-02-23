import base64
from typing import Optional, Tuple

def encode_cursor(val: str, id_str: str) -> str:
    """
    Encodes a value and a UUID string into an opaque Base64 cursor.
    """
    raw_cursor = f"{val}:{id_str}"
    return base64.b64encode(raw_cursor.encode()).decode()

def decode_cursor(cursor: str) -> Optional[Tuple[str, str]]:
    """
    Decodes an opaque Base64 cursor into a value and a UUID string.
    Returns None if the cursor is malformed.
    """
    try:
        decoded = base64.b64decode(cursor.encode()).decode()
        if ":" not in decoded:
            return None
        val, id_str = decoded.rsplit(":", 1)
        return val, id_str
    except (ValueError, UnicodeDecodeError, Exception):
        return None
