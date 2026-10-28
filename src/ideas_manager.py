"""Video Ideas Manager from CSV.
Allows organizing, picking, and marking video topics to avoid duplication.
- Reads topics from CSV (e.g. config/ideas.csv).
- Picks the first unused/pending topic.
- Marks the topic as 'used' with timestamp once picked.
- Completely optional: falls back gracefully if CSV is missing or all topics are used.
"""
import csv
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COLUMNS = ["id", "topic", "status", "used_at", "notes"]


def resolve_ideas_csv(csv_path: Path = None) -> Path:
    """Resolve topics CSV, prioritizing context/topics.csv."""
    if csv_path:
        p = Path(csv_path)
        if not p.is_absolute():
            p = ROOT / p
        return p
    for candidate in [
        ROOT / "context" / "topics.csv",
        ROOT / "Context" / "topics.csv",
        ROOT / "context" / "Topics.csv",
        ROOT / "config" / "ideas.csv",
    ]:
        if candidate.is_file():
            return candidate.resolve()
    return (ROOT / "context" / "topics.csv").resolve()


def is_status_unused(status: str) -> bool:
    """Check if the status string indicates an unused idea."""
    if not status:
        return True
    s = str(status).strip().lower()
    return s in {"pending", "new", "unused", "todo", "open", "available", "0", "false"}


def load_ideas(csv_path: Path) -> tuple[list[dict], list[str]]:
    """Load ideas from a CSV file with automatic column normalization.
    Returns (list_of_row_dicts, fieldnames).
    """
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return [], DEFAULT_COLUMNS

    try:
        # Use utf-8-sig to handle both UTF-8 and Excel-exported BOM CSVs
        with open(csv_path, mode="r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            fieldnames = [fn.strip() for fn in (reader.fieldnames or [])]
            if not fieldnames:
                return [], DEFAULT_COLUMNS

            rows = []
            for r in reader:
                cleaned_row = {k.strip(): (v.strip() if v else "") for k, v in r.items() if k}
                rows.append(cleaned_row)
            return rows, fieldnames
    except Exception as e:
        print(f"[IDEAS CSV WARNING] Failed to read {csv_path}: {e}")
        return [], DEFAULT_COLUMNS


def save_ideas(csv_path: Path, rows: list[dict], fieldnames: list[str]) -> bool:
    """Save ideas back to CSV preserving existing fields and structure."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        # Ensure standard columns are present
        for col in ["id", "topic", "status", "used_at"]:
            if col not in fieldnames:
                fieldnames.append(col)

        with open(csv_path, mode="w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            for r in rows:
                writer.writerow(r)
        return True
    except Exception as e:
        print(f"[IDEAS CSV ERROR] Failed to save {csv_path}: {e}")
        return False


def get_next_unused_idea(csv_path: Path = None) -> dict | None:
    """Find and return the next unused topic from the CSV file.
    Returns None if CSV does not exist or all ideas are already marked as used.
    """
    csv_path = resolve_ideas_csv(csv_path)
    rows, _ = load_ideas(csv_path)
    if not rows:
        return None

    for row in rows:
        # Find topic column flexibly (topic, idea, title, subject)
        topic = row.get("topic") or row.get("idea") or row.get("title") or row.get("subject")
        if not topic:
            continue

        status = row.get("status", "")
        if is_status_unused(status):
            return row

    return None


def mark_idea_used(csv_path: Path, topic_or_id: str, timestamp: str = None) -> bool:
    """Mark an idea as 'used' in the CSV by matching topic string or ID."""
    csv_path = resolve_ideas_csv(csv_path)
    if not csv_path.exists():
        return False

    rows, fieldnames = load_ideas(csv_path)
    if not rows:
        return False

    if not timestamp:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    target = str(topic_or_id).strip().lower()
    matched = False

    for row in rows:
        row_id = str(row.get("id", "")).strip().lower()
        row_topic = str(row.get("topic") or row.get("idea") or row.get("title") or "").strip().lower()

        if row_id == target or row_topic == target or (target and target in row_topic):
            row["status"] = "used"
            row["used_at"] = timestamp
            matched = True
            break

    if matched:
        save_ideas(csv_path, rows, fieldnames)
        return True

    return False


def pick_and_mark_next_idea(csv_path: Path = None) -> str | None:
    """Convenience function:
    1. Finds the next unused idea.
    2. Marks it as 'used' with current timestamp.
    3. Returns the topic string, or None if no pending idea.
    """
    csv_path = resolve_ideas_csv(csv_path)
    if not csv_path.exists():
        return None

    rows, fieldnames = load_ideas(csv_path)
    if not rows:
        return None

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    for row in rows:
        topic = row.get("topic") or row.get("idea") or row.get("title") or ""
        topic_clean = topic.strip()
        if not topic_clean:
            continue

        if is_status_unused(row.get("status", "")):
            row["status"] = "used"
            row["used_at"] = timestamp
            save_ideas(csv_path, rows, fieldnames)
            return topic_clean

    return None
