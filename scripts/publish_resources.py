#!/usr/bin/env python3
"""把资源写入复刻站（幂等）。

流程：
  1. 读 items.json（title / category / subcategory / tags / desc / size / url）
  2. 若给了 --shares batch_share_results.json（quark_batch_run.py 的输出），
     用其中的永久分享链接；否则原样用 items 里的 url（仅测试）
  3. 按原始 url 的 md5 前 12 位做幂等 id，合并进 data/resources.json
  4. 重建 sitemap
  5. --push 时 git commit + push

用法：
  python3 scripts/publish_resources.py --items items.json --shares batch_share_results.json --push
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def rid(url: str) -> str:
    return hashlib.md5(url.encode("utf-8")).hexdigest()[:12]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", required=True)
    ap.add_argument("--shares", help="quark_batch_run.py 输出文件")
    ap.add_argument("--push", action="store_true")
    a = ap.parse_args()

    items = json.load(open(a.items, encoding="utf-8"))
    if isinstance(items, dict):
        items = items.get("items", [])

    share_map = {}
    if a.shares:
        sh = json.load(open(a.shares, encoding="utf-8"))
        for r in sh.get("share_results", sh if isinstance(sh, list) else []):
            src = r.get("url") or r.get("source_url")
            dst = r.get("share_url") or r.get("shareUrl")
            if src and dst:
                share_map[src] = r

    db_path = os.path.join(ROOT, "data/resources.json")
    db = json.load(open(db_path, encoding="utf-8"))
    existing = {it["id"]: it for it in db.get("items", [])}

    added = 0
    for it in items:
        src = it.get("url") or it.get("sourceUrl")
        if not src:
            print(f"[skip] 无原始链接: {it.get('title')}", file=sys.stderr)
            continue
        rid_ = rid(src)
        if rid_ in existing:
            print(f"[skip] 已存在 {rid_} {it.get('title')}")
            continue
        sr = share_map.get(src, {})
        entry = {
            "id": rid_,
            "title": it.get("title", ""),
            "category": it.get("category", "study"),
            "subcategory": it.get("subcategory", ""),
            "tags": it.get("tags", []),
            "size": it.get("size", ""),
            "formats": it.get("formats", ""),
            "desc": it.get("desc", ""),
            "shareUrl": sr.get("share_url") or sr.get("shareUrl") or "",
            "pwd": sr.get("pwd") or it.get("pwd", ""),
            "sourceUrl": src,
            "updatedAt": date.today().isoformat(),
        }
        existing[rid_] = entry
        added += 1
        print(f"[add] {rid_} {entry['title']}")

    db["items"] = list(existing.values())
    db["count"] = len(db["items"])
    db["updatedAt"] = date.today().isoformat()
    json.dump(db, open(db_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[db] 新增 {added} 条，共 {db['count']} 条")

    subprocess.run([sys.executable, os.path.join(ROOT, "scripts/build_sitemap.py")], check=True)

    if a.push:
        subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
        subprocess.run(["git", "commit", "-m", f"data: 新增 {added} 条资源 ({date.today()})"],
                       cwd=ROOT, check=True)
        subprocess.run(["git", "push"], cwd=ROOT, check=True)
        print("[git] pushed")


if __name__ == "__main__":
    main()
