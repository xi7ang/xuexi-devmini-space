#!/usr/bin/env python3
"""按需重建 sitemap.xml / robots.txt —— 数据一变就重跑，不用整站预生成。"""
import json
import os
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.environ.get("SITE_URL", "https://xuexi.devmini.space").rstrip("/")


def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return json.load(f)


def main():
    res = load("data/resources.json")
    tax = load("data/taxonomy.json")
    today = date.today().isoformat()
    urls = [("/", "1.0", "daily"), ("/about.html", "0.3", "monthly"),
            ("/disclaimer.html", "0.3", "yearly")]

    for slug in tax:
        urls.append((f"/category.html?c={slug}", "0.8", "daily"))
        for sub in tax[slug].get("subs", []):
            urls.append((f"/category.html?c={slug}&s={sub['slug']}", "0.6", "daily"))

    for it in res.get("items", []):
        if it.get("demo") or not it.get("shareUrl"):
            continue
        urls.append((f"/resource.html?id={it['id']}", "0.9", "weekly"))

    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path, pri, freq in urls:
        lines.append(f"  <url><loc>{SITE}{path}</loc>"
                     f"<lastmod>{res.get('updatedAt', today)}</lastmod>"
                     f"<changefreq>{freq}</changefreq><priority>{pri}</priority></url>")
    lines.append("</urlset>")

    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    with open(os.path.join(ROOT, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n")

    print(f"[sitemap] {len(urls)} urls -> sitemap.xml / robots.txt")


if __name__ == "__main__":
    main()
