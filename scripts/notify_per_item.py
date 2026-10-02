#!/usr/bin/env python3
"""一条资源 = 一条 IMA 笔记 + 一条飞书条目（按日期幂等）。

TG 消息由调用方用 conversations_send 逐条发送（脚本不直接发 TG）。

用法: python3 notify_per_item.py [--date YYYY-MM-DD] [--force]
"""
import argparse
import datetime
import json
import os
import subprocess

ROOT = "/root/.openclaw/workspace/projects/xuexi-devmini-space"
IMA_API = "/root/.openclaw/workspace/skills/ima-skill/ima_api.cjs"
KB_ID = "voS8_o4CR0hrhboJS6VXlHdFyk512g3zOPf2r_1DImk="
FEISHU_DOC = "https://my.feishu.cn/docx/PaIwdt4dRoNxJ5xYOvncM8u9nkM"
STATE = os.path.join(ROOT, ".notify_state_items.json")
CATS = {"exam": "考试真题", "study": "中小学资料", "office": "办公素材"}


def load_state():
    try:
        return json.load(open(STATE, encoding="utf-8"))
    except Exception:
        return {}


def save_state(s):
    json.dump(s, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def ima(method, body):
    out = subprocess.run(
        ["node", IMA_API, f"openapi/{method}", json.dumps(body, ensure_ascii=False)],
        capture_output=True, text=True)
    try:
        return json.loads(out.stdout)
    except Exception:
        return {"code": -1, "msg": (out.stdout or out.stderr).strip()[:200]}


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;")


def item_text(it):
    # 展示给用户的资源链接 = 站点详情页（不再暴露夸克原链）
    return {
        "title": it["title"],
        "desc": it.get("desc") or "",
        "tags": it.get("tags") or [],
        "link": f"https://xuexi.devmini.space/resource.html?id={it['id']}",
        "cat": CATS.get(it["category"], it["category"]),
    }


def push_ima_one(it):
    t = item_text(it)
    md = (f"# {t['title']}\n\n"
          f"- **分类**：{t['cat']}\n"
          f"- **标签**：{'、'.join(t['tags']) if t['tags'] else '无'}\n"
          f"- **描述**：{t['desc'] or '无'}\n"
          f"- **资源详情页**：{t['link']}\n")
    r1 = ima("note/v1/import_doc", {"content_format": 1, "content": md})
    nid = (r1.get("data") or {}).get("note_id")
    if not nid:
        return f"import_doc失败 {r1.get('code')} {r1.get('msg')}"
    r2 = ima("wiki/v1/add_knowledge", {
        "media_type": 11, "note_info": {"content_id": nid},
        "title": t["title"], "knowledge_base_id": KB_ID})
    return "ok" if r2.get("code") == 0 else f"add_knowledge失败 {r2.get('code')} {r2.get('msg')}"


def push_feishu_one(it):
    t = item_text(it)
    tags = "、".join(t["tags"]) if t["tags"] else "无"
    xml = (f"<h2>{esc(t['title'])}</h2>"
           f"<p><b>分类</b>：{t['cat']}　<b>标签</b>：{esc(tags)}</p>"
           f"<p><b>描述</b>：{esc(t['desc']) or '无'}</p>"
           f"<p><b>详情页</b>：<a href=\"{t['link']}\">{t['link']}</a></p><hr/>")
    env = {k: v for k, v in os.environ.items() if not k.startswith("OPENCLAW")}
    out = subprocess.run(
        ["lark-cli", "docs", "+update", "--api-version", "v2", "--doc", FEISHU_DOC,
         "--command", "append", "--content", xml],
        capture_output=True, text=True, env=env)
    try:
        d = json.loads(out.stdout)
        return "ok" if d.get("ok") else f"失败 {(d.get('error') or {}).get('message')}"
    except Exception:
        return f"raw {(out.stdout or out.stderr)[:150]}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    items = json.load(open(os.path.join(ROOT, "data/resources.json"), encoding="utf-8"))["items"]
    if a.date:
        items = [i for i in items if i.get("updatedAt") == a.date]
    st = load_state()
    for it in items:
        key = it["id"]
        if not a.force and st.get(key) == "ok":
            print(f"[skip] {it['title'][:30]} 已推过"); continue
        ri = push_ima_one(it)
        rf = push_feishu_one(it)
        ok = (ri == "ok" and rf == "ok")
        st[key] = "ok" if ok else f"ima={ri} feishu={rf}"
        print(f"[{ 'ok' if ok else '部分失败' }] {it['title'][:34]} | ima={ri} | feishu={rf}")
    save_state(st)


if __name__ == "__main__":
    main()
