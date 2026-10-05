#!/usr/bin/env python3
"""按需重建 sitemap.xml / robots.txt —— 数据一变就重跑，不用整站预生成。"""
import json
import os
from datetime import date
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.environ.get("SITE_URL", "https://xuexi.devmini.space").rstrip("/")


def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return json.load(f)


def main():
    res = load("data/resources.json")
    tax = load("data/taxonomy.json")
    today = date.today().isoformat()
    site_lm = res.get("updatedAt", today)
    urls = [("/", "1.0", "daily", site_lm), ("/about.html", "0.3", "monthly", site_lm),
            ("/disclaimer.html", "0.3", "yearly", site_lm)]

    for slug in tax:
        urls.append((f"/category.html?c={slug}", "0.8", "daily", site_lm))
        for sub in tax[slug].get("subs", []):
            urls.append((f"/category.html?c={slug}&s={sub['slug']}", "0.6", "daily", site_lm))

    for it in res.get("items", []):
        if it.get("demo") or not it.get("shareUrl"):
            continue
        # 详情页用各自的 updatedAt 做 lastmod（全站同一个值对 SEO 信号弱）
        # 详情页指向预生成的静态页（head 里写死真标题，爬虫可见）
        urls.append((f"/r/{it['id']}.html", "0.9", "weekly", it.get("updatedAt") or site_lm))

    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path, pri, freq, lastmod in urls:
        # <loc> 里必须做 XML 转义：分类链接带 ?c=x&s=y，裸 & 会让 sitemap 解析报
        # “EntityRef: expecting ';'”。saxutils.escape 把 & < > 转成实体。
        lines.append(f"  <url><loc>{escape(SITE + path)}</loc>"
                     f"<lastmod>{lastmod}</lastmod>"
                     f"<changefreq>{freq}</changefreq><priority>{pri}</priority></url>")
    lines.append("</urlset>")

    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    with open(os.path.join(ROOT, "robots.txt"), "w", encoding="utf-8") as f:
        # 收藏页是私密页，不该被收录
        f.write(f"User-agent: *\nAllow: /\nDisallow: /favorites.html\n\nSitemap: {SITE}/sitemap.xml\n")

    print(f"[sitemap] {len(urls)} urls -> sitemap.xml / robots.txt")


if __name__ == "__main__":
    main()
