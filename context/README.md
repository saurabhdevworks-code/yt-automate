# 📂 Channel Context & Creative Hub (`context/`)

Ye folder aapke YouTube channel ki saari guidelines, templates aur creative assets ka **Single Source of Truth** hai!

Aap bina kisi code ko chhede, sirf is folder ki files edit karke poore automation ko control kar sakte hain:

---

## 📁 Folder Structure & Usage:

```text
context/
├── yt_rules.json               <- Title, Description aur Tags ke exact rules
├── topics.csv                  <- Video Ideas ki queue (Status: pending / used)
├── channel_context.json        <- Channel ka niche, language, target audience
├── thumbnail_templates/        <- 3 se 5 customizable HTML thumbnail templates
│   ├── template1_scheme.html   <- सरकारी योजना & सब्सिडी (Solar Pump, PM Kisan)
│   ├── template2_profit.html   <- कमाई & बंपर मुनाफा (Polyhouse, Vermicompost)
│   ├── template3_tech.html     <- आधुनिक तकनीक & स्मार्ट खेती (Drone, Drip)
│   ├── template4_split.html    <- पुराना तरीका vs नया तरीका (Comparison)
│   └── template5_bold.html     <- Big Bold High-Impact Minimalist
└── images/
    ├── watermark/              <- Apna watermark.png yahan rakhein
    └── thumbnails/             <- Custom backgrounds ya reference assets
```

---

### 1. `yt_rules.json` (YouTube SEO Rules)
- Yahan aap Title ki length, Description ka structure, disclaimer aur default tags/hashtags define karte hain.
- Gemini AI inhi rules ko padhkar 100% compliant titles aur descriptions generate karta hai.

### 2. `topics.csv` (Video Ideas Queue)
- Column format: `id,topic,status,used_at,notes`
- Naye ideas add karne ke liye baseline row add karein aur `status` ko `pending` rakhein.
- Pipeline video banne ke baad status ko automatically `used` mark kar deti hai.

### 3. `thumbnail_templates/` (Custom HTML Templates)
- Aap kisi bhi template ka HTML/CSS open karke design, colors, font sizes change kar sakte hain.
- Pipeline in templates ko Headless Chrome se 1280x720 pixel-perfect JPEG me convert karti hai.

### 4. `images/watermark/`
- Bas apna logo `watermark.png` naam se yahan paste kar dein.
- Video Processor automatically use video ke corner me fit kar dega.
