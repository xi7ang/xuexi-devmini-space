#!/usr/bin/env python3
"""把 xuexi 资源逐条推送到 TG 群（走 @GoodStudyDayUpBot，与 quark-mswnlz-publisher 同一套发送通道）。

一条资源 = 一条消息，内容含：资源标题 / 资源描述 / 资源标签 / 站点详情页链接。
按资源 id 幂等；链接一律用站点详情页，不暴露夸克原链。

用法:
  python3 tg_notify.py                      # 全部资源
  python3 tg_notify.py --date 2026-10-02    # 只推该日期更新的
  python3 tg_notify.py --ids a1,b2 --limit 1
  python3 tg_notify.py --force              # 忽略幂等
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MSWNLZ_SKILL = Path("/root/.openclaw/workspace/skills/quark-mswnlz-publisher")
XUEXI_ENV = Path("/root/.openclaw/credentials/quark-xuexi-publisher.env")
STATE = ROOT / ".tg_state_items.json"
SITE = "https://xuexi.devmini.space"

sys.path.insert(0, str(MSWNLZ_SKILL / "scripts"))
from telegram_album_notify import send_text_message  # noqa: E402

CATS = {"exam": "考试真题", "study": "中小学资料", "office": "办公素材"}


def read_env_file(p: Path) -> dict:
    out = {}
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    return out


def get_token() -> str:
    t = os.environ.get("XUEXI_TG_BOT_TOKEN", "").strip()
    if t:
        return t
    # 与 mswnlz 共用同一个 bot token（单一来源）
    t = read_env_file(MSWNLZ_SKILL / ".env").get("TELEGRAM_BOT_TOKEN", "").strip()
    if t:
        return t
    return read_env_file(XUEXI_ENV).get("XUEXI_TG_BOT_TOKEN", "").strip()


def get_targets() -> list[str]:
    raw = os.environ.get("XUEXI_TG_TARGETS", "").strip() or \
        read_env_file(XUEXI_ENV).get("XUEXI_TG_TARGETS", "").strip()
    return [x.strip() for x in raw.split(",") if x.strip()]


def esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_caption(it: dict) -> str:
    tags = "、".join(it.get("tags") or []) or "无"
    link = f"{SITE}/resource.html?id={it['id']}"
    parts = [
        f"<b>{esc(it['title'])}</b>",
        "",
        esc(it.get("desc") or ""),
        "",
        f"🏷 {esc(tags)}",
        f"🔗 <a href=\"{link}\">{link}</a>",
    ]
    return "\n".join(parts)[:1000]


def load_state() -> dict:
    try:
        return json.load(open(STATE, encoding="utf-8"))
    except Exception:
        return {}


def save_state(s: dict) -> None:
    json.dump(s, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--ids")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    token = get_token()
    targets = get_targets()
    if not token:
        print("✗ 未取到 TG bot token", file=sys.stderr)
        return 2
    if not targets:
        print("✗ 未配置目标群", file=sys.stderr)
        return 2

    items = json.load(open(ROOT / "data/resources.json", encoding="utf-8"))["items"]
    if a.ids:
        want = {x.strip() for x in a.ids.split(",") if x.strip()}
        items = [i for i in items if i["id"] in want]
    elif a.date:
        items = [i for i in items if i.get("updatedAt") == a.date]
    if a.limit:
        items = items[: a.limit]

    st = load_state()
    ok = fail = skip = 0
    for it in items:
        if not a.force and st.get(it["id"]) == "ok":
            skip += 1
            continue
        caption = build_caption(it)
        sent = []
        for cid in targets:
            try:
                r = send_text_message(bot_token=token, chat_id=cid, text=caption,
                                      parse_mode="HTML")
                sent.append(f"{cid}:{'ok' if r.ok else 'fail'}")
            except Exception as e:  # noqa: BLE001
                sent.append(f"{cid}:ERR {str(e)[:80]}")
        good = all("ok" in s for s in sent)
        st[it["id"]] = "ok" if good else ";".join(sent)
        print(f"[{'ok  ' if good else 'FAIL'}] {it['title'][:36]} | {' '.join(sent)}")
        ok += 1 if good else 0
        fail += 0 if good else 1
    save_state(st)
    print(f"\n成功 {ok} / 失败 {fail} / 跳过 {skip}（目标 {len(targets)} 个）")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
