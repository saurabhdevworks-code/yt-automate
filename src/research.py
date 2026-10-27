from datetime import datetime, timezone
import html, re
from urllib.parse import quote
import feedparser, requests

UA = "KisanBadlegaYouTubeResearch/1.0 (Agriculture Explainer Pipeline)"

def clean(text):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text or ""))).strip()

def rss_items(urls, per_feed=25):
    items, seen = [], set()
    for url in urls:
        try:
            parsed = feedparser.parse(url, agent=UA)
            for entry in parsed.entries[:per_feed]:
                link, title = getattr(entry, "link", ""), clean(getattr(entry, "title", ""))
                if not link or not title or link in seen:
                    continue
                seen.add(link)
                items.append({
                    "title": title, "url": link,
                    "summary": clean(getattr(entry, "summary", ""))[:1800],
                    "publisher": clean(getattr(parsed.feed, "title", url)),
                    "published": clean(getattr(entry, "published", "")),
                    "retrieved_at": datetime.now(timezone.utc).isoformat()
                })
        except Exception as exc:
            print(f"WARNING: RSS feed failed: {url}: {exc}")
    return items

def wikipedia_search(query, language="hi", limit=8):
    endpoint = f"https://{language}.wikipedia.org/w/api.php"
    try:
        response = requests.get(endpoint, params={
            "action": "query", "list": "search", "srsearch": query,
            "format": "json", "srlimit": limit
        }, headers={"User-Agent": UA}, timeout=20)
        response.raise_for_status()
        hits = response.json().get("query", {}).get("search", [])
        return [{
            "title": hit.get("title", ""),
            "url": f"https://{language}.wikipedia.org/wiki/{quote(hit.get('title','').replace(' ', '_'))}",
            "summary": clean(hit.get("snippet", "")),
            "publisher": f"Wikipedia ({language})",
            "published": "",
            "retrieved_at": datetime.now(timezone.utc).isoformat()
        } for hit in hits]
    except Exception as exc:
        print(f"WARNING: Wikipedia search failed ({query}): {exc}")
        return []

def discover_topics(settings):
    items = rss_items(settings.get("rss_feeds", []))

    # Wikipedia terms for Indian agriculture
    wiki_lang = settings.get("wikipedia_language", "hi")
    search_terms = settings.get("wikipedia_search_terms", ["भारत में कृषि", "जैविक खेती", "स्मार्ट फार्मिंग"])
    for term in search_terms[:3]:
        items += wikipedia_search(term, language=wiki_lang, limit=4)

    # Keywords to score and prioritize top farming topics
    keywords = [
        "किसान", "खेती", "कृषि", "फसल", "बीज", "खाद", "योजना", "सिंचाई", "उत्पादन",
        "kisan", "farming", "agriculture", "crop", "soil", "organic", "tractor", "yield"
    ]
    for item in items:
        body = f"{item['title']} {item['summary']}".lower()
        item["score"] = sum(2 for kw in keywords if kw.lower() in body) + (1 if item.get("published") else 0)
        item["score_note"] = "Relevance score based on farming and agriculture niche."

    items.sort(key=lambda item: (item["score"], bool(item.get("published"))), reverse=True)
    return items[:max(1, int(settings.get("max_topics", 10)))]
