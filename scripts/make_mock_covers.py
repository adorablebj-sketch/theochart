#!/usr/bin/env python3
"""개발용 가짜 표지 PNG를 만든다 (site/mock-covers/). 실데이터가 붙으면 알라딘 표지가 대신 들어온다.

출력: site/mock-covers/*.png, data/mock_covers.json (slug → cover 경로, 대표색)
"""
import hashlib
import json
import pathlib
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "site" / "mock-covers"
FONT = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
W, H = 400, 600

PALETTES = [
    ("#1F2A44", "#F4F1EA", "#D9A441"),
    ("#6B1F2A", "#F7EFE6", "#E0B27A"),
    ("#1E3D33", "#EFF5EF", "#9CC5A1"),
    ("#F1E9D6", "#2B2B2B", "#B5473B"),
    ("#2E2E2E", "#F5F5F0", "#E5C07B"),
    ("#3C4A6B", "#FFFFFF", "#F2C14E"),
    ("#7A5C3E", "#FBF6EE", "#E9D8B4"),
    ("#EAE2D6", "#1F2A44", "#1F2A44"),
    ("#0F3D5E", "#EAF2F8", "#F4A261"),
    ("#4A2C4A", "#F6EEF6", "#D4A5D4"),
    ("#8C2F39", "#FFF5F5", "#F2D1D1"),
    ("#F7F3EA", "#3A2F2F", "#7A9E7E"),
]

_font_cache = {}


def font(size, bold=True):
    key = (size, bold)
    if key in _font_cache:
        return _font_cache[key]
    want = "Bold" if bold else "Regular"
    found = 0
    for idx in range(20):
        try:
            f = ImageFont.truetype(FONT, size, index=idx)
        except (OSError, IndexError):
            break
        if f.getname()[1] == want:
            found = idx
            break
    _font_cache[key] = ImageFont.truetype(FONT, size, index=found)
    return _font_cache[key]


def wrap(title, n):
    lines, cur = [], ""
    for w in title.split(" "):
        if len(w) > n:
            if cur:
                lines.append(cur)
                cur = ""
            lines += [w[i:i + n] for i in range(0, len(w), n)]
            continue
        if len(cur) + len(w) + (1 if cur else 0) > n:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return lines


def text_block(d, lines, f, x, y, fill, align="left", gap=8):
    for ln in lines:
        bbox = d.textbbox((0, 0), ln, font=f)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        tx = x if align == "left" else x - w / 2
        d.text((tx, y), ln, font=f, fill=fill)
        y += h + gap
    return y


def make_cover(title, author, seed):
    h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    bg, fg, ac = PALETTES[h % len(PALETTES)]
    variant = (h >> 8) % 4
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    size = 46 if len(title) <= 8 else (40 if len(title) <= 14 else 34)
    per = 6 if size >= 46 else (7 if size >= 40 else 9)
    lines = wrap(title, per)
    tf, af = font(size, True), font(20, False)
    authors = [author] if author else []
    if variant == 0:
        d.line([(60, 200), (W - 60, 200)], fill=ac, width=2)
        y = text_block(d, lines, tf, W / 2, 230, fg, "center")
        text_block(d, authors, af, W / 2, y + 14, fg, "center")
        d.ellipse([W / 2 - 6, H - 70, W / 2 + 6, H - 58], fill=ac)
    elif variant == 1:
        d.ellipse([W - 260, H - 260, W + 60, H + 60], fill=ac)
        y = text_block(d, lines, tf, 44, 70, fg)
        text_block(d, authors, af, 44, y + 10, fg)
    elif variant == 2:
        d.rectangle([0, 0, 56, H], fill=ac)
        y = text_block(d, lines, tf, 90, 250, fg)
        text_block(d, authors, af, 90, H - 90, fg)
    else:
        d.rectangle([18, 18, W - 18, H - 18], outline=fg, width=2)
        d.rectangle([28, 28, W - 28, H - 28], outline=fg, width=1)
        y = text_block(d, lines, tf, W / 2, 210, fg, "center")
        text_block(d, authors, af, W / 2, y + 16, fg, "center")
    return img, bg


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(ROOT / "scripts"))
    from make_mock import POOLS, slug

    books = {}
    for pool in POOLS.values():
        for title, author, _pub in pool:
            books[slug(title)] = (title, author if author != "?" else "")
    books["own-example-1"] = ("개혁교의학 워크북", "황병준")

    meta = {}
    for key, (title, author) in books.items():
        fname = hashlib.md5(key.encode()).hexdigest()[:10] + ".png"
        img, accent = make_cover(title, author, key)
        img.save(OUT / fname, optimize=True)
        meta[key] = {"cover": "mock-covers/" + fname, "accent": accent}
    (ROOT / "data" / "mock_covers.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"표지 {len(meta)}장 생성 → {OUT}")


if __name__ == "__main__":
    main()
