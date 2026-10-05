#!/usr/bin/env python3
"""给所有 *.html <head> 补品牌片段（幂等；重复跑不叠加）。
用法：python3 scripts/inject_head_meta.py
"""
from __future__ import annotations
import re, hashlib
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
SITE = "https://xuexi.devmini.space"
MARK = "<!-- brand-head -->"
SITE_META = ('<meta property="og:type" content="website">\n'
             '<meta property="og:site_name" content="学习资料站">\n')

def h(name): p=ROOT/"assets"/"img"/name; return hashlib.sha256(p.read_bytes()).hexdigest()[:8] if p.exists() else "0"

def block():
    v64,v180,vog=h("icon-64.png"),h("icon-180.png"),h("og.png")
    return f"""{MARK}
<link rel="apple-touch-icon" sizes="180x180" href="assets/img/icon-180.png?v={v180}">
<meta property="og:image" content="{SITE}/assets/img/og.png?v={vog}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
"""

def all_pages():
    """根目录页面 + 预生成的资源静态页 r/*.html。"""
    return sorted(list(ROOT.glob("*.html")) + list((ROOT / "r").glob("*.html")))


def main():
    blk=block(); changed=[]
    for p in all_pages():
        t=orig=p.read_text("utf-8")
        if "</head>" not in t: continue
        if MARK in t:
            t = re.compile(re.escape(MARK)+r".*?(?=</head>)",re.S).sub(blk,t,1)
        else:
            extra="" if 'property="og:site_name"' in t else SITE_META
            t=t.replace("</head>", extra+blk+"</head>",1)
        if t!=orig: p.write_text(t,"utf-8"); changed.append(p.name)
    print("updated:",", ".join(changed) or "none")
    return 0
if __name__=="__main__": raise SystemExit(main())