# High-CTR YouTube Thumbnail Prompt Templates

These templates are used by `src/thumbnail.py` to generate ultra high-CTR, cinematic YouTube thumbnails using AI image generation (Google Imagen 3 via Gemini API / Pollinations Flux).

## Templates List
- **`template1.txt`**: **Maroon Top + White Strip + 3 Cards Layout** (Full-width deep maroon top banner, white subheadline strip, full-frame background, 3 visual detail cards).
- **`template2.txt`**: **Yellow Headline Strip + Full Photo + Inset Layout** (Bright saturated yellow top banner with black Devanagari text + black keyword pill, cinematic photo + bottom-right inset).
- **`template3.txt`**: **Left Photo + Black Right Panel + Yellow Hook Layout** (55% dominant subject on left + 45% deep dark right text panel with stacked hierarchy & curved white arrow).
- **`template4.txt`**: **Dramatic Split-Screen Comparison Layout** (50/50 vertical split: Old struggling method vs Modern prosperous breakthrough method with center VS badge).
- **`template5.txt`**: **Breaking News Alert & Shocking Face Layout** (Red top alert badge + shocked expressive farmer pointing to main visual + bold Devanagari headline & yellow tag).

## Fields Replaced on Every Topic:
- `[TOPIC]` / `{topic}`: Current video topic
- `[MAIN HEADLINE]` / `{main_headline}`: Short punchy Devanagari headline
- `[SUBHEADLINE]` / `{subheadline}`: Supporting line / subheadline
- `[MAIN VISUAL]` / `[MAIN SUBJECT]`: Main photo subject
- `[VISUAL 1]`, `[VISUAL 2]`, `[VISUAL 3]`: Three detail visuals / examples
- `[KEY WORD]` / `[KEY PHRASE]`: Highlighted keyword
- `[NUMBER OR SHORT HOOK]`: Verified stat or punchy hook
- `[SETTING]`: Farm setting / background
- `[SECONDARY VISUAL]`: Inset photo detail
- `[IMPORTANT DETAIL]`: Detail pointed by arrow
- `[TOPIC LABEL]`: Alert badge label
- `[SUPPORTING TEXT]`: Benefit / trust line

## Automatic Random Selection
On each automated run, `src/thumbnail.py` automatically picks a **random template** from `template1.txt` to `template5.txt` to ensure visual diversity and high CTR across all uploads!
