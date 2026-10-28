# Assets Directory

This directory contains assets used by the automation pipeline:

- `images/`: Put your custom watermark image here as `assets/images/watermark.png` (or `.jpg`, `.webp`).
  - If `assets/images/watermark.*` is present, it will be added in place of the NotebookLM watermark.
  - If no image is present, the pipeline simply removes the NotebookLM watermark cleanly using FFmpeg delogo.
- `fonts/`: TTF fonts for YouTube thumbnail rendering.
