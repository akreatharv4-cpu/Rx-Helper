import json
from datetime import datetime
from typing import Any


def iso(obj: Any) -> str:
    """
    Convert non-JSON types (like datetime) to string.
    """
    if isinstance(obj, datetime):
        return obj.isoformat()

    return str(obj)


def dumps(obj: Any) -> str:
    """
    Convert Python object to JSON string safely.
    Handles datetime automatically.
    """
    return json.dumps(
        obj,
        ensure_ascii=False,
        default=iso
    )


def loads(s: str) -> Any:
    """
    Convert JSON string back to Python object.
    """
    return json.loads(s)
