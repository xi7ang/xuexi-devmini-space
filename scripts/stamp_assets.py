#!/usr/bin/env python3
"""给 HTML 里的 assets 引用打内容哈希版本号，解决静态资源长缓存问题。

站点资源被 CDN/浏览器缓存 4 小时（cache-control: max-age=14400），
HTML 里的 <script src="assets/js/app.js"> 不带版本号时，改版后用户仍看旧文件。
本脚本把引用重写成 assets/js/app.js?v=<sha256 前 8 位>，内容一变 URL 就变。

幂等：已是最新哈希则不改。由 .github/workflows/stamp-assets.yml 在 assets/ 变更时自动跑。
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def discover_assets() -> list[str]:
    """从 assets/ 发现所有 js/css。别硬编码列表：新增文件会静默不打号，
    又被 4 小时长缓存咬。"""
    return sorted(p.relative_to(ROOT).as_posix()
                  for p in ROOT.glob("assets/**/*")
                  if p.suffix in (".js", ".css"))


def digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:8]


def main() -> int:
    vers = {a: digest(ROOT / a) for a in discover_assets() if (ROOT / a).exists()}
    changed = []
    for html in sorted(ROOT.glob("*.html")):
        text = orig = html.read_text(encoding="utf-8")
        for asset, ver in vers.items():
            # 匹配 href/src="<asset>" 或已带 ?v=... 的形式
            pattern = re.compile(r'(?P<attr>(?:href|src)=")' + re.escape(asset) + r'(?:\?v=[^"]*)?(")')
            text = pattern.sub(lambda m, v=ver: f"{m.group('attr')}{asset}?v={v}{m.group(2)}", text)
        if text != orig:
            html.write_text(text, encoding="utf-8")
            changed.append(html.name)
    print(f"版本: {vers}")
    print("已更新: " + (", ".join(changed) if changed else "无变化"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
