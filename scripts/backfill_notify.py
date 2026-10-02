#!/usr/bin/env python3
"""把 xuexi 站资源回填到 IMA 知识库 + 飞书文档。

用法: python3 backfill_notify.py [--feishu-only|--ima-only]
"""
import json
import os
import subprocess
import sys

ROOT = "/root/.openclaw/workspace/projects/xuexi-devmini-space"
IMA_SKILL = "/root/.openclaw/workspace/skills/ima-skill"
IMA_API = os.path.join(IMA_SKILL, "ima_api.cjs")
KB_ID = "voS8_o4CR0hrhboJS6VXlHdFyk512g3zOPf2r_1DImk="
FEISHU_DOC = "https://my.feishu.cn/docx/PaIwdt4dRoNxJ5xYOvncM8u9nkM"

CATS = {"exam": "考试真题", "study": "中小学资料", "office": "办公素材"}


def load_items():
    with open(os.path.join(ROOT, "data/resources.json"), encoding="utf-8") as f:
        return json.load(f)["items"]


def ima(method, body):
    """调 ima_api.cjs，body 用 argv 传（避免 shell 转义）。"""
    out = subprocess.run(
        ["node", IMA_API, f"openapi/{method}", json.dumps(body, ensure_ascii=False)],
        capture_output=True, text=True,
    )
    try:
        return json.loads(out.stdout)
    except Exception:
        return {"code": -1, "msg": out.stdout.strip()[:300] or out.stderr.strip()[:300]}


def build_md(items):
    lines = [f"# 学习资料站资源汇总", "",
             f"来源：https://xuexi.devmini.space ｜ 共 {len(items)} 条 ｜ "
             f"更新 {__import__('datetime').date.today().isoformat()}", ""]
    for cat in ("exam", "study", "office"):
        group = [i for i in items if i["category"] == cat]
        if not group:
            continue
        lines.append(f"## {CATS[cat]}（{len(group)}）")
        for i in group:
            pwd = f"　提取码 {i['pwd']}" if i.get("pwd") else ""
            lines.append(f"- {i['title']}｜{i['shareUrl']}{pwd}")
        lines.append("")
    lines += ["---", "本站仅整理公开分享信息，不存储任何资源文件。"]
    return "\n".join(lines)


def build_xml(items):
    parts = ["<h1>资源列表</h1>",
             f"<p><span text-color=\"gray\">共 {len(items)} 条 · "
             f"更新 {__import__('datetime').date.today().isoformat()}</span></p>"]
    for cat in ("exam", "study", "office"):
        group = [i for i in items if i["category"] == cat]
        if not group:
            continue
        parts.append(f"<h2>{CATS[cat]}（{len(group)}）</h2><ul>")
        for i in group:
            pwd = f"　提取码 <code>{i['pwd']}</code>" if i.get("pwd") else ""
            parts.append(
                f"<li><a href=\"{i['shareUrl']}\">{i['title'].replace('&', '&amp;').replace('<', '&lt;')}</a>{pwd}</li>"
            )
        parts.append("</ul>")
    return "".join(parts)


def do_ima(items):
    md = build_md(items)
    title = f"学习资料站资源汇总 {__import__('datetime').date.today().isoformat()}"
    r1 = ima("note/v1/import_doc", {"content_format": 1, "content": md})
    print("[ima] import_doc:", r1.get("code"), r1.get("msg"))
    note_id = (r1.get("data") or {}).get("note_id")
    if not note_id:
        print("[ima] 未拿到 note_id，跳过 add_knowledge"); return
    print("[ima] note_id:", note_id)
    r2 = ima("wiki/v1/add_knowledge", {
        "media_type": 11,
        "note_info": {"content_id": note_id},
        "title": title,
        "knowledge_base_id": KB_ID,
    })
    print("[ima] add_knowledge:", r2.get("code"), r2.get("msg"))


def do_feishu(items):
    xml = build_xml(items)
    env = dict(os.environ)
    for k in [k for k in env if k.startswith("OPENCLAW")]:
        env.pop(k, None)
    out = subprocess.run(
        ["lark-cli", "docs", "+update", "--api-version", "v2", "--doc", FEISHU_DOC,
         "--command", "append", "--content", xml],
        capture_output=True, text=True, env=env,
    )
    try:
        d = json.loads(out.stdout)
        print("[feishu]", d.get("ok"), (d.get("error") or {}).get("message", ""))
    except Exception:
        print("[feishu] raw:", out.stdout[:300], out.stderr[:200])


if __name__ == "__main__":
    items = load_items()
    print(f"共 {len(items)} 条")
    only = sys.argv[1] if len(sys.argv) > 1 else ""
    if only != "--feishu-only":
        do_ima(items)
    if only != "--ima-only":
        do_feishu(items)
