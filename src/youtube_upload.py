import argparse, json, os
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def create_client():
    values = [os.getenv(k) for k in ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")]
    if not all(values):
        raise RuntimeError("Set YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET and YOUTUBE_REFRESH_TOKEN.")
    creds = Credentials(None, refresh_token=values[2],
        token_uri="https://oauth2.googleapis.com/token", client_id=values[0],
        client_secret=values[1], scopes=SCOPES)
    creds.refresh(Request())
    return build("youtube", "v3", credentials=creds, cache_discovery=False)

def upload(video_path, metadata, privacy="private", thumbnail=None):
    path = Path(video_path)
    if not path.is_file() or path.stat().st_size == 0:
        raise FileNotFoundError(f"Video file missing/empty: {path}")
    if path.suffix.lower() not in {".mp4", ".mov", ".m4v", ".webm"}:
        raise ValueError("Unsupported video extension.")
    if privacy not in {"private", "unlisted", "public"}:
        raise ValueError("Invalid privacy setting.")
    if privacy == "public" and os.getenv("ALLOW_PUBLIC_PUBLISH", "false").lower() != "true":
        raise PermissionError("Public upload blocked by default. Use private/unlisted or deliberately enable ALLOW_PUBLIC_PUBLISH.")
    yt = create_client()
    snippet = {
        "title": str(metadata.get("title", "Hindi Educational Video"))[:100],
        "description": str(metadata.get("description", ""))[:5000],
        "categoryId": str(metadata.get("category_id", "27")),
        "defaultLanguage": "hi",
        "defaultAudioLanguage": "hi"
    }
    tags = metadata.get("tags", [])
    if isinstance(tags, str):
        tags = [x.strip() for x in tags.split(",") if x.strip()]
    if tags: snippet["tags"] = [str(x)[:100] for x in tags[:30]]
    request = yt.videos().insert(
        part="snippet,status",
        body={"snippet": snippet, "status": {"privacyStatus": privacy}},
        media_body=MediaFileUpload(str(path), chunksize=8*1024*1024, resumable=True)
    )
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status: print(f"Upload progress: {int(status.progress()*100)}%")
    result = {"video_id": response["id"], "url": f"https://www.youtube.com/watch?v={response['id']}", "privacy": privacy}
    if thumbnail and Path(thumbnail).is_file():
        try:
            yt.thumbnails().set(videoId=response["id"], media_body=thumbnail).execute()
            result["thumbnail_uploaded"] = True
        except Exception as exc:
            result["thumbnail_uploaded"] = False
            result["thumbnail_error"] = str(exc)
    return result

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--metadata", required=True)
    ap.add_argument("--privacy", default="private")
    ap.add_argument("--thumbnail")
    ap.add_argument("--result", default="upload_result.json")
    a = ap.parse_args()
    metadata = json.loads(Path(a.metadata).read_text(encoding="utf-8"))
    result = upload(a.video, metadata, a.privacy, a.thumbnail)
    Path(a.result).parent.mkdir(parents=True, exist_ok=True)
    Path(a.result).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
