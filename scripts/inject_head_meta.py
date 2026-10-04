#!/usr/bin/env python3
"""给所有 *.html 的 <head> 维护品牌片段（幂等；重复跑只更新变化的部分）。

站点没有构建期 head 注入（纯静态手写 HTML），所以用这个脚本兜底：
- favicon / apple-touch-icon：指向 assets/img/*.png，带**内容哈希**版本号
- og:image（绝对 URL，带内容哈希）/ og:image:width/height / twitter:card

为什么要带内容哈希：图片路径是固定名，Cloudflare 会把「文件还没部署时探到的 404」
按 max-age=14400 缓存 4 小时（实测 cf-cache-status: HIT + age），届时 favicon 与 OG 预览全挂。
带上内容哈希 → URL 一变就是新缓存键，立即生效（与 scripts/stamp_assets.py 同一套思路）。

用法：python3 scripts/inject_head_meta.py
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://xuexi.devmini.space"
MARK = "<!-- brand-head -->"

FAVICON_RE = re.compile(r'<link rel="icon"[^>]*>\s*')
BLOCK_RE = re.compile(re.escape(MARK) + r".*?(?=</head>)", re.S)
SITE_META = ('<meta property="og:type" content="website">\n'
             '<meta property="og:site_name" content="学习资料站">\n')


def img_ver(name: str) -> str:
    p = ROOT / "assets" / "img" / name
    return hashlib.sha256(p.read_bytes()).hexdigest()[:8] if p.exists() else "0"


def build_block() -> str:
    v64, v180, vog = img_ver("icon-64.png"), img_ver("icon-180.png"), img_ver("og.png")
    return f"""{MARK}
<link rel="icon" type="image/png" sizes="64x64" href="assets/img/icon-64.png?v={v64}">
<link rel="apple-touch-icon" sizes="180x180" href="assets/img/icon-180.png?v={v180}">
<meta property="og:image" content="{SITE}/assets/img/og.png?v={vog}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
"""


def main() -> int:
    block = build_block()
    changed = []
    for p in sorted(ROOT.glob("*.html")):
        t = orig = p.read_text(encoding="utf-8")
        if "</head>" not in t:
            continue
        if MARK in t:
            t = BLOCK_RE.sub(block, t, count=1)
        else:
            t = FAVICON_RE.sub("", t)
            extra = "" if 'property="og:site_name"' in t else SITE_META
            t = t.replace("</head>", extra + block + "</head>", 1)
        if t != orig:
            p.write_text(t, encoding="utf-8")
            changed.append(p.name)
    print("updated:", ", ".join(changed) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
