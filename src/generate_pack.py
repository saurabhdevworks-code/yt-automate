import argparse, json, os, re, sys
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
from pathlib import Path
from datetime import datetime, timezone
import requests
from src.research import discover_topics
from src.ideas_manager import pick_and_mark_next_idea, mark_idea_used, resolve_ideas_csv

ROOT = Path(__file__).resolve().parents[1]

def load_context():
    for rel in ["context/channel_context.json", "Context/channel_context.json", "config/channel_context.json"]:
        p = ROOT / rel
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                pass
    return {
        "channel_name": "BEYOND THE OBVIOUS",
        "niche": "Mind-Bending Book Summaries, Deep Philosophy, Dark Psychology & Craziest Theories",
        "country": "United States",
        "location": "United States",
        "language": "English",
        "target_audience": "USA & Global English viewers, curious thinkers, philosophy & psychology enthusiasts, book lovers, and theory explorers",
        "thumbnail_fonts": ["Montserrat", "Bebas Neue", "Poppins", "Inter"]
    }

def load_yt_rules():
    for rel in ["context/yt_rules.json", "Context/yt_rules.json", "config/yt_rules.json"]:
        p = ROOT / rel
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                pass
    return None

def generate_metadata(topic, audience, channel_info=None):
    if channel_info is None:
        channel_info = load_context()
    ch_name = channel_info.get("channel_name", "BEYOND THE OBVIOUS")

    # Smart English fallback metadata
    fallback = {
        "title": f"{topic} | {ch_name}",
        "description": (
            f"Welcome to {ch_name}.\n\n"
            f"In this deep dive, we explore: {topic}.\n\n"
            f"We deconstruct the core psychology, mind-bending philosophical paradoxes, "
            f"and transformative book insights that shatter conventional thinking.\n\n"
            f"📌 Subscribe to {ch_name} for weekly deep dives into the craziest theories, "
            f"hidden psychology, and transformative books that change how you see reality.\n\n"
            f"#BeyondTheObvious #Philosophy #Psychology #BookSummary #SimulationTheory #DarkPsychology"
        ),
        "tags": [
            ch_name, "Beyond The Obvious", "Book Summary", "Psychology", "Philosophy",
            "Craziest Theories", "Mind Bending Theories", "Simulation Theory", "Deep Thinking",
            "Fermi Paradox", "Dark Psychology", "Cognitive Biases", "Self Improvement Books"
        ],
        "hashtags": ["#BeyondTheObvious", "#Psychology", "#Philosophy", "#BookSummary", "#DeepThinking"],
        "thumbnail_text": "SHATTER REALITY",
        "thumbnail_format": "mystery",
        "thumbnail_line1": "THE HIDDEN TRUTH OF",
        "thumbnail_highlight": "WHAT THEY HIDE!",
        "thumbnail_benefit": "👁️ The Mind-Bending Paradox Explained",
        "thumbnail_top_badge": "🚨 PARADIGM SHIFT",
        "thumbnail_stat_num": "99.9%",
        "thumbnail_stat_title": "Will Question Reality",
        "thumbnail_stat_tag": "✔ Mind-Bending Theory",
        "thumbnail_image_prompt": (
            f"Cinematic dark psychological mystery YouTube thumbnail exploring {topic}, "
            "striking visual metaphor, glowing surreal illumination in cosmic deep shadows, "
            "ultra-detailed 4K photorealistic composition, octane render quality, breathtaking aesthetic."
        )
    }

    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return fallback

    yt_rules = load_yt_rules()
    rules_text = ""
    if yt_rules:
        rules_text = f"\nCustom YouTube Guidelines (from context/yt_rules.json):\n{json.dumps(yt_rules, ensure_ascii=False, indent=2)}\nFollow these instructions strictly.\n"

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    prompt = (
        f"You are the executive YouTube strategist for the prestigious channel '{ch_name}'.\n"
        f"Niche: Mind-Bending Book Summaries, Deep Philosophy, Dark Psychology, and Craziest Unsolved Theories.\n"
        f"Target Audience: USA & Global English thinkers, book lovers, psychology & philosophy enthusiasts.\n"
        f"Topic: {topic}\n"
        f"{rules_text}\n"
        "Generate a viral, intellectual, high-CTR YouTube metadata package in natural, captivating English.\n"
        "Requirements:\n"
        "1. title: Intriguing, click-worthy English title under 80 characters. Balance philosophical curiosity and viral hook (e.g. 'The Dark Forest Theory: Why Finding Aliens Is Our Worst Nightmare').\n"
        "2. description: Well-structured, intellectual English description with an irresistible hook, key insights breakdown, book/theory synthesis, and call-to-action.\n"
        "3. tags: Array of 20-30 high-ranking English search tags relevant to books, psychology, theories, and this specific topic.\n"
        "4. hashtags: 3-5 relevant hashtags including #BeyondTheObvious.\n"
        "5. thumbnail_format: pick one of 'paradox', 'glitch', or 'mystery'.\n"
        "6. thumbnail_line1: Short uppercase English context line (3-4 words, e.g. 'THE TERRIFYING TRUTH' or 'WHY REALITY IS A LIE').\n"
        "7. thumbnail_highlight: Massive high-impact curiosity hook (2-4 words, e.g. 'NOT WHAT IT SEEMS', 'DON'T LOOK AWAY').\n"
        "8. thumbnail_benefit: Intriguing supporting line (e.g. '👁️ The Paradox That Shook Physicists').\n"
        "9. thumbnail_top_badge: Alert hook badge (e.g. '🚨 MIND-BENDING THEORY' or '📖 FORBIDDEN PSYCHOLOGY').\n"
        "10. thumbnail_stat_num: Bold impact number or phrase (e.g. '1 IN A BILLION' or '99.9%' or 'THE 1% RULE').\n"
        "11. thumbnail_stat_title: Stat label (e.g. 'Probability' or 'Mind Glitch' or 'Paradox Unlocked').\n"
        "12. thumbnail_stat_tag: Trust/intrigue tag (e.g. '✔ Verified Concept' or '✔ Bestselling Book').\n"
        "13. thumbnail_image_prompt: Highly detailed 16:9 cinematic prompt for Google Imagen 3 image generation showing a surreal philosophical/psychological visual metaphor, dramatic shadows, ray-traced neon/amber glow, 4K film quality.\n"
        "14. thumbnail_text: 2-3 punchy uppercase English words for mobile screens.\n"
        "Return ONLY a valid JSON object matching these keys."
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
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            parsed = json.loads(match.group(0))
            for k, v in fallback.items():
                if k not in parsed or not parsed[k]:
                    parsed[k] = v
            return parsed
    except Exception as e:
        print(f"[WARN] Gemini metadata generation failed: {e}. Using fallback.")
    return fallback

def main():
    ap = argparse.ArgumentParser(description="Generate AI Research Pack for Beyond The Obvious")
    ap.add_argument("--settings", default="config/settings.json")
    ap.add_argument("--output", default="output")
    ap.add_argument("--ideas-file", default="context/topics.csv")
    ap.add_argument("--disable-csv-ideas", action="store_true")
    ap.add_argument("--custom-topic", default="")
    ap.add_argument("--custom-title", default="")
    ap.add_argument("--custom-description", default="")
    ap.add_argument("--custom-tags", default="")
    args = ap.parse_args()

    settings = json.loads(Path(args.settings).read_text(encoding="utf-8")) if Path(args.settings).exists() else {}
    channel_info = load_context()
    ch_name = channel_info.get("channel_name", "BEYOND THE OBVIOUS")
    ideas_csv = resolve_ideas_csv(ROOT / args.ideas_file if args.ideas_file != "config/ideas.csv" else None)

    if args.custom_topic.strip():
        topic = args.custom_topic.strip()
        print(f"\n[CUSTOM MODE - {ch_name}] Topic: '{topic}'")
        if not args.disable_csv_ideas and ideas_csv.exists():
            if mark_idea_used(ideas_csv, topic):
                print(f"[IDEAS CSV] Marked topic '{topic}' as 'used' in {args.ideas_file}")
        topics = [{
            "title": topic,
            "url": "https://en.wikipedia.org/wiki/Special:Search?search=" + requests.utils.quote(topic),
            "publisher": f"{ch_name} (Custom Request)",
            "published": datetime.now(timezone.utc).isoformat(),
            "summary": f"In-depth philosophical and psychological analysis of {topic}."
        }]
    else:
        csv_topic = None
        if not args.disable_csv_ideas and ideas_csv.exists():
            csv_topic = pick_and_mark_next_idea(ideas_csv)

        if csv_topic:
            topic = csv_topic
            print(f"\n[AUTO MODE - {ch_name}] Picked next pending topic from CSV: '{topic}'")
            print(f"[IDEAS CSV] Marked as 'used' in {args.ideas_file} to avoid duplication.")
            topics = [{
                "title": topic,
                "url": "https://en.wikipedia.org/wiki/Special:Search?search=" + requests.utils.quote(topic),
                "publisher": f"{ch_name} (Curated Idea from CSV)",
                "published": datetime.now(timezone.utc).isoformat(),
                "summary": f"Comprehensive synthesis and philosophical breakdown of {topic}."
            }]
        else:
            if ideas_csv.exists() and not args.disable_csv_ideas:
                print("\n" + "=" * 70)
                print(f" [PIPELINE PAUSED] All topics in {ideas_csv.name} have been completed!")
                print(f" All curated book & theory topics completed. Pipeline is safely paused.")
                print(f" Add new topics (status: 'unused') in {ideas_csv.name} to resume.")
                print("=" * 70 + "\n")
                pause_file = ROOT / args.output / "PIPELINE_PAUSED.txt"
                pause_file.parent.mkdir(parents=True, exist_ok=True)
                pause_file.write_text("ALL_TOPICS_FINISHED", encoding="utf-8")
                sys.exit(0)
            else:
                print(f"\n[AUTO MODE - {ch_name}] No CSV ideas file found. Searching trending topics via RSS & Wikipedia...")
                topics = discover_topics(settings)
                if not topics:
                    raise SystemExit("No research results were found. Check network/RSS or add sources manually.")
                topic = topics[0]["title"]

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out = ROOT / args.output / f"research-{stamp}"
    out.mkdir(parents=True, exist_ok=True)

    metadata = generate_metadata(topic, settings.get("target_audience", channel_info.get("target_audience")), channel_info)

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
        f"- [{x['title']}]({x['url']}) — {x.get('publisher','')} | {x.get('published','')}\n  - Summary: {x.get('summary','')}"
        for x in topics
    )
    brief = f"""# Research & Deep Dive Brief: {ch_name}

- Channel: {ch_name}
- Niche: {channel_info.get('niche')}
- Location: {channel_info.get('country', 'United States')}
- Language: {channel_info.get('language', 'English')}
- Target Audience: {channel_info.get('target_audience')}
- Channel Vision: {channel_info.get('channel_vision')}
- Ideal Duration: {settings.get('duration_min_minutes', 5)}–{settings.get('duration_max_minutes', 10)} minutes

## Main Subject / Concept
{topic}

## Objective & Narrative Arc
This research brief is curated for a thoughtful, intellectual audience seeking to look beyond ordinary assumptions.
The goal of this video overview is to synthesize complex ideas, psychological paradoxes, and groundbreaking book lessons into an addictive, mind-expanding intellectual narrative.

Core Pillars:
1. The Core Paradox / Mind-Bending Question: Hook the viewer with what seems impossible or counterintuitive.
2. The Deconstruction: Break down the author's key theories, psychological experiments, or philosophical axioms.
3. The Counter-Narrative: Why society gets this wrong, and what the hidden consequence of this truth is.
4. The Paradigm Shift: The actionable takeaway that permanently changes how the viewer perceives life, society, or the cosmos.

## Curated Sources & Grounding Reference
{source_lines}
"""
    (out / "research_brief.md").write_text(brief, encoding="utf-8")

    prompt = f"""Create an intellectual, highly engaging English Video Overview for thinkers, book lovers, and curious minds.
Channel: {ch_name}
Topic: {topic}
Language: Fluent, natural, engaging American English (clear, compelling storytelling tone).
Style: A deep, mind-expanding podcast conversation between two brilliant thinkers deconstructing the book's most profound lessons, psychological paradoxes, and existential implications.
Format: Cinematic, thought-provoking, avoiding superficial bullet points; dive straight into the existential, psychological, and transformative core of the idea.
"""
    (out / "notebooklm_prompt.txt").write_text(prompt, encoding="utf-8")
    print(f"Research pack created: {out}")
    print(f"Topic: {topic}")

if __name__ == "__main__":
    main()
