#!/usr/bin/env python3
"""站内分享链接体检（只读，不改数据）。

背景：2026-11-08 发现 10-20 那批 7 条站内链接全部「分享地址已过期」——
根因是当时用手写脚本建分享时没传 expired_type，默认值是 2（短期），
而正式批处理脚本都写死 expired_type=1（永久）。错链在站内躺了 19 天没人发现。

这个脚本把「链接是否还活着」变成可执行的检查：
  1. 读 data/resources.json，逐条取 shareUrl
  2. 调夸克 sharepage/token，看返回 status
  3. 分类：ok / 失效 / 网络异常（网络异常不算失效，不误报）

用法：
  python3 scripts/check_links.py            # 体检 + 报告
  python3 scripts/check_links.py --json     # 机器可读
  python3 scripts/check_links.py --timeout 30

退出码：0 = 无失效链接；1 = 有失效链接；2 = 参数/环境错误。
"""
import argparse
import asyncio
import json
import os
import random
import sys
import time

import httpx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "data", "resources.json")

# 夸克分享页取 token 的端点（与 QuarkPanTool/quark.py 同款参数）
TOKEN_URL = "https://drive-pc.quark.cn/1/clouddrive/share/sharepage/token"
QUARK_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Referer": "https://pan.quark.cn/",
}


def _ts13() -> str:
    return str(int(time.time() * 1000))


def _params(pwd_id: str) -> dict:
    return {
        "pr": "ucpro",
        "fr": "pc",
        "uc_param_str": "",
        "__dt": random.randint(100, 9999),
        "__t": _ts13(),
        "pwd_id": pwd_id,
    }


def pwd_id_of(share_url: str) -> str:
    """从 https://pan.quark.cn/s/<pwd_id> 里取出 pwd_id。"""
    if "pan.quark.cn/s/" not in share_url:
        return ""
    tail = share_url.split("/s/", 1)[1]
    return tail.split("?")[0].split("-")[0].strip()


async def check_one(client: httpx.AsyncClient, pwd_id: str, timeout: float) -> tuple:
    """返回 (状态, 说明)。状态 ∈ ok / expired / net。"""
    for attempt in range(3):
        try:
            r = await client.post(
                TOKEN_URL,
                params=_params(pwd_id),
                json={"pwd_id": pwd_id, "passcode": ""},
                headers=QUARK_HEADERS,
                timeout=timeout,
            )
            j = r.json()
        except httpx.TransportError as exc:
            if attempt == 2:
                return "net", f"{type(exc).__name__}"
            await asyncio.sleep(2 + attempt * 2)
            continue
        except Exception as exc:  # noqa: BLE001
            return "net", f"{type(exc).__name__}: {exc}"

        if j.get("status") == 200 and j.get("data"):
            d = j["data"]
            return "ok", f"expired_type={d.get('expired_type')} expired_at={d.get('expired_at')}"
        msg = str(j.get("message") or j.get("code") or "no-data")
        if "过期" in msg or "expired" in msg.lower():
            return "expired", msg
        # 其它业务错误：算失效（链接确实打不开），但说明里保留原文
        return "expired", msg
    return "net", "retries exhausted"


async def main() -> int:
    ap = argparse.ArgumentParser(description="站内分享链接体检")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--timeout", type=float, default=30.0, help="单请求超时秒数")
    ap.add_argument("--concurrency", type=int, default=8, help="并发数")
    a = ap.parse_args()

    if not os.path.exists(DB_PATH):
        print(f"[fatal] 找不到 {DB_PATH}", file=sys.stderr)
        return 2
    db = json.load(open(DB_PATH, encoding="utf-8"))
    items = db.get("items", db) if isinstance(db, dict) else db

    targets = []
    for it in items:
        url = it.get("shareUrl") or ""
        pid = pwd_id_of(url)
        if pid:
            targets.append((it.get("id", ""), it.get("title", ""), url, pid))

    if not targets:
        print("[info] 没有需要体检的夸克分享")
        return 0

    sem = asyncio.Semaphore(max(1, a.concurrency))

    async def worker(t):
        iid, title, url, pid = t
        async with sem:
            async with httpx.AsyncClient(timeout=a.timeout) as client:
                state, detail = await check_one(client, pid, a.timeout)
        return {"id": iid, "title": title, "shareUrl": url, "state": state, "detail": detail}

    async with httpx.AsyncClient(timeout=a.timeout) as client:
        results = await asyncio.gather(*[worker(t) for t in targets])

    dead = [r for r in results if r["state"] == "expired"]
    net = [r for r in results if r["state"] == "net"]
    ok = [r for r in results if r["state"] == "ok"]

    if a.json:
        print(json.dumps({"checked": len(results), "ok": len(ok),
                          "expired": len(dead), "net_error": len(net),
                          "dead": dead, "net": net}, ensure_ascii=False, indent=2))
    else:
        print(f"体检 {len(results)} 条：有效 {len(ok)} · 失效 {len(dead)} · 网络异常 {len(net)}")
        for r in dead:
            print(f"  ❌ {r['id']} | {r['title'][:36]:38} | {r['shareUrl']} | {r['detail']}")
        for r in net:
            print(f"  ⚠ {r['id']} | {r['title'][:36]:38} | 网络异常（不算失效）：{r['detail']}")
        if dead:
            print(f"\n失效链接需重建分享：重转存 → 建分享务必传 expired_type=1（永久）→ 更新 shareUrl/pwd")
    return 1 if dead else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
