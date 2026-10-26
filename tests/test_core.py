from src.generate_pack import generate_metadata

def test_fallback_metadata(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    data = generate_metadata("AI in India", "Hindi viewers")
    assert data["title"]
    assert isinstance(data["tags"], list)
    assert data["thumbnail_text"]
