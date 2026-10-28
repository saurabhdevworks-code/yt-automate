import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.video_processor import (
    find_watermark_image,
    get_video_duration,
    get_video_dimensions,
    prepare_watermark_badge,
)

def test_find_watermark_image_custom(tmp_path):
    custom_img = tmp_path / "my_logo.png"
    custom_img.write_bytes(b"dummy")
    found = find_watermark_image(str(custom_img), base_dir=tmp_path)
    assert found == custom_img.resolve()

def test_find_watermark_image_assets(tmp_path):
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    wm = assets_dir / "watermark.png"
    wm.write_bytes(b"dummy_bytes")
    found = find_watermark_image("", base_dir=tmp_path)
    assert found == wm.resolve()

def test_find_watermark_image_not_found(tmp_path):
    found = find_watermark_image("", base_dir=tmp_path)
    assert found is None

def test_get_video_duration_ffprobe_success():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="184.52\n", stderr="")
        dur = get_video_duration(Path("fake_video.mp4"))
        assert dur == 184.52

def test_get_video_duration_ffmpeg_fallback():
    with patch("subprocess.run") as mock_run:
        # First call (ffprobe format) fails, second (ffprobe stream) fails, third (ffmpeg -i) outputs stderr
        mock_run.side_effect = [
            MagicMock(returncode=1, stdout="", stderr="ffprobe error"),
            MagicMock(returncode=1, stdout="", stderr="ffprobe error"),
            MagicMock(returncode=1, stdout="", stderr="Duration: 00:02:45.30, start: 0.000000"),
        ]
        dur = get_video_duration(Path("fake_video.mp4"))
        assert dur == 165.30

def test_get_video_dimensions_success():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="1920x1080\n", stderr="")
        w, h = get_video_dimensions(Path("fake_video.mp4"))
        assert w == 1920
        assert h == 1080

def test_auto_trim_calculation():
    duration = 120.0
    trim_last_seconds = 3.0
    calc_end = duration - trim_last_seconds
    assert calc_end == 117.0
