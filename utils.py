import json
from datetime import datetime

def dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)

def loads(s: str):
    return json.loads(s)

def iso(dt) -> str:
    if isinstance(dt, str):
        return dt
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt)
