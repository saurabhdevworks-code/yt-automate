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
    ap.add_argument("--custom-topic", default="", help="Custom user-specified topic")
    ap.add_argument("--custom-title", default="", help="Custom YouTube title")
    ap.add_argument("--custom-description", default="", help="Custom YouTube description")
    ap.add_argument("--custom-tags", default="", help="Custom YouTube tags (comma-separated)")
    args = ap.parse_args()

    settings = json.loads((ROOT / args.settings).read_text(encoding="utf-8"))

    if args.custom_topic.strip():
        topic = args.custom_topic.strip()
        print(f"\n[CUSTOM MODE] Using user-specified topic: '{topic}'")
        topics = [{
            "title": topic,
            "url": "https://notebooklm.google.com/",
            "publisher": "Custom User Topic",
            "published": datetime.now(timezone.utc).isoformat(),
            "summary": f"Comprehensive explainer and breakdown of {topic}."
        }]
    else:
        print("\n[AUTO MODE] Discovering trending topics automatically via RSS & web feeds...")
        topics = discover_topics(settings)
        if not topics:
            raise SystemExit("No research results were found. Check network/RSS or add sources manually.")
        topic = topics[0]["title"]

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out = ROOT / args.output / f"research-{stamp}"
    out.mkdir(parents=True, exist_ok=True)

    metadata = generate_metadata(topic, settings.get("target_audience", "Hindi viewers"))
    
    # Override with custom metadata if provided by user
    if args.custom_title.strip():
        metadata["title"] = args.custom_title.strip()[:100]
    if args.custom_description.strip():
        metadata["description"] = args.custom_description.strip()[:5000]
    if args.custom_tags.strip():
        metadata["tags"] = [t.strip() for t in args.custom_tags.split(",") if t.strip()][:30]

    (out / "topics.json").write_text(json.dumps(topics, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "research_sources.json").write_text(json.dumps(topics, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    source_lines = "\n".join(
        f"- [{x['title']}]({x['url']}) — {x.get('publisher','')} | {x.get('published','')}\n  - Notes: {x.get('summary','')}"
        for x in topics
    )
    brief = f"""# Research brief

- Topic: {topic}
- Niche: {settings.get('niche')}
- Audience: {settings.get('target_audience')}
- Language: {settings.get('language', 'Hindi')}
- Target duration: {settings.get('duration_min_minutes', 4)}–{settings.get('duration_max_minutes', 8)} minutes
- Generated: {datetime.now(timezone.utc).isoformat()}

## Candidate topic
{topic}

## Detailed Overview
This brief guides NotebookLM to create an engaging Hindi Video Overview explaining {topic}.
Key aspects to cover:
1. Clear explanation of what {topic} is and why it matters today.
2. Background context, origin, and key developments.
3. Real-world impact and India-relevant analogies or examples.
4. Summary takeaway and future outlook.

## Sources
{source_lines}
"""
    (out / "research_brief.md").write_text(brief, encoding="utf-8")
    prompt = f"""Create a comprehensive Hindi Video Overview for {settings.get('target_audience', 'Hindi-speaking viewers')}.
Topic: {topic}
Style: {settings.get('video_style', 'Educational explainer')}.
Aim for {settings.get('duration_min_minutes', 4)}–{settings.get('duration_max_minutes', 8)} minutes.
Start with a strong, curiosity-inducing hook. Explain key ideas in clean, simple conversational Hindi. Maintain a logical narrative flow from introduction to deep-dive to conclusion. Avoid unsupported claims. Ensure the visuals and narration are clear and engaging.
The final video must be generated using Google NotebookLM Video Overview in Hindi.
"""
    (out / "notebooklm_prompt.txt").write_text(prompt, encoding="utf-8")
    handoff = f"""# NotebookLM handoff

1. Open https://notebooklm.google.com/
2. Create a notebook for: {topic}
3. Sources and notes are in `research_brief.md`.
4. In Studio, choose Video Overview (Language: Hindi).
"""
    (out / "NOTEBOOKLM_HANDOFF.md").write_text(handoff, encoding="utf-8")
    print(f"Research pack: {out}")
    print(f"Selected topic: {topic}")

if __name__ == "__main__":
    main()
