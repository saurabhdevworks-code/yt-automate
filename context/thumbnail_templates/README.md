# AI Thumbnail Prompt Templates

These templates are used to generate full high-CTR YouTube thumbnails using AI image generation (Google Imagen 3 via Gemini API / Pollinations Flux).

## Available Templates
- `template1_scheme.txt`: Government Schemes, Subsidies, PM Kisan, Yojana.
- `template2_profit.txt`: High-Profit Cash Crops, Vermicompost, Polyhouse Farming.
- `template3_tech.txt`: Modern Technology, Smart Farming, Drones, Drip Irrigation.
- `template4_split.txt`: Split-Screen Before vs After / Traditional vs Modern comparison.
- `template5_bold.txt`: Breaking News, Urgent Alerts, High Emotion viral thumbnails.

## Dynamic Placeholders
You can use the following variables inside any prompt template:
- `{topic}`: The video topic (e.g., "ड्रिप सिंचाई तकनीक और सरकारी सब्सिडी")
- `{headline}` / `{title}`: Video title or headline
- `{highlight}`: Punchy high-CTR hook / benefit
- `{channel_name}`: Channel name (default: "Kisan bdlega")
- `{style_notes}`: Additional lighting or composition guidelines

## How to Add New Templates
Create a new file like `template6_organic.txt` or `template7_tractor.txt` in this folder and write your custom prompt. The generator will automatically detect and match it!
