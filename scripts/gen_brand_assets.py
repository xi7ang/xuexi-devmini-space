#!/usr/bin/env python3
"""生成品牌资产（PNG）：OG 分享图 + 应用图标。

为什么用 PIL 手绘而不是 AI 生图：图上的中文文案要精确，AI 生图会把字写歪。
配色与站内一致（--accent #ff6b35 / --accent-d #e8562a）。
字体用系统自带的文泉驿正黑（CJK）；不用 emoji（PIL 对彩色 emoji 位图字体支持不稳）。

用法：python3 scripts/gen_brand_assets.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "img"
CJK = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"

C1 = (255, 138, 76)   # 亮橙
C2 = (232, 86, 42)    # 深橙
WHITE = (255, 255, 255)


def font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(CJK, size, index=0)


def hgrad(w: int, h: int, c1=C1, c2=C2) -> Image.Image:
    img = Image.new("RGB", (w, h), c1)
    d = ImageDraw.Draw(img)
    for x in range(w):
        t = x / max(1, w - 1)
        d.line([(x, 0), (x, h)], fill=tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3)))
    return img


def draw_book(d: ImageDraw.ImageDraw, cx: float, cy: float, size: float, color=WHITE) -> None:
    """简单开卷书图形：左右两页 + 中缝留白。"""
    w, h = size, size * 0.76
    x0, y0 = cx - w / 2, cy - h / 2
    spine = max(2.0, size * 0.055)
    notch = size * 0.13
    d.polygon([(x0, y0 + notch), (cx - spine, y0), (cx - spine, y0 + h), (x0, y0 + h - notch)], fill=color)
    d.polygon([(cx + spine, y0), (x0 + w, y0 + notch), (x0 + w, y0 + h - notch), (cx + spine, y0 + h)], fill=color)


def centered(d: ImageDraw.ImageDraw, text: str, f: ImageFont.FreeTypeFont, cx: float, y: float, fill=WHITE) -> None:
    box = d.textbbox((0, 0), text, font=f)
    d.text((cx - (box[2] - box[0]) / 2 - box[0], y), text, font=f, fill=fill)


def make_og() -> Path:
    W, H = 1200, 630
    img = hgrad(W, H)
    d = ImageDraw.Draw(img)
    cx = W / 2
    draw_book(d, cx, 138, 96)
    centered(d, "学习资料站", font(92), cx, 210)
    centered(d, "高考真题 · 中考真题 · 中小学资料 · 办公素材", font(38), cx, 350)
    centered(d, "每日更新   一键转存夸克网盘   永久有效", font(32), cx, 430, fill=(255, 240, 232))
    # 底部细线
    d.line([(W * 0.30, 500), (W * 0.70, 500)], fill=(255, 255, 255), width=2)
    centered(d, "xuexi.devmini.space", font(28), cx, 522, fill=(255, 235, 226))
    p = OUT / "og.png"
    img.save(p, "PNG", optimize=True)
    return p


def make_icon(size: int) -> Path:
    img = hgrad(size, size)
    d = ImageDraw.Draw(img)
    draw_book(d, size / 2, size / 2, size * 0.52)
    p = OUT / f"icon-{size}.png"
    img.save(p, "PNG", optimize=True)
    return p


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for p in [make_og(), make_icon(64), make_icon(180), make_icon(512)]:
        print(f"wrote {p.relative_to(ROOT)} ({p.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
