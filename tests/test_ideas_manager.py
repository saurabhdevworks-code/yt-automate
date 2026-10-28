import pytest
from pathlib import Path
from src.ideas_manager import (
    load_ideas,
    save_ideas,
    get_next_unused_idea,
    mark_idea_used,
    pick_and_mark_next_idea,
)

SAMPLE_CSV = """id,topic,status,used_at,notes
1,Topic One,pending,,Note 1
2,Topic Two,pending,,Note 2
3,Topic Three,used,2026-10-20 10:00:00 UTC,Note 3
"""

def test_load_ideas(tmp_path):
    csv_file = tmp_path / "ideas.csv"
    csv_file.write_text(SAMPLE_CSV, encoding="utf-8")

    rows, fieldnames = load_ideas(csv_file)
    assert len(rows) == 3
    assert rows[0]["topic"] == "Topic One"
    assert rows[0]["status"] == "pending"

def test_get_next_unused_idea(tmp_path):
    csv_file = tmp_path / "ideas.csv"
    csv_file.write_text(SAMPLE_CSV, encoding="utf-8")

    idea = get_next_unused_idea(csv_file)
    assert idea is not None
    assert idea["id"] == "1"
    assert idea["topic"] == "Topic One"

def test_pick_and_mark_next_idea_progression(tmp_path):
    csv_file = tmp_path / "ideas.csv"
    csv_file.write_text(SAMPLE_CSV, encoding="utf-8")

    # First pick -> Topic One
    picked1 = pick_and_mark_next_idea(csv_file)
    assert picked1 == "Topic One"

    # Second pick -> Topic Two
    picked2 = pick_and_mark_next_idea(csv_file)
    assert picked2 == "Topic Two"

    # Third pick -> None (since Topic Three is already 'used')
    picked3 = pick_and_mark_next_idea(csv_file)
    assert picked3 is None

def test_mark_idea_used_by_topic_name(tmp_path):
    csv_file = tmp_path / "ideas.csv"
    csv_file.write_text(SAMPLE_CSV, encoding="utf-8")

    success = mark_idea_used(csv_file, "Topic Two")
    assert success is True

    rows, _ = load_ideas(csv_file)
    row2 = next(r for r in rows if r["id"] == "2")
    assert row2["status"] == "used"
    assert row2["used_at"] != ""

def test_missing_csv_returns_none(tmp_path):
    missing_file = tmp_path / "does_not_exist.csv"
    assert pick_and_mark_next_idea(missing_file) is None
    assert get_next_unused_idea(missing_file) is None
