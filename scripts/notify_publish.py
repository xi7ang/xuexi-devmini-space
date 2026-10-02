#!/usr/bin/env python3
"""把 xuexi 站资源同步到 IMA 知识库 + 飞书文档（幂等，按日期去重）。

用法:
  python3 notify_publish.py                 # 全部资源
  python3 notify_publish.py --date 2026-10-02   # 只同步该日期更新的资源
  python3 notify_publish.py --date ... --force  # 忽略去重强制重推
"""
import argparse
import datetime
import json
import os
import subprocess
import sys

ROOT = "/root/.openclaw/workspace/projects/xuexi-devmini-space"
IMA_API = "/root/.openclaw/workspace/skills/ima-skill/ima_api.cjs"
KB_ID = "voS8_o4CR0hrhboJS6VXlHdFyk512g3zOPf2r_1DImk="
FEISHU_DOC = "https://my.feishu.cn/docx/PaIwdt4dRoNxJ5xYOvncM8u9nkM"
CATS = {"exam": "考试真题", "study": "中小学资料", "office": "办公素材"}

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_store  # noqa: E402

# 幂等状态存在仓库外的持久目录（见 scripts/state_store.py），不进内容仓库
STATE_NAME = ".notify_state.json"


def load_state():
    return state_store.load(STATE_NAME, default={"feishu": [], "ima": []})


def save_state(s):
    state_store.save(STATE_NAME, s)


def ima(method, body):
    out = subprocess.run(
        ["node", IMA_API, f"openapi/{method}", json.dumps(body, ensure_ascii=False)],
        capture_output=True, text=True,
    )
    try:
        return json.loads(out.stdout)
    except Exception:
        return {"code": -1, "msg": (out.stdout or out.stderr).strip()[:300]}


def build_md(items, tag):
    lines = ["# 学习资料站资源汇总", "",
             f"来源：https://xuexi.devmini.space ｜ 本批 {len(items)} 条 ｜ {tag}", ""]
    for cat in ("exam", "study", "office"):
        g = [i for i in items if i["category"] == cat]
        if not g:
            continue
        lines.append(f"## {CATS[cat]}（{len(g)}）")
        for i in g:
            pwd = f"　提取码 {i['pwd']}" if i.get("pwd") else ""
            lines.append(f"- {i['title']}｜{i['shareUrl']}{pwd}")
        lines.append("")
    lines += ["---", "本站仅整理公开分享信息，不存储任何资源文件。"]
    return "\n".join(lines)


def build_xml(items, tag):
    esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;")
    p = [f"<h1>资源列表 · {tag}</h1>",
         f"<p><span text-color=\"gray\">本批 {len(items)} 条</span></p>"]
    for cat in ("exam", "study", "office"):
        g = [i for i in items if i["category"] == cat]
        if not g:
            continue
        p.append(f"<h2>{CATS[cat]}（{len(g)}）</h2><ul>")
        for i in g:
            pwd = f"　提取码 <code>{i['pwd']}</code>" if i.get("pwd") else ""
            p.append(f"<li><a href=\"{i['shareUrl']}\">{esc(i['title'])}</a>{pwd}</li>")
        p.append("</ul>")
    return "".join(p)


def push_ima(items, tag):
    r1 = ima("note/v1/import_doc", {"content_format": 1, "content": build_md(items, tag)})
    note_id = (r1.get("data") or {}).get("note_id")
    if not note_id:
        return f"import_doc 失败: {r1.get('code')} {r1.get('msg')}"
    r2 = ima("wiki/v1/add_knowledge", {
        "media_type": 11, "note_info": {"content_id": note_id},
        "title": f"学习资料站资源汇总 {tag}", "knowledge_base_id": KB_ID,
    })
    if r2.get("code") != 0:
        return f"add_knowledge 失败: {r2.get('code')} {r2.get('msg')}"
    return "ok"


def push_feishu(items, tag):
    env = {k: v for k, v in os.environ.items() if not k.startswith("OPENCLAW")}
    out = subprocess.run(
        ["lark-cli", "docs", "+update", "--api-version", "v2", "--doc", FEISHU_DOC,
         "--command", "append", "--content", build_xml(items, tag)],
        capture_output=True, text=True, env=env,
    )
    try:
        d = json.loads(out.stdout)
        return "ok" if d.get("ok") else f"失败: {(d.get('error') or {}).get('message')}"
    except Exception:
        return f"raw: {(out.stdout or out.stderr)[:200]}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    items = json.load(open(os.path.join(ROOT, "data/resources.json"), encoding="utf-8"))["items"]
    tag = a.date or datetime.date.today().isoformat()
    if a.date:
        items = [i for i in items if i.get("updatedAt") == a.date]
    if not items:
        print(f"[notify] {tag} 无资源，跳过"); return

    st = load_state()
    if not a.force and tag in st.get("ima", []):
        print(f"[notify] {tag} IMA 已推过，跳过")
    else:
        r = push_ima(items, tag)
        print(f"[notify] IMA {tag}: {r}")
        if r == "ok":
            st.setdefault("ima", []).append(tag)

    if not a.force and tag in st.get("feishu", []):
        print(f"[notify] {tag} 飞书 已推过，跳过")
    else:
        r = push_feishu(items, tag)
        print(f"[notify] 飞书 {tag}: {r}")
        if r == "ok":
            st.setdefault("feishu", []).append(tag)

    save_state(st)


if __name__ == "__main__":
    main()
