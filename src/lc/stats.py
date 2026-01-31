from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from .db import connect, get_meta


@dataclass(frozen=True)
class Stats:
    cursor_plan_order: int
    cursor_lc_num: int | None
    cursor_title: str | None

    problems_total: int
    reviews_total: int
    active_total: int
    due_total: int
    retired_total: int

    logs_today: int
    logs_7d: int


def compute_stats(db_path: Path) -> Stats:
    now = int(time.time())
    today_start = now - (now % 86400)  # naive local/UTC boundary ok for MVP
    seven_days_ago = now - 7 * 86400

    conn = connect(db_path)

    cursor_po = int(get_meta(conn, "cursor_plan_order", "1") or "1")

    cur = conn.execute(
        "SELECT lc_num, title FROM problems WHERE plan_order=?;",
        (cursor_po,),
    ).fetchone()
    cursor_lc = int(cur["lc_num"]) if cur else None
    cursor_title = str(cur["title"]) if cur else None

    problems_total = conn.execute("SELECT COUNT(*) AS c FROM problems;").fetchone()["c"]
    reviews_total = conn.execute("SELECT COUNT(*) AS c FROM reviews;").fetchone()["c"]
    active_total = conn.execute(
        "SELECT COUNT(*) AS c FROM reviews WHERE status='active';"
    ).fetchone()["c"]
    due_total = conn.execute(
        "SELECT COUNT(*) AS c FROM reviews WHERE status='active' AND due_at <= ?;",
        (now,),
    ).fetchone()["c"]
    retired_total = conn.execute(
        "SELECT COUNT(*) AS c FROM reviews WHERE status='retired';"
    ).fetchone()["c"]

    logs_today = conn.execute(
        "SELECT COUNT(*) AS c FROM review_logs WHERE reviewed_at >= ? AND grade != 'seed';",
        (today_start,),
    ).fetchone()["c"]
    logs_7d = conn.execute(
        "SELECT COUNT(*) AS c FROM review_logs WHERE reviewed_at >= ? AND grade != 'seed';",
        (seven_days_ago,),
    ).fetchone()["c"]

    conn.close()

    return Stats(
        cursor_plan_order=cursor_po,
        cursor_lc_num=cursor_lc,
        cursor_title=cursor_title,
        problems_total=int(problems_total),
        reviews_total=int(reviews_total),
        active_total=int(active_total),
        due_total=int(due_total),
        retired_total=int(retired_total),
        logs_today=int(logs_today),
        logs_7d=int(logs_7d),
    )

