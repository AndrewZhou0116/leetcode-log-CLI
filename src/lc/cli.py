from pathlib import Path
import typer
from rich import print as rprint
from lc.db import DEFAULT_DB_PATH, init_db
from .importer import import_plan
from .show import load_show
from .done import apply_done
from .seed import cursor_set, mark_done_before

from datetime import datetime
from rich.table import Table
from rich.console import Console

from .history import fetch_history
from .stats import compute_stats

from .open_cmd import open_problem



app = typer.Typer(help="LeetCode SRS CLI (Plan+Cursor+SRS)")

@app.callback()
def root():
    """Command group for lc."""
    # 这里可以放全局选项（以后比如 --db-path）
    pass

@app.command()
def version():
    """Show version."""
    rprint("[bold green]lcsrs[/bold green] v0.1.0")

@app.command()
def init(db: Path = typer.Option(DEFAULT_DB_PATH, "--db", help="Path to sqlite db file")):
    """Initialize database schema and default meta."""
    path = init_db(db)
    rprint(f"[bold cyan]OK[/bold cyan] initialized db at: {path}")

@app.command("import")
def import_(plan: Path = typer.Argument(..., help="Path to plan.txt"),
            db: Path = typer.Option(DEFAULT_DB_PATH, "--db", help="Path to sqlite db file")):
    """Import plan.txt into problems table (authoritative plan_order)."""
    n, last_order = import_plan(db, plan)
    rprint(f"[bold cyan]OK[/bold cyan] imported {n} problems (last plan_order={last_order})")
@app.command()
def show(db: Path = typer.Option(DEFAULT_DB_PATH, "--db", help="Path to sqlite db file")):
    """Show today's NEW + REVIEW (cursor only affects NEW)."""
    new_items, review_items = load_show(db)

    rprint("[bold]NEW[/bold]")
    if not new_items:
        rprint("  (none)")
    else:
        for it in new_items:
            rprint(f"  {it.lc_num}  {it.title}")

    rprint("")
    rprint("[bold]REVIEW[/bold]")
    if not review_items:
        rprint("  (none)")
    else:
        for it in review_items:
            rprint(f"  {it.lc_num}  {it.title}")
@app.command()
def done(
    lc_num: int = typer.Argument(..., help="LeetCode problem number"),
    grade: str = typer.Argument("good", help="again|hard|good|easy"),
    note: str = typer.Option("", "--note", help="Optional note for this review log"),
    db: Path = typer.Option(DEFAULT_DB_PATH, "--db", help="Path to sqlite db file"),
):
    """Mark a problem done and schedule next review (SRS)."""
    prev_due, next_due = apply_done(db, lc_num, grade, note if note else None)
    rprint(f"[bold cyan]OK[/bold cyan] done {lc_num} grade={grade} prev_due={prev_due} next_due={next_due}")
def _quick_done(lc_num: int, grade: str, note: str, db: Path):
    prev_due, next_due = apply_done(db, lc_num, grade, note if note else None)
    rprint(f"[bold cyan]OK[/bold cyan] done {lc_num} grade={grade} prev_due={prev_due} next_due={next_due}")

@app.command()
def again(
    lc_num: int = typer.Argument(..., help="LeetCode problem number"),
    note: str = typer.Option("", "--note", help="Optional note"),
    db: Path = typer.Option(DEFAULT_DB_PATH, "--db", help="Path to sqlite db file"),
):
    """Shortcut for: done <lc_num> again"""
    _quick_done(lc_num, "again", note, db)

@app.command()
def hard(
    lc_num: int = typer.Argument(..., help="LeetCode problem number"),
    note: str = typer.Option("", "--note", help="Optional note"),
    db: Path = typer.Option(DEFAULT_DB_PATH, "--db", help="Path to sqlite db file"),
):
    """Shortcut for: done <lc_num> hard"""
    _quick_done(lc_num, "hard", note, db)

@app.command()
def good(
    lc_num: int = typer.Argument(..., help="LeetCode problem number"),
    note: str = typer.Option("", "--note", help="Optional note"),
    db: Path = typer.Option(DEFAULT_DB_PATH, "--db", help="Path to sqlite db file"),
):
    """Shortcut for: done <lc_num> good"""
    _quick_done(lc_num, "good", note, db)

@app.command()
def easy(
    lc_num: int = typer.Argument(..., help="LeetCode problem number"),
    note: str = typer.Option("", "--note", help="Optional note"),
    db: Path = typer.Option(DEFAULT_DB_PATH, "--db", help="Path to sqlite db file"),
):
    """Shortcut for: done <lc_num> easy"""
    _quick_done(lc_num, "easy", note, db)

cursor_app = typer.Typer(help="Manage NEW cursor (only affects NEW)")
app.add_typer(cursor_app, name="cursor")

@cursor_app.command("set")
def cursor_set_cmd(
    lc_num: int = typer.Argument(..., help="Set NEW start to this LeetCode number"),
    db: Path = typer.Option(DEFAULT_DB_PATH, "--db", help="Path to sqlite db file"),
):
    po = cursor_set(db, lc_num)
    rprint(f"[bold cyan]OK[/bold cyan] cursor_plan_order set to {po} (lc_num={lc_num})")

@app.command("mark-done-before")
def mark_done_before_cmd(
    lc_num: int = typer.Argument(..., help="All problems before this become due REVIEW"),
    force: bool = typer.Option(False, "--force", help="Also force existing reviews to become due now"),
    db: Path = typer.Option(DEFAULT_DB_PATH, "--db", help="Path to sqlite db file"),
):
    n = mark_done_before(db, lc_num, force=force)
    rprint(f"[bold cyan]OK[/bold cyan] seeded {n} missing problems before {lc_num}; force={force}")

@app.command()
def history(
    n: int = typer.Option(15, "--n", help="How many recent logs to show"),
    all: bool = typer.Option(False, "--all", help="Include seed logs"),
    notes: bool = typer.Option(False, "--notes", help="Show note column"),
    db: Path = typer.Option(DEFAULT_DB_PATH, "--db", help="Path to sqlite db file"),
):
    """Show recent review logs."""
    items = fetch_history(db, n=n, include_seed=all)

    table = Table(title=f"History (last {len(items)})", show_lines=False)
    table.add_column("Time", no_wrap=True)
    table.add_column("LC", justify="right", no_wrap=True)
    table.add_column("Grade", no_wrap=True)
    table.add_column("NextDue", no_wrap=True)
    table.add_column("Title")

    if notes:
        table.add_column("Note")

    for it in items:
        t = datetime.fromtimestamp(it.reviewed_at).strftime("%m-%d %H:%M")
        nd = "-" if it.next_due_at is None else datetime.fromtimestamp(it.next_due_at).strftime("%m-%d")
        row = [t, str(it.lc_num), it.grade, nd, it.title]

        if notes:
            row.append(it.note or "")
        table.add_row(*row)

    Console().print(table)

@app.command()
def stats(db: Path = typer.Option(DEFAULT_DB_PATH, "--db", help="Path to sqlite db file")):
    """Show key SRS stats."""
    s = compute_stats(db)

    rprint("[bold]STATS[/bold]")
    rprint(f"Cursor: plan_order={s.cursor_plan_order}  lc={s.cursor_lc_num}  {s.cursor_title or ''}")
    rprint(f"Problems: {s.problems_total}")
    rprint(f"Reviews:  total={s.reviews_total}  active={s.active_total}  retired={s.retired_total}")
    rprint(f"Due now:  {s.due_total}")
    rprint(f"Activity: today={s.logs_today}  last7d={s.logs_7d}")

@app.command()
def open(
    lc_num: int | None = typer.Argument(None, help="Optional LeetCode number (default: current NEW)"),
    db: Path = typer.Option(DEFAULT_DB_PATH, "--db", help="Path to sqlite db file"),
):
    """Open LeetCode page for current NEW (or a specific lc_num)."""
    url = open_problem(db, lc_num=lc_num)
    rprint(f"[dim]{url}[/dim]")


def main():
    app()

if __name__ == "__main__":
    main()
