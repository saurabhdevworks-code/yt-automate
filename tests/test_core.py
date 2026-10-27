from src.generate_pack import generate_metadata
from src.notebooklm_automation import normalize_cookie

def test_fallback_metadata(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    data = generate_metadata("AI in India", "Hindi viewers")
    assert data["title"]
    assert isinstance(data["tags"], list)
    assert data["thumbnail_text"]

def test_cookie_normalization():
    # Cookie-Editor export format with no_restriction and expirationDate
    ce_cookie = {
        "domain": ".google.com",
        "expirationDate": 1780000000.5,
        "hostOnly": False,
        "httpOnly": True,
        "name": "__Secure-1PSID",
        "path": "/",
        "sameSite": "no_restriction",
        "secure": True,
        "session": False,
        "storeId": "0",
        "value": "secret_token",
    }
    normalized = normalize_cookie(ce_cookie)
    assert normalized is not None
    assert normalized["sameSite"] == "None"
    assert normalized["expires"] == 1780000000.5
    assert "expirationDate" not in normalized
    assert "hostOnly" not in normalized
    assert normalized["domain"] == ".google.com"
    assert normalized["path"] == "/"
