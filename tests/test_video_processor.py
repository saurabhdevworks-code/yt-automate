import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.video_processor import (
    find_watermark_image,
    get_video_duration,
    get_video_dimensions,
    remove_or_replace_watermark,
)

def test_find_watermark_image_custom(tmp_path):
    custom_img = tmp_path / "my_logo.png"
    custom_img.write_bytes(b"dummy")
    found = find_watermark_image(str(custom_img), base_dir=tmp_path)
    assert found == custom_img.resolve()

def test_find_watermark_image_in_assets_images(tmp_path):
    images_dir = tmp_path / "assets" / "images"
    images_dir.mkdir(parents=True)
    wm = images_dir / "watermark.png"
    wm.write_bytes(b"dummy_bytes")
    found = find_watermark_image("", base_dir=tmp_path)
    assert found == wm.resolve()

def test_find_watermark_image_none_when_empty(tmp_path):
    # Empty directory - should return None so watermark is cleanly removed without image
    images_dir = tmp_path / "assets" / "images"
    images_dir.mkdir(parents=True)
    found = find_watermark_image("", base_dir=tmp_path)
    assert found is None

def test_remove_watermark_without_image_runs_delogo():
    with patch("subprocess.run") as mock_run, patch("src.video_processor.get_video_dimensions", return_value=(1920, 1080)):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        
        input_vid = Path("test_input.mp4")
        output_vid = Path("test_output.mp4")
        remove_or_replace_watermark(input_vid, output_vid, watermark_image=None)
        
        assert mock_run.called
        cmd = mock_run.call_args[0][0]
        cmd_str = " ".join(cmd)
        assert "delogo=" in cmd_str
        assert "overlay=" not in cmd_str

def test_remove_watermark_with_image_runs_delogo_and_overlay(tmp_path):
    wm_img = tmp_path / "watermark.png"
    wm_img.write_bytes(b"dummy")
    
    with patch("subprocess.run") as mock_run, \
         patch("src.video_processor.get_video_dimensions", return_value=(1920, 1080)), \
         patch("src.video_processor.prepare_watermark_badge", return_value=wm_img):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        
        input_vid = Path("test_input.mp4")
        output_vid = Path("test_output.mp4")
        remove_or_replace_watermark(input_vid, output_vid, watermark_image=wm_img, work_dir=tmp_path)
        
        assert mock_run.called
        cmd = mock_run.call_args[0][0]
        cmd_str = " ".join(cmd)
        assert "delogo=" in cmd_str
        assert "overlay=" in cmd_str

def test_get_video_duration_ffprobe_success():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="184.52\n", stderr="")
        dur = get_video_duration(Path("fake_video.mp4"))
        assert dur == 184.52

def test_auto_trim_calculation():
    duration = 120.0
    trim_last_seconds = 3.0
    calc_end = duration - trim_last_seconds
    assert calc_end == 117.0
