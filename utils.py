import json
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID
from typing import Any


def iso(obj: Any) -> Any:
    """
    Convert non-JSON serializable objects into JSON-compatible values.
    """

    if isinstance(obj, datetime):
        return obj.isoformat()

    if isinstance(obj, date):
        return obj.isoformat()

    if isinstance(obj, Decimal):
        return float(obj)

    if isinstance(obj, UUID):
        return str(obj)

    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="ignore")

    return str(obj)


def dumps(obj: Any, pretty: bool = False) -> str:
    """
    Convert Python object to JSON string safely.

    Handles:
    - datetime
    - date
    - Decimal
    - UUID
    """

    return json.dumps(
        obj,
        ensure_ascii=False,
        default=iso,
        indent=2 if pretty else None
    )


def loads(s: str) -> Any:
    """
    Convert JSON string back to Python object safely.
    """

    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return None
