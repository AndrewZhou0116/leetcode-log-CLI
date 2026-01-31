from __future__ import annotations

from pathlib import Path

from .db import connect, tx, get_meta, set_meta

ALLOWED = {
    "new_quota": "int>=0",
    "review_per_new": "int>=0",
    "window_size": "int>=1",
    "interleave_ratio": "float(0..1)",
    "leetcode_base_url": "str",
}

def _validate(key: str, value: str) -> str:
    if key not in ALLOWED:
        raise ValueError(f"Unknown key: {key}. Allowed: {', '.join(ALLOWED.keys())}")

    rule = ALLOWED[key]
    if rule.startswith("int"):
        v = int(value)
        if ">=1" in rule and v < 1:
            raise ValueError(f"{key} must be >= 1")
        if ">=0" in rule and v < 0:
            raise ValueError(f"{key} must be >= 0")
        return str(v)

    if rule.startswith("float"):
        v = float(value)
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"{key} must be between 0 and 1")
        return str(v)

    return value

def config_get(db_path: Path, key: str) -> str | None:
    conn = connect(db_path)
    try:
        return get_meta(conn, key, None)
    finally:
        conn.close()

def config_set(db_path: Path, key: str, value: str) -> None:
    val = _validate(key, value)
    conn = connect(db_path)
    with tx(conn):
        set_meta(conn, key, val)
    conn.close()

