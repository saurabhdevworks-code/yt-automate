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
from src.ideas_manager import pick_and_mark_next_idea, mark_idea_used

ROOT = Path(__file__).resolve().parents[1]

def load_context():
    ctx_path = ROOT / "config" / "channel_context.json"
    if ctx_path.exists():
        try:
            return json.loads(ctx_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "channel_name": "Kisan bdlega",
        "niche": "Farming and Agriculture",
        "country": "India",
        "location": "India",
        "language": "Hindi",
        "target_audience": "भारतीय किसान, ग्रामीण युवा और आधुनिक कृषि उद्यमी",
        "thumbnail_fonts": ["Mukta", "Hind", "Poppins", "Baloo"]
    }

def generate_metadata(topic, audience, channel_info):
    ch_name = channel_info.get("channel_name", "Kisan bdlega")
    fallback = {
        "title": f"{topic} | {ch_name} - किसान बदलेगा",
        "description": (
            f"स्वागत है '{ch_name}' पर!\n\n"
            f"इस वीडियो में हम बात करेंगे: {topic} के बारे में। "
            f"आधुनिक खेती, उन्नत बीज, नई कृषि तकनीक, खाद प्रबंधन और सरकारी योजनाओं की पूरी जानकारी।\n\n"
            f"📌 चैनल को Subscribe करें और अपनी खेती को बनाएं अधिक मुनाफेदार!\n"
            f"किसान बदलेगा तो देश बदलेगा! 🌾\n\n"
            f"#KisanBdlega #KhetiBadi #SmartFarming #IndianAgriculture #KisanYojana"
        ),
        "tags": [
            ch_name, "Kisan bdlega", "Kisan Badlega", "Kheti Badi", "Aadhunik Kheti",
            "Smart Farming India", "Krishi Gyan", "Indian Agriculture", "Kisan Yojana",
            "Crop Protection", "Organic Farming India", "Hindi Farming Guide"
        ],
        "hashtags": ["#KisanBdlega", "#KhetiBadi", "#SmartFarming", "#IndianAgriculture"],
        "thumbnail_text": "किसान बदलेगा"
    }

    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return fallback

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    prompt = (
        f"You are the head YouTube strategist for the popular Indian farming channel '{ch_name}'.\n"
        f"Niche: Farming and Agriculture in India.\n"
        f"Topic: {topic}\n"
        f"Target Audience: {audience}\n"
        "Requirements:\n"
        "1. title: Eye-catching, click-worthy Hindi title for Indian farmers (under 90 chars). Include channel branding or farming hook.\n"
        "2. description: Detailed, informative Hindi description with intro, bullet points, call-to-action for 'Kisan bdlega', and hashtags.\n"
        "3. tags: Array of 20-30 high-ranking Hindi & English YouTube search tags related to Indian farming and this topic.\n"
        "4. hashtags: 3-5 relevant hashtags including #KisanBdlega.\n"
        "5. thumbnail_text: 2-4 punchy Hindi Devanagari words that farmers can read easily on mobile screens.\n"
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
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I)
        obj = json.loads(text)
        for k, v in fallback.items():
            obj.setdefault(k, v)
        return obj
    except Exception as exc:
        print(f"WARNING: Gemini metadata generation failed; using fallback: {exc}")
        return fallback

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--settings", default="config/settings.json")
    ap.add_argument("--output", default="output")
    ap.add_argument("--custom-topic", default="", help="Custom user-specified topic")
    ap.add_argument("--custom-title", default="", help="Custom YouTube title")
    ap.add_argument("--custom-description", default="", help="Custom YouTube description")
    ap.add_argument("--custom-tags", default="", help="Custom YouTube tags (comma-separated)")
    ap.add_argument("--ideas-file", default="config/ideas.csv", help="Path to ideas CSV file (optional)")
    ap.add_argument("--disable-csv-ideas", action="store_true", help="Disable picking ideas from CSV")
    args = ap.parse_args()

    channel_info = load_context()
    settings = json.loads((ROOT / args.settings).read_text(encoding="utf-8"))

    ch_name = channel_info.get("channel_name", "Kisan bdlega")
    ideas_csv = ROOT / args.ideas_file

    if args.custom_topic.strip():
        topic = args.custom_topic.strip()
        print(f"\n[CUSTOM MODE - {ch_name}] Topic: '{topic}'")
        # Mark as used in CSV if found to prevent duplication
        if not args.disable_csv_ideas and ideas_csv.exists():
            if mark_idea_used(ideas_csv, topic):
                print(f"[IDEAS CSV] Marked topic '{topic}' as 'used' in {args.ideas_file}")
        topics = [{
            "title": topic,
            "url": "https://krishijagran.com/",
            "publisher": f"{ch_name} (Custom Agriculture Topic)",
            "published": datetime.now(timezone.utc).isoformat(),
            "summary": f"Complete guide and actionable advice on {topic} for Indian farmers."
        }]
    else:
        # Check if CSV ideas file has any pending topics
        csv_topic = None
        if not args.disable_csv_ideas and ideas_csv.exists():
            csv_topic = pick_and_mark_next_idea(ideas_csv)

        if csv_topic:
            topic = csv_topic
            print(f"\n[AUTO MODE - {ch_name}] Picked next pending topic from CSV: '{topic}'")
            print(f"[IDEAS CSV] Marked as 'used' in {args.ideas_file} to avoid duplication.")
            topics = [{
                "title": topic,
                "url": "https://krishijagran.com/",
                "publisher": f"{ch_name} (Curated Idea from CSV)",
                "published": datetime.now(timezone.utc).isoformat(),
                "summary": f"Complete guide and actionable advice on {topic} for Indian farmers."
            }]
        else:
            print(f"\n[AUTO MODE - {ch_name}] No pending ideas found in CSV (or CSV missing).")
            print(f"[AUTO MODE - {ch_name}] Searching trending farming & agriculture topics in India via RSS & Wikipedia...")
            topics = discover_topics(settings)
            if not topics:
                raise SystemExit("No research results were found. Check network/RSS or add sources manually.")
            topic = topics[0]["title"]

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out = ROOT / args.output / f"research-{stamp}"
    out.mkdir(parents=True, exist_ok=True)

    metadata = generate_metadata(topic, settings.get("target_audience", channel_info.get("target_audience")), channel_info)

    # Apply manual custom overrides if specified
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
        f"- [{x['title']}]({x['url']}) — {x.get('publisher','')} | {x.get('published','')}\n  - विवरण: {x.get('summary','')}"
        for x in topics
    )
    brief = f"""# Research Brief: {ch_name}

- चैनल (Channel): {ch_name}
- क्षेत्र (Niche): {channel_info.get('niche', 'Farming and Agriculture')}
- देश (Country/Location): {channel_info.get('country', 'India')}
- भाषा (Language): {channel_info.get('language', 'Hindi')}
- दर्शक (Target Audience): {channel_info.get('target_audience')}
- विज़न (Vision): {channel_info.get('channel_vision')}
- समय (Duration): {settings.get('duration_min_minutes', 4)}–{settings.get('duration_max_minutes', 8)} मिनट

## मुख्य विषय (Main Topic)
{topic}

## विषय का सार व उद्देश्य
यह रिसर्च ब्रीफ भारतीय किसानों के लिए तैयार किया गया है।
इस वीडियो का उद्देश्य किसानों को सरल और व्यावहारिक हिंदी में सही मार्गदर्शन देना है ताकि वे अपनी खेती से अधिकतम मुनाफा कमा सकें।
प्रमुख बिंदु:
1. विषय की बुनियादी और जरूरी जानकारी।
2. आधुनिक तकनीक, उन्नत किस्म, या सरकारी योजना का किसानों को सीधा फायदा।
3. सावधानियां, सही समय और लागत-मुनाफे का विश्लेषण।
4. किसानों के लिए उपयोगी निष्कर्ष (Actionable Takeaway)।

## संदर्भ व स्रोत (Sources)
{source_lines}
"""
    (out / "research_brief.md").write_text(brief, encoding="utf-8")

    prompt = f"""Create an engaging Hindi Video Overview for Indian farmers and rural youth.
Channel: {ch_name}
Topic: {topic}
Language: Natural, conversational, respectful Hindi.
Style: Practical and educational farming explainer.
Focus on practical benefits, modern techniques, cost-profit analysis, and actionable advice for farmers.
"""
    (out / "notebooklm_prompt.txt").write_text(prompt, encoding="utf-8")
    print(f"Research pack created: {out}")
    print(f"Topic: {topic}")

if __name__ == "__main__":
    main()
