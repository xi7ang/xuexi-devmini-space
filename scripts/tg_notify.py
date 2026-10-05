#!/usr/bin/env python3
"""把 xuexi 资源逐条推送到 TG 群（走 @GoodStudyDayUpBot，与 quark-mswnlz-publisher 同一套通道）。

一条资源 = 一条消息。发送前先向 Bot 后端注册资源拿 start_link，
消息里的「获取资源」做成指向 start_link 的超链接（点击 → 私聊 bot 触发资源交付），
与 mswnlz 的 caption 格式一致。

用法:
  python3 tg_notify.py --date 2026-10-02
  python3 tg_notify.py --ids a1,b2 --limit 1
  python3 tg_notify.py --force            # 忽略幂等，重发
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MSWNLZ_SKILL = Path("/root/.openclaw/workspace/skills/quark-mswnlz-publisher")
XUEXI_ENV = Path("/root/.openclaw/credentials/quark-xuexi-publisher.env")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import state_store  # noqa: E402

# 幂等状态存在仓库外的持久目录（见 scripts/state_store.py），不进内容仓库
STATE = state_store.state_path(".tg_state_items.json")
SITE = "https://xuexi.devmini.space"
BOT_API_URL = "https://goodstudydayupbot-telegram-bot.wsheng-980210.workers.dev"

sys.path.insert(0, str(MSWNLZ_SKILL / "scripts"))
from telegram_album_notify import send_text_message  # noqa: E402

CATS = {"exam": "考试真题", "study": "中小学资料", "office": "办公素材"}
_start_link_cache: dict[str, str] = {}


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
    # 单一来源：优先 xuexi 自己的 env（XUEXI_ENV 里的 XUEXI_TG_BOT_TOKEN）。
    # mswnlz 的 .env 只作**已废弃**的兜底：一旦走到那里就告警，提醒把 token 迁到本技能 env。
    token = os.environ.get("XUEXI_TG_BOT_TOKEN", "").strip() or \
        read_env_file(XUEXI_ENV).get("XUEXI_TG_BOT_TOKEN", "").strip()
    if token:
        return token
    legacy = read_env_file(MSWNLZ_SKILL / ".env").get("TELEGRAM_BOT_TOKEN", "").strip()
    if legacy:
        print("⚠ TG token 来自 mswnlz 的 .env（已废弃路径），请迁到 XUEXI_ENV 的 XUEXI_TG_BOT_TOKEN", file=sys.stderr)
        return legacy
    return ""


def get_targets() -> list[str]:
    raw = os.environ.get("XUEXI_TG_TARGETS", "").strip() or \
        read_env_file(XUEXI_ENV).get("XUEXI_TG_TARGETS", "").strip()
    return [x.strip() for x in raw.split(",") if x.strip()]


def esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def register(item: dict) -> str | None:
    """向 Bot 后端注册资源，返回 start_link（形如 https://t.me/GoodStudyDayUpBot?start=N）。

    resource_link 用站点详情页；start_link 必须来自注册接口，绝不自己拼。
    """
    title = item["title"]
    if title in _start_link_cache:
        return _start_link_cache[title]
    payload = json.dumps({
        "resource_name": title[:80],
        "resource_description": (item.get("desc") or "")[:200],
        "resource_link": f"{SITE}/resource.html?id={item['id']}",
        "resource_hint": "",
    }, ensure_ascii=False).encode("utf-8")
    try:
        req = urllib.request.Request(
            f"{BOT_API_URL}/api/add", data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "xuexi-publisher/1.0"},
            method="POST")
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.loads(r.read().decode("utf-8"))
        link = (d.get("start_link") or "").strip()
        if link:
            _start_link_cache[title] = link
            return link
    except Exception as e:  # noqa: BLE001
        print(f"  ⚠ Bot 注册失败: {str(e)[:100]}", file=sys.stderr)
    return None


def build_caption(item: dict) -> str:
    title = item["title"]
    tags = " ".join("#" + t.replace(" ", "") for t in (item.get("tags") or [])[:3])
    head = f"<b>{esc(title)}</b>" + (f" {esc(tags)}" if tags else "")
    parts = [head]
    if item.get("desc"):
        parts += ["", esc(item["desc"])]
    start_link = register(item)
    if start_link:
        parts += ["", f'💾 获取资源：<a href="{start_link}">👉 点我获取{esc(title)}👈</a>']
    else:
        parts += ["", "💾 获取资源：请私聊 @GoodStudyDayUpBot 发送资源名称"]
    return "\n".join(parts)[:1000]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--ids")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--sleep", type=float, default=1.5,
                    help="每条之间的间隔秒数，防 Telegram 429 限流（默认 1.5）")
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

    st = _load()
    ok = fail = skip = 0
    for it in items:
        if not a.force and st.get(it["id"], {}).get("status") == "ok":
            skip += 1
            continue
        caption = build_caption(it)
        sent, mids = [], []
        for cid in targets:
            try:
                r = send_text_message(bot_token=token, chat_id=cid, text=caption, parse_mode="HTML")
                sent.append(f"{cid}:{'ok' if r.ok else 'fail'}")
                if r.message_id:
                    mids.append(r.message_id)
            except Exception as e:  # noqa: BLE001
                sent.append(f"{cid}:ERR {str(e)[:80]}")
        good = bool(sent) and all("ok" in s for s in sent)
        st[it["id"]] = {"status": "ok" if good else "fail", "result": ";".join(sent), "message_ids": mids}
        print(f"[{'ok  ' if good else 'FAIL'}] {it['title'][:36]} | {' '.join(sent)}")
        ok += good
        fail += (not good)
        time.sleep(max(0.0, a.sleep))
    _save(st)
    print(f"\n成功 {ok} / 失败 {fail} / 跳过 {skip}（目标 {len(targets)} 个）")
    return 0 if fail == 0 else 1


def _load() -> dict:
    try:
        d = json.load(open(STATE, encoding="utf-8"))
        # 兼容旧格式（值为字符串 "ok"）
        return {k: (v if isinstance(v, dict) else {"status": v}) for k, v in d.items()}
    except Exception:
        return {}


def _save(s: dict) -> None:
    json.dump(s, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    raise SystemExit(main())
