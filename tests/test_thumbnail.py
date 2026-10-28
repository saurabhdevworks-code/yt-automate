import json
from pathlib import Path
from src.thumbnail import make_thumbnail

def test_make_thumbnail_scheme_format(tmp_path):
    meta = {
        "topic": "सोलर पंप योजना और सब्सिडी",
        "thumbnail_format": "scheme",
        "thumbnail_line1": "सोलर पंप योजना से",
        "thumbnail_highlight": "80% सब्सिडी तुरंत!",
        "thumbnail_benefit": "⚡ बिजली बिल ₹0 • पानी भरपूर",
        "thumbnail_top_badge": "🚨 सरकारी योजना 2026",
        "thumbnail_stat_num": "80%",
        "thumbnail_stat_title": "सरकारी सब्सिडी",
        "thumbnail_stat_tag": "✔ ऑनलाइन आवेदन शुरू"
    }
    meta_file = tmp_path / "metadata.json"
    meta_file.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    out_file = tmp_path / "thumb_scheme.jpg"

    res = make_thumbnail(metadata_path=str(meta_file), output=str(out_file))
    assert Path(res).exists()
    assert Path(res).stat().st_size > 5000

def test_make_thumbnail_profit_format(tmp_path):
    meta = {
        "topic": "पॉलीहाउस खेती से लाखों का मुनाफा",
        "thumbnail_format": "profit",
        "thumbnail_line1": "पॉलीहाउस खेती से",
        "thumbnail_highlight": "₹5 लाख महीना कमाई!",
        "thumbnail_benefit": "🚀 कम जमीन में 4x ज्यादा मुनाफा",
        "thumbnail_top_badge": "💰 बंपर कमाई 2026",
        "thumbnail_stat_num": "₹5L",
        "thumbnail_stat_title": "प्रति महीना कमाई",
        "thumbnail_stat_tag": "✔ 100% सफल मॉडल"
    }
    meta_file = tmp_path / "metadata.json"
    meta_file.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    out_file = tmp_path / "thumb_profit.jpg"

    res = make_thumbnail(metadata_path=str(meta_file), output=str(out_file))
    assert Path(res).exists()
    assert Path(res).stat().st_size > 5000

def test_make_thumbnail_cli_fallback(tmp_path):
    out_file = tmp_path / "thumb_simple.jpg"
    res = make_thumbnail(text="ड्रिप सिंचाई से बंपर पैदावार", output=str(out_file))
    assert Path(res).exists()
    assert Path(res).stat().st_size > 1000
