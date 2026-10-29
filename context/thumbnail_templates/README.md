# High-CTR YouTube Thumbnail Prompt Templates

These templates are used by `src/thumbnail.py` to generate ultra high-CTR, cinematic YouTube thumbnails using AI image generation (Google Imagen 3 via Gemini API / Pollinations Flux).

## Templates List
- **`template1.txt`**: **The Shocking Secret & Breakthrough Formula** (Shocked expressive farmer, game-changing discovery, high viral click-through rate).
- **`template2.txt`**: **The Bumper Profit & Wealth Formula** (Prosperous farmer, giant fresh harvest, wealth and abundance hook).
- **`template3.txt`**: **The Official Government Scheme & Subsidy Formula** (Authoritative, official certified documents with gold seal, trust hook).
- **`template4.txt`**: **The Dramatic Split-Screen Formula** (Before vs After / Old struggling farming vs Modern profitable farming).
- **`template5.txt`**: **The Smart Modern Tech & Future Farming Formula** (Smart tablet, precision drip irrigation, drone flying at sunset).

## Automatic Random Selection
On each automated run, `src/thumbnail.py` automatically picks a **random template** from `template1.txt` to `template5.txt` to keep the channel's video thumbnails fresh and diverse!

You can also force a specific template using:
```bash
python -m src.thumbnail --template template1
python -m src.thumbnail --template template2
```

## Available Variables
- `{topic}`: The video topic
- `{channel_name}`: "Kisan bdlega"
- `{headline}`: Title or punchline
- `{highlight}`: Catchy text hook
- `{style_notes}`: Contextual style details
