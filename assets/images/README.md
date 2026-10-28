# Custom Watermark Image Directory (`assets/images`)

Place your custom watermark or logo image in this folder with the name `watermark`:
- `watermark.png`
- `watermark.jpg` / `watermark.jpeg`
- `watermark.webp`

### Behavior:
1. **If an image exists here** (e.g. `assets/images/watermark.png`):
   The pipeline removes the NotebookLM watermark and overlays this custom image in its place.
2. **If no image exists here**:
   The pipeline simply removes the NotebookLM watermark cleanly using FFmpeg `delogo` without adding any replacement image.
