#!/usr/bin/env python3
"""data 写入校验：水位类字段该有值却没有，直接让构建失败。

背景（2026-10-24）：xuexi 曾有 152 条资源 addedAt 全空，公告任务靠「取最新公告日期」
回退推断才没崩；v 站也曾从未把 announcementModal.watermark 写进 site.json。
两次事故同一类病：消费者依赖的字段，生产者从来没写过。回退能兜一次，兜不住永远。

因此这里把「必须有值」的字段做成硬门禁：
  - resources[].addedAt   必填、ISO8601 到秒带时区、可解析、不在未来
  - announcementModal.watermark  已有公告时必须存在且可解析，且不得落后于最新一期已播报资源

用法：python3 scripts/validate_data.py
退出码：0 通过；2 校验失败（与 publish_resources.py 的硬失败口径一致）
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RES_FILE = ROOT / "data/resources.json"
SITE_FILE = ROOT / "data/site.json"

ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:[+-]\d{2}:\d{2}|Z)$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
VER_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-\d+$")
ID_RE = re.compile(r"^[0-9a-f]{12}$")
MAX_FUTURE = timedelta(days=1)

errors: list[str] = []
warns: list[str] = []


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def main() -> int:
    try:
        res_raw = json.loads(RES_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"❌ 缺失数据文件: {RES_FILE.relative_to(ROOT)}")
        return 2
    except json.JSONDecodeError as exc:
        print(f"❌ resources.json 不是合法 JSON: {exc}")
        return 2

    items = res_raw.get("items") if isinstance(res_raw, dict) else res_raw
    if not isinstance(items, list):
        print("❌ resources.json 结构异常：期望 {items: [...]} 或 [...]")
        return 2

    now = datetime.now(timezone.utc)
    seen_ids: set[str] = set()
    added_map: dict[str, str] = {}

    for i, r in enumerate(items):
        rid = str(r.get("id") or "")
        loc = f"资源[{i}]({rid or r.get('title') or '?'})"

        if not rid:
            errors.append(f"{loc} 缺 id")
        elif not ID_RE.match(rid):
            errors.append(f"{loc} id 必须是 md5 前 12 位小写十六进制: {rid}")
        elif rid in seen_ids:
            errors.append(f"{loc} id 重复: {rid}")
        seen_ids.add(rid)

        if not str(r.get("title") or "").strip():
            errors.append(f"{loc} 缺 title")

        added = r.get("addedAt")
        if not added:
            errors.append(f"{loc} 缺 addedAt（必填，ISO8601 到秒带时区）")
        elif not isinstance(added, str) or not ISO_RE.match(added):
            errors.append(f"{loc} addedAt 格式非法(需形如 2026-10-23T22:18:30+08:00): {added!r}")
        else:
            try:
                dt = parse_iso(added)
            except ValueError:
                errors.append(f"{loc} addedAt 无法解析: {added}")
            else:
                if dt > now + MAX_FUTURE:
                    errors.append(f"{loc} addedAt 在未来: {added}")
                added_map[rid] = added

        updated = r.get("updatedAt")
        if not updated:
            warns.append(f"{loc} 缺 updatedAt（建议与 addedAt 同为 ISO8601 到秒带时区）")
        elif not isinstance(updated, str) or not ISO_RE.match(updated):
            errors.append(f"{loc} updatedAt 格式非法: {updated!r}")

    if isinstance(res_raw, dict) and "count" in res_raw and res_raw["count"] != len(items):
        warns.append(f"resources.count({res_raw['count']}) 与实际条数({len(items)}) 不一致")

    try:
        site = json.loads(SITE_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append("缺失数据文件: data/site.json")
        site = {}
    except json.JSONDecodeError as exc:
        errors.append(f"site.json 不是合法 JSON: {exc}")
        site = {}

    am = site.get("announcementModal") if isinstance(site, dict) else None
    if not isinstance(am, dict):
        errors.append("site.json 缺 announcementModal")
    else:
        ann_items = am.get("items")
        if not isinstance(ann_items, list):
            errors.append("announcementModal.items 必须是数组")
            ann_items = []
        for i, it in enumerate(ann_items):
            if not DATE_RE.match(str(it.get("date") or "")):
                errors.append(f"公告[{i}] date 非法: {it.get('date')!r}")
            if not str(it.get("title") or "").strip():
                errors.append(f"公告[{i}] 缺 title")
        if ann_items:
            version = am.get("version")
            if not isinstance(version, str) or not VER_RE.match(version):
                errors.append(f"announcementModal.version 必须形如 YYYY-MM-DD-N: {version!r}")

            wm = am.get("watermark")
            if not wm:
                errors.append(
                    f"announcementModal.watermark 缺失（已有 {len(ann_items)} 条公告，"
                    "写入侧必须落盘该字段，不得依赖下游回退推断）"
                )
            elif not isinstance(wm, str) or not ISO_RE.match(wm):
                errors.append(f"announcementModal.watermark 格式非法: {wm!r}")
            else:
                try:
                    wm_dt = parse_iso(wm)
                except ValueError:
                    errors.append(f"announcementModal.watermark 无法解析: {wm}")
                else:
                    if wm_dt > now + MAX_FUTURE:
                        errors.append(f"announcementModal.watermark 在未来: {wm}")
                    latest = str(ann_items[0].get("content") or "")
                    ref_ids = re.findall(r"id=([0-9a-f]{12})", latest)
                    covered = [added_map[x] for x in ref_ids if x in added_map]
                    if covered:
                        max_added = max(covered)
                        if wm_dt < parse_iso(max_added):
                            errors.append(
                                f"announcementModal.watermark({wm}) 落后于最新一期已播报资源"
                                f"({max_added})，会导致同一批重复播报"
                            )
                    elif ref_ids:
                        warns.append(
                            f"最新一期公告引用的 {len(ref_ids)} 个 id 不在 resources.json 中，"
                            "水位覆盖性未校验"
                        )

    if warns:
        print("⚠️ 警告:\n  " + "\n  ".join(warns))
    if errors:
        print(f"❌ 校验失败 ({len(errors)} 项):\n  " + "\n  ".join(errors))
        return 2
    print(f"✅ 数据校验通过: {len(items)} 条资源, {len(am.get('items', [])) if isinstance(am, dict) else 0} 条公告")
    return 0


if __name__ == "__main__":
    sys.exit(main())
