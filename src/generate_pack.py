import argparse, json, os, re
from pathlib import Path
from datetime import datetime, timezone
import requests
from src.research import discover_topics

ROOT = Path(__file__).resolve().parents[1]

def generate_metadata(topic, audience):
    fallback = {
        "title": f"{topic} | आसान हिंदी में समझें",
        "description": f"{topic}\n\nइस वीडियो में विषय को सरल हिंदी में समझाया जाएगा। कृपया मूल स्रोतों की जाँच करें।",
        "tags": ["Hindi", "Education", "Technology", "Explained in Hindi"],
        "hashtags": ["#Hindi", "#Education", "#Technology"],
        "thumbnail_text": "आसान हिंदी में"
    }
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return fallback
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    prompt = (
        "Create accurate YouTube metadata in natural Hindi. Do not invent facts or citations. "
        "Return only valid JSON with keys title, description, tags (array), hashtags (array), thumbnail_text. "
        f"Topic: {topic}. Audience: {audience}. Title must be engaging but not misleading. "
        "Thumbnail text must be short (2-5 words)."
    )
    try:
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            params={"key": key},
            json={"contents": [{"parts": [{"text": prompt}]}],
                  "generationConfig": {"temperature": 0.4}},
            timeout=90,
        )
        r.raise_for_status()
        text = "\n".join(p.get("text", "") for c in r.json().get("candidates", [])
                         for p in c.get("content", {}).get("parts", []))
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I)
        obj = json.loads(text)
        for k, v in fallback.items():
            obj.setdefault(k, v)
        return obj
    except Exception as exc:
        print(f"WARNING: Gemini metadata failed; using fallback: {exc}")
        return fallback

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--settings", default="config/settings.json")
    ap.add_argument("--output", default="output")
    args = ap.parse_args()
    settings = json.loads((ROOT / args.settings).read_text(encoding="utf-8"))
    topics = discover_topics(settings)
    if not topics:
        raise SystemExit("No research results were found. Check network/RSS or add sources manually.")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out = ROOT / args.output / f"research-{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    topic = topics[0]["title"]
    metadata = generate_metadata(topic, settings.get("target_audience", "Hindi viewers"))
    (out / "topics.json").write_text(json.dumps(topics, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "research_sources.json").write_text(json.dumps(topics, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    source_lines = "\n".join(
        f"- [{x['title']}]({x['url']}) — {x.get('publisher','')} | {x.get('published','')}\n  - Notes: {x.get('summary','')}"
        for x in topics
    )
    brief = f"""# Research brief

- Niche: {settings.get('niche')}
- Audience: {settings.get('target_audience')}
- Language: {settings.get('language', 'Hindi')}
- Target duration: {settings.get('duration_min_minutes', 4)}–{settings.get('duration_max_minutes', 8)} minutes
- Generated: {datetime.now(timezone.utc).isoformat()}

## Candidate topic
{topic}

## Selection note
This is a heuristic ranking of RSS and Wikipedia discovery results. It is not YouTube search volume or a guarantee of popularity. Verify all facts from original sources.

## Sources to inspect and add to NotebookLM
{source_lines}

## Research cautions
- Search snippets are leads, not proof.
- Prefer official/primary sources and multiple independent sources for important claims.
- Remove irrelevant or low-quality sources before generating.
"""
    (out / "research_brief.md").write_text(brief, encoding="utf-8")
    prompt = f"""Create a Hindi Video Overview for {settings.get('target_audience', 'Hindi-speaking viewers')}.
Topic: {topic}
Style: {settings.get('video_style', 'Educational explainer')}.
Aim for {settings.get('duration_min_minutes', 4)}–{settings.get('duration_max_minutes', 8)} minutes, without promising an exact duration.
Use the supplied sources as the factual basis. Start with a strong but accurate hook, explain concepts in simple Hindi with India-relevant examples, maintain a clear beginning-middle-end, avoid repetition and unsupported statistics, and end with a useful takeaway. Use readable visual text. Do not copy long passages.
The final video must be generated using Google NotebookLM Video Overview only. Do not use any other video generator.
"""
    (out / "notebooklm_prompt.txt").write_text(prompt, encoding="utf-8")
    handoff = f"""# NotebookLM handoff

1. Open https://notebooklm.google.com/
2. Create a notebook for: {topic}
3. Inspect the sources in `research_sources.json`; open and verify them, then add relevant source pages/files to NotebookLM.
4. In Studio, choose Video Overview.
5. Choose Hindi as output language if available and paste `notebooklm_prompt.txt` into custom instructions.
6. Generate and download the video from NotebookLM.
7. Review facts, narration, visuals and duration. Exact {settings.get('duration_min_minutes',4)}–{settings.get('duration_max_minutes',8)} minute duration is not guaranteed.
8. Trigger GitHub Actions → Upload NotebookLM Video with a direct HTTPS download URL for the MP4.
"""
    (out / "NOTEBOOKLM_HANDOFF.md").write_text(handoff, encoding="utf-8")
    print(f"Research pack: {out}")
    print(f"Selected topic: {topic}")

if __name__ == "__main__":
    main()
