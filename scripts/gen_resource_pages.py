#!/usr/bin/env python3
"""为每条资源预生成静态详情页 r/<id>.html。

为什么：本站是纯静态 MPA，详情页靠 JS 渲染 → 搜索引擎/分享抓取拿到的是泛标题。
每条资源一个静态页，head 里写死真实 title/description/canonical/og:*，正文仍由 app.js 复用
（<body data-page="resource" data-id="<id>">）。

关键技巧：<base href="/">。页面在 r/ 子目录下，靠它让页内的相对路径
（assets/…、data/…、category.html）仍按站点根解析 —— 于是无需改动 app.js 的任何路径。

幂等：同内容不重写；被删掉的资源会清理其静态页。
用法：python3 scripts/gen_resource_pages.py
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://xuexi.devmini.space"
OUT = ROOT / "r"

PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<base href="/">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} - 学习资料站</title>
<meta name="description" content="{desc}">
<meta name="robots" content="index,follow">
<link rel="canonical" href="{SITE}/r/{id}.html">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>📚</text></svg>">
<meta property="og:type" content="article">
<meta property="og:site_name" content="学习资料站">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{SITE}/r/{id}.html">
<link rel="stylesheet" href="assets/css/style.css">
{stats}
</head>
<body data-page="resource" data-id="{id}">
<header class="hd" id="site-header"></header>
<main id="main"><div class="wrap"><div class="empty">加载中…</div></div></main>
<footer class="ft" id="site-footer"></footer>
<script src="assets/js/app.js"></script>
</body>
</html>
"""


def esc(s: str) -> str:
    return html.escape(str(s or ""), quote=True)


def main() -> int:
    res = json.loads((ROOT / "data" / "resources.json").read_text(encoding="utf-8"))
    idx = (ROOT / "index.html").read_text(encoding="utf-8")
    # 统计脚本逐页一致（与首页相同的那一段）
    m = re.search(r'<script[^>]+src="https://stats\.[^"]+"[^>]*></script>', idx)
    stats = m.group(0) if m else ""
    items = [it for it in res.get("items", []) if not it.get("demo") and it.get("shareUrl")]

    OUT.mkdir(exist_ok=True)
    wrote, kept, ids = 0, 0, set()
    for it in items:
        rid = str(it.get("id") or "")
        if not rid:
            continue
        ids.add(rid)
        title = it.get("title") or "学习资料"
        desc = it.get("desc") or f"{title}｜夸克网盘转存，永久有效。"
        page = PAGE.format(title=esc(title), desc=esc(desc), id=esc(rid), SITE=SITE, stats=stats)
        p = OUT / f"{rid}.html"
        if p.exists() and p.read_text(encoding="utf-8") == page:
            kept += 1
            continue
        p.write_text(page, encoding="utf-8")
        wrote += 1

    # 清理已下架/已删资源的静态页（否则 sitemap 与页面会对不上）
    removed = 0
    for p in OUT.glob("*.html"):
        if p.stem not in ids:
            p.unlink()
            removed += 1

    print(f"[resource-pages] {len(items)} items → 新写 {wrote} / 未变 {kept} / 清理 {removed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())