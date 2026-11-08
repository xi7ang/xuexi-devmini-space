#!/usr/bin/env python3
"""站内分享链接体检（只读，不改数据）。

背景：2026-11-08 发现 10-20 那批 7 条站内链接全部「分享地址已过期」——
根因是当时用手写脚本建分享时没传 expired_type，默认值是 2（短期），
而正式批处理脚本都写死 expired_type=1（永久）。错链在站内躺了 19 天没人发现。

这个脚本把「链接是否还活着」变成可执行的检查：
  1. 读 data/resources.json，逐条取 shareUrl 与 pwd
  2. 调夸克 sharepage/token，看返回 status
  3. 分类：ok / expired / needs_pwd / net

⚠️ 只用标准库（urllib），不依赖 httpx —— CI 跑在干净的 ubuntu runner 上，
   多一个第三方依赖就多一份「装不上就静默失效」的风险。

用法：
  python3 scripts/check_links.py            # 体检 + 报告
  python3 scripts/check_links.py --json     # 机器可读
  python3 scripts/check_links.py --timeout 30

退出码：0 = 无失效/码不符；1 = 有失效或码不符；2 = 参数/环境错误。
"""
import argparse
import concurrent.futures
import json
import os
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "data", "resources.json")

TOKEN_URL = "https://drive-pc.quark.cn/1/clouddrive/share/sharepage/token"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Referer": "https://pan.quark.cn/",
    "Content-Type": "application/json",
}


def pwd_id_of(share_url: str) -> str:
    """从 https://pan.quark.cn/s/<pwd_id> 里取出 pwd_id。"""
    if "pan.quark.cn/s/" not in share_url:
        return ""
    tail = share_url.split("/s/", 1)[1]
    return tail.split("?")[0].split("-")[0].strip()


def check_one(pwd_id: str, pwd: str, timeout: float) -> tuple:
    """返回 (状态, 说明)。

    状态 ∈ ok / expired / needs_pwd / net
      ok        链接可用
      expired   分享已过期（真死链）
      needs_pwd 链接还在，但提取码不对或缺失 —— **不是死链**，
                 是站内 pwd 字段写错了（用户会点不开，但网盘没坏）
      net       网络异常（不算失效）
    """
    params = urllib.parse.urlencode({
        "pr": "ucpro", "fr": "pc", "uc_param_str": "",
        "__dt": random.randint(100, 9999), "__t": str(int(time.time() * 1000)),
        "pwd_id": pwd_id,
    })
    body = json.dumps({"pwd_id": pwd_id, "passcode": pwd or ""}).encode()
    req = urllib.request.Request(f"{TOKEN_URL}?{params}", data=body, headers=HEADERS, method="POST")
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                j = json.loads(resp.read().decode("utf-8", "replace"))
            break
        except urllib.error.HTTPError as exc:
            try:
                j = json.loads(exc.read().decode("utf-8", "replace"))
                break
            except Exception:  # noqa: BLE001
                j = {"message": f"HTTP {exc.code}"}
                break
        except Exception as exc:  # noqa: BLE001  网络层异常
            if attempt == 2:
                return "net", f"{type(exc).__name__}"
            time.sleep(2 + attempt * 2)
    else:
        return "net", "retries exhausted"

    if j.get("status") == 200 and j.get("data"):
        d = j["data"]
        return "ok", f"expired_type={d.get('expired_type')} expired_at={d.get('expired_at')}"
    msg = str(j.get("message") or j.get("code") or "no-data")
    # 顺序很重要：先判「过期」，再判「提取码」。
    # 2026-11-08 教训：带提取码的分享在**裸请求**下会回「需要提取码」，
    # 若把它当「过期」就会把好链接误报成死链（实测误报 6 条）。
    if "过期" in msg or "expired" in msg.lower():
        return "expired", msg
    if "提取码" in msg or "passcode" in msg.lower() or "密码" in msg:
        return "needs_pwd", msg
    return "expired", msg


def main() -> int:
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
            # 提取码必须一起带上：裸请求下带提取码的分享不给码就取不到 token。
            targets.append((it.get("id", ""), it.get("title", ""), url, pid, it.get("pwd") or ""))

    if not targets:
        print("[info] 没有需要体检的夸克分享")
        return 0

    def work(t):
        iid, title, url, pid, pwd = t
        state, detail = check_one(pid, pwd, a.timeout)
        return {"id": iid, "title": title, "shareUrl": url, "state": state, "detail": detail}

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, a.concurrency)) as pool:
        results = list(pool.map(work, targets))

    dead = [r for r in results if r["state"] == "expired"]
    needpwd = [r for r in results if r["state"] == "needs_pwd"]
    net = [r for r in results if r["state"] == "net"]
    ok = [r for r in results if r["state"] == "ok"]

    if a.json:
        print(json.dumps({"checked": len(results), "ok": len(ok),
                          "expired": len(dead), "needs_pwd": len(needpwd),
                          "net_error": len(net),
                          "dead": dead, "needs_pwd_list": needpwd, "net": net},
                         ensure_ascii=False, indent=2))
    else:
        print(f"体检 {len(results)} 条：有效 {len(ok)} · 失效 {len(dead)} · "
              f"提取码不符 {len(needpwd)} · 网络异常 {len(net)}")
        for r in dead:
            print(f"  ❌ {r['id']} | {r['title'][:36]:38} | {r['shareUrl']} | {r['detail']}")
        for r in needpwd:
            print(f"  ⚠ {r['id']} | {r['title'][:36]:38} | {r['shareUrl']} | {r['detail']}（链接在，pwd 不对）")
        for r in net:
            print(f"  ⚠ {r['id']} | {r['title'][:36]:38} | 网络异常（不算失效）：{r['detail']}")
        if dead:
            print("\n失效链接需重建分享：重转存 → 建分享务必传 expired_type=1（永久）→ 更新 shareUrl/pwd")
    return 1 if (dead or needpwd) else 0


if __name__ == "__main__":
    sys.exit(main())
