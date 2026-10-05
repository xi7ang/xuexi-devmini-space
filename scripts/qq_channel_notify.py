#!/usr/bin/env python3
"""把 xuexi 资源逐条发布到腾讯频道（QQ 频道）「考公考试办公资料」（频道号 pd37080799）。

一条资源 = 一条频道帖子。帖子含 标题 / 简介 / 分类方向 / 标签 / 站点详情页链接。
按资源 id 幂等（状态存仓库外的持久目录，见 scripts/state_store.py）。
发帖走 tencent-channel-cli feed publish-feed（以管理员身份，普通用户模式需要 guild-id + channel-id）。

注意：用户可见的**频道号**（pd37080799）不是 guild_id，只是展示层标识。
真实 guild_id 由 `tencent-channel-cli manage get-my-join-guild-info` 查得；版块 ID 由
`tencent-channel-cli manage get-guild-channel-list --guild-id <ID>` 查得。二者配在
credentials/quark-xuexi-publisher.env 的 XUEXI_QQ_GUILD_ID / XUEXI_QQ_CHANNEL_ID。

用法:
  python3 qq_channel_notify.py --date 2026-10-04
  python3 qq_channel_notify.py --ids a1,b2 --limit 1
  python3 qq_channel_notify.py --force        # 忽略幂等，重发
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
XUEXI_ENV = Path("/root/.openclaw/credentials/quark-xuexi-publisher.env")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import state_store  # noqa: E402

STATE_NAME = ".qq_channel_state_items.json"
SITE = "https://xuexi.devmini.space"
CLI = "tencent-channel-cli"

# 兜底默认（实际以 env 为准）：考公考试办公资料
DEFAULT_GUILD_ID = "11015291791075810"
DEFAULT_CHANNEL_ID = "743606659"

# 「posting」占位超过此时长（秒）视为僵死，允许重试
CLAIM_TTL = 600


def _already_done(prev: dict) -> bool:
    """幂等判据：该资源是否已被（本次或其他实例）处理过。

    ok   → 已发成功，跳过；
    posting 且未超 CLAIM_TTL → 有实例正在发，跳过（防并发重发）；
    超时或缺失 → 可发。
    """
    s = (prev or {}).get("status")
    if s == "ok":
        return True
    if s == "posting":
        try:
            return (time.time() - float((prev or {}).get("epoch", 0))) < CLAIM_TTL
        except Exception:
            return True
    return False


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


def cfg(key: str, default: str) -> str:
    v = os.environ.get(key, "").strip() or read_env_file(XUEXI_ENV).get(key, "").strip()
    if not v:
        # 兜底默认值与真实频道容易漂移，回退时大声提醒
        print(f"⚠ {key} 未配置，回退到内置默认值 {default}（请写进 {XUEXI_ENV}）", file=sys.stderr)
        return default
    return v


def tax_names() -> tuple[dict, dict]:
    try:
        d = json.load(open(ROOT / "data/taxonomy.json", encoding="utf-8"))
    except Exception:
        return {}, {}
    cats, subs = {}, {}
    for slug, c in d.items():
        cats[slug] = c.get("name", slug)
        for s in c.get("subs", []):
            subs[s.get("slug")] = s.get("name", s.get("slug"))
    return cats, subs


def build_content(it: dict, cats: dict, subs: dict) -> str:
    parts = [f"📚 《{it.get('title', '')}》", ""]
    if it.get("desc"):
        parts += [it["desc"], ""]
    cat = cats.get(it.get("category"), it.get("category", ""))
    sub = subs.get(it.get("subcategory"), "")
    line = f"分类：{cat}" + (f" · {sub}" if sub else "")
    parts.append(line)
    tags = it.get("tags") or []
    if tags:
        parts.append("标签：" + " ".join("#" + str(t).replace(" ", "") for t in tags[:6]))
    if it.get("size"):
        parts.append(f"大小：{it['size']}")
    parts += ["", "👇 点开转存到自己的夸克网盘（永久有效）",
              f"{SITE}/resource.html?id={it['id']}"]
    return "\n".join(parts)


def publish(guild_id: str, channel_id: str, title: str, content: str) -> dict:
    """发布一条帖子，返回 {ok, feed_id, share_url, err}。"""
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as fh:
        fh.write(content)
        tmp = fh.name
    try:
        proc = subprocess.run(
            [CLI, "feed", "publish-feed",
             "--guild-id", str(guild_id), "--channel-id", str(channel_id),
             "--title", title[:100], "--content-file", tmp, "--json"],
            capture_output=True, text=True, timeout=120)
        raw = (proc.stdout or "").strip() or (proc.stderr or "").strip()
        # 频率限制（retCode 153）：sleep 70s 后原样重试一次
        if raw.lstrip().startswith("{") is False and "153" in raw:
            time.sleep(70)
            proc = subprocess.run(
                [CLI, "feed", "publish-feed",
                 "--guild-id", str(guild_id), "--channel-id", str(channel_id),
                 "--title", title[:100], "--content-file", tmp, "--json"],
                capture_output=True, text=True, timeout=120)
            raw = (proc.stdout or "").strip() or (proc.stderr or "").strip()
        try:
            d = json.loads(raw)
        except Exception:
            return {"ok": False, "err": f"非 JSON 输出: {raw[:160]}"}
        if d.get("success") and isinstance(d.get("data"), dict) and d["data"].get("feed_id"):
            return {"ok": True, "feed_id": d["data"]["feed_id"],
                    "share_url": d["data"].get("share_url", "")}
        if re.search(r'"retCode"\s*:\s*153', raw) or "153" in raw:
            return {"ok": False, "err": "接口频率限制（153），请稍后再试"}
        return {"ok": False, "err": raw[:200]}
    finally:
        try:
            os.unlink(tmp)
        except Exception:
            pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--ids")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--sleep", type=float, default=2.0, help="每条之间的间隔秒数（默认 2）")
    a = ap.parse_args()

    guild_id = cfg("XUEXI_QQ_GUILD_ID", DEFAULT_GUILD_ID)
    channel_id = cfg("XUEXI_QQ_CHANNEL_ID", DEFAULT_CHANNEL_ID)

    items = json.load(open(ROOT / "data/resources.json", encoding="utf-8"))["items"]
    if a.ids:
        want = {x.strip() for x in a.ids.split(",") if x.strip()}
        items = [i for i in items if i["id"] in want]
    elif a.date:
        items = [i for i in items if i.get("updatedAt") == a.date]
    if a.limit:
        items = items[: a.limit]

    # 闸一：单实例文件锁。并发/重复触发时只允许一个实例发帖，其余立即退出。
    lock_fh = open(state_store.state_dir() / ".qq_channel_notify.lock", "w")
    try:
        fcntl.flock(lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("已有另一个 qq_channel_notify 实例在运行，本次跳过（防重复发帖）")
        return 0

    cats, subs = tax_names()
    ok = fail = skip = 0
    for it in items:
        # 闸二：每条发帖前重读状态并占位，锁之外的重叠触发也不会重复发同一条
        st = state_store.load(STATE_NAME, {})
        if not a.force and _already_done(st.get(it["id"], {})):
            skip += 1
            continue
        st[it["id"]] = {"status": "posting", "epoch": time.time(),
                        "at": time.strftime("%Y-%m-%d %H:%M:%S")}
        state_store.save(STATE_NAME, st)
        title = it.get("title", "")
        res = publish(guild_id, channel_id, title, build_content(it, cats, subs))
        st = state_store.load(STATE_NAME, {})
        st[it["id"]] = {
            "status": "ok" if res["ok"] else "fail",
            "feed_id": res.get("feed_id", ""),
            "share_url": res.get("share_url", ""),
            "err": res.get("err", ""),
            "epoch": time.time(),
            "at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        state_store.save(STATE_NAME, st)
        print(f"[{'ok  ' if res['ok'] else 'FAIL'}] {title[:36]} | "
              f"{res.get('share_url') or res.get('err', '')}")
        ok += res["ok"]
        fail += (not res["ok"])
        time.sleep(max(0.0, a.sleep))
    print(f"\n成功 {ok} / 失败 {fail} / 跳过 {skip}（频道 {guild_id} · 版块 {channel_id}）")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
