import json
from pathlib import Path
from src.generate_pack import load_yt_rules, load_context
from src.ideas_manager import resolve_ideas_csv, pick_and_mark_next_idea
from src.video_processor import find_watermark_image
from src.thumbnail import resolve_template_html

def test_load_context_and_yt_rules():
    ctx = load_context()
    assert ctx["channel_name"] == "Kisan bdlega"
    assert "Farming" in ctx["niche"]

    rules = load_yt_rules()
    assert "title_rules" in rules
    assert "description_rules" in rules
    assert "tags_rules" in rules

def test_resolve_topics_csv_prefers_context(tmp_path):
    ctx_csv = tmp_path / "context" / "topics.csv"
    ctx_csv.parent.mkdir(parents=True, exist_ok=True)
    ctx_csv.write_text("id,topic,status,used_at,notes\n1,ड्रोन खेती,pending,,", encoding="utf-8")

    cfg_csv = tmp_path / "config" / "ideas.csv"
    cfg_csv.parent.mkdir(parents=True, exist_ok=True)
    cfg_csv.write_text("id,topic,status,used_at,notes\n1,पुराना टॉपिक,pending,,", encoding="utf-8")

    # When context exists
    assert resolve_ideas_csv(ctx_csv) == ctx_csv

def test_resolve_template_html():
    scheme_tpl = resolve_template_html(fmt_type="scheme")
    assert "title-line-1" in scheme_tpl
    assert "highlight-banner" in scheme_tpl

    split_tpl = resolve_template_html(template_name="template4_split")
    assert "split-overlay" in split_tpl

def test_find_watermark_in_context_images(tmp_path):
    wm_dir = tmp_path / "context" / "images" / "watermark"
    wm_dir.mkdir(parents=True, exist_ok=True)
    dummy_wm = wm_dir / "watermark.png"
    dummy_wm.write_bytes(b"dummy_png_bytes")

    found = find_watermark_image(base_dir=tmp_path)
    assert found is not None
    assert found.name == "watermark.png"
