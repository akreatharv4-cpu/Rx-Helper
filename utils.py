import json
from datetime import datetime
from typing import Any


def dumps(obj: Any) -> str:
    """
    Convert Python object to JSON string safely.
    Handles datetime automatically.
    """
    return json.dumps(obj, ensure_ascii=False, default=iso)


def loads(s: str) -> Any:
    """
    Convert JSON string back to Python object.
    """
    return json.loads(s)


def iso(dt: Any) -> str:
    """
    Convert datetime objects to ISO string.
    """
    if isinstance(dt, datetime):
        return dt.isoformat()

    if isinstance(dt, str):
        return dt

    return str(dt)
