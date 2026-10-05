#!/usr/bin/env python3
"""生成品牌资源 PNG：OG 分享图 1200×630 + 应用图标 64/180/512。
PIL 手绘中文（文泉驿正黑），配色取自网站 accent。
用法：python3 scripts/gen_brand_assets.py
"""
from __future__ import annotations
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "img"
CJK = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
C1, C2 = (255, 138, 76), (232, 86, 42)
WHITE = (255, 255, 255)
def f(sz): return ImageFont.truetype(CJK, sz, index=0)
def hgrad(w, h, c1=C1, c2=C2):
    img = Image.new("RGB", (w, h), c1)
    d = ImageDraw.Draw(img)
    for x in range(w):
        t = x / max(1, w - 1)
        d.line([(x, 0), (x, h)], fill=tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3)))
    return img
def book(d, cx, cy, sz):
    w, h = sz, sz * 0.76
    x0, y0 = cx - w/2, cy - h/2
    sp = max(2.0, sz * 0.055)
    nc = sz * 0.13
    d.polygon([(x0, y0+nc), (cx-sp, y0), (cx-sp, y0+h), (x0, y0+h-nc)], fill=WHITE)
    d.polygon([(cx+sp, y0), (x0+w, y0+nc), (x0+w, y0+h-nc), (cx+sp, y0+h)], fill=WHITE)
def ctext(d, txt, sz, cx, y, fill=WHITE):
    ft = f(sz)
    b = d.textbbox((0, 0), txt, font=ft)
    d.text((cx - (b[2]-b[0])/2 - b[0], y), txt, font=ft, fill=fill)

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    # ── OG 1200×630 ──
    img = hgrad(1200, 630); dr = ImageDraw.Draw(img)
    cx = 600
    book(dr, cx, 138, 96)
    ctext(dr, "学习资料站", 92, cx, 210)
    ctext(dr, "高考真题 · 中考真题 · 中小学资料 · 办公素材", 38, cx, 350)
    ctext(dr, "每日更新   一键转存夸克网盘   永久有效", 32, cx, 430, fill=(255, 240, 232))
    dr.line([(360, 500), (840, 500)], fill=WHITE, width=2)
    ctext(dr, "xuexi.devmini.space", 28, cx, 522, fill=(255, 235, 226))
    p = OUT / "og.png"; img.save(p, "PNG", optimize=True); print(f"OG 1200×630  {p.stat().st_size}B  {p}")
    # ── 图标 ──
    for s in (64, 180, 512):
        img = hgrad(s, s); dr = ImageDraw.Draw(img); book(dr, s/2, s/2, s * 0.52)
        p = OUT / f"icon-{s}.png"; img.save(p, "PNG", optimize=True); print(f"icon {s}×{s}  {p.stat().st_size}B  {p}")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())