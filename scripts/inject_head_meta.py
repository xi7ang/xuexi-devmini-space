#!/usr/bin/env python3
"""给所有 *.html 的 <head> 补品牌片段（幂等，重复跑不叠加）。

站点没有构建期 head 注入（纯静态手写 HTML），所以用这个脚本兜底：
- favicon：把 emoji data-URI 换成 assets/img/icon-64.png（品牌色图标）
- apple-touch-icon
- og:image / og:image:width/height / twitter:card
- og:type / og:site_name（缺才补）

用法：python3 scripts/inject_head_meta.py
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://xuexi.devmini.space"
MARK = "<!-- brand-head -->"

FAVICON_RE = re.compile(r'<link rel="icon"[^>]*>\s*')

BLOCK = f"""{MARK}
<link rel="icon" type="image/png" sizes="64x64" href="assets/img/icon-64.png">
<link rel="apple-touch-icon" sizes="180x180" href="assets/img/icon-180.png">
<meta property="og:image" content="{SITE}/assets/img/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
"""

SITE_META = ('<meta property="og:type" content="website">\n'
             '<meta property="og:site_name" content="学习资料站">\n')


def main() -> int:
    changed = []
    for p in sorted(ROOT.glob("*.html")):
        t = orig = p.read_text(encoding="utf-8")
        if "</head>" not in t:
            continue
        if MARK not in t:
            # favicon：emoji data-URI → 品牌 PNG
            t = FAVICON_RE.sub("", t, count=0)
            extra = "" if 'property="og:site_name"' in t else SITE_META
            t = t.replace("</head>", extra + BLOCK + "</head>", 1)
        if t != orig:
            p.write_text(t, encoding="utf-8")
            changed.append(p.name)
    print("updated:", ", ".join(changed) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
