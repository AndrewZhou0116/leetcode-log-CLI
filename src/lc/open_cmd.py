from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from urllib.parse import quote

from .db import connect, get_meta


def _is_wsl() -> bool:
    try:
        with open("/proc/version", "r", encoding="utf-8") as f:
            return "microsoft" in f.read().lower()
    except Exception:
        return False


def _open_url(url: str) -> None:
    # 1) WSL: prefer wslview, else Windows start
    if _is_wsl():
        if shutil.which("wslview"):
            subprocess.run(["wslview", url], check=False)
            return
        if shutil.which("cmd.exe"):
            # cmd.exe /c start "" "<url>"
            subprocess.run(["cmd.exe", "/c", "start", "", url], check=False)
            return

    # 2) Linux desktop: xdg-open
    if shutil.which("xdg-open"):
        subprocess.run(["xdg-open", url], check=False)
        return

    # 3) last resort: print only
    print(url)


def _current_new_lc_num(conn) -> int:
    cursor_po = int(get_meta(conn, "cursor_plan_order", "1") or "1")
    row = conn.execute(
        """
        SELECT p.lc_num
        FROM problems p
        LEFT JOIN reviews r ON r.lc_num=p.lc_num
        WHERE p.plan_order >= ?
          AND r.lc_num IS NULL
        ORDER BY p.plan_order ASC
        LIMIT 1;
        """,
        (cursor_po,),
    ).fetchone()
    if not row:
        raise RuntimeError("No NEW problem found (did you import plan.txt?)")
    return int(row["lc_num"])


def open_problem(db_path: Path, lc_num: int | None = None) -> str:
    conn = connect(db_path)
    try:
        base = get_meta(conn, "leetcode_base_url", "https://leetcode.com") or "https://leetcode.com"
        n = lc_num if lc_num is not None else _current_new_lc_num(conn)
        # LeetCode 没有稳定的 “按题号直达 slug” 的 URL，所以用搜索页最稳
        url = f"{base.rstrip('/')}/problemset/?search={quote(str(n))}"
        _open_url(url)
        return url
    finally:
        conn.close()

