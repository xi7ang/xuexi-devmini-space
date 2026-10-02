#!/usr/bin/env python3
"""xuexi 发布流水线的幂等状态存放位置。

状态是**运行时数据**，不属于站点内容仓库。以前放在仓库根目录
（.notify_state_items.json / .tg_state_items.json / .notify_state.json），
一旦 `git checkout .`、换机器或干净 clone，去重记录就丢了，
已推过的资源会被当成新资源重推（IMA 笔记 + 飞书条目 + TG 消息三处刷屏）。

现统一放到仓库外的持久目录，优先级：
  1) 环境变量 XUEXI_STATE_DIR
  2) credentials/quark-xuexi-publisher.env 里的 XUEXI_STATE_DIR
  3) 默认 ~/.local/state/xuexi-publisher

首次解析时若外部文件不存在、而仓库内遗留文件还在，自动迁移一次（保留全部键）。
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CREDS_ENV = Path("/root/.openclaw/credentials/quark-xuexi-publisher.env")
DEFAULT_DIR = "~/.local/state/xuexi-publisher"


def _dir_from_creds() -> str | None:
    try:
        for line in CREDS_ENV.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("XUEXI_STATE_DIR="):
                return line.split("=", 1)[1].strip() or None
    except Exception:
        pass
    return None


def state_dir() -> Path:
    raw = os.environ.get("XUEXI_STATE_DIR") or _dir_from_creds() or DEFAULT_DIR
    d = Path(os.path.expanduser(raw))
    d.mkdir(parents=True, exist_ok=True)
    return d


def state_path(name: str) -> Path:
    """状态文件绝对路径；必要时从仓库内遗留文件一次性迁移。"""
    dst = state_dir() / name
    legacy = REPO_ROOT / name
    if not dst.exists() and legacy.exists():
        shutil.copy2(legacy, dst)
    return dst


def load(name: str, default=None):
    try:
        return json.load(open(state_path(name), encoding="utf-8"))
    except Exception:
        return {} if default is None else default


def save(name: str, data) -> None:
    p = state_path(name)
    tmp = p.with_name(p.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, p)
