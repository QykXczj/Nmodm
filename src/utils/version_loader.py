"""加载并缓存包内版本信息的工具。

该模块使用 importlib.resources 在打包后仍能访问包内资源。
"""
from __future__ import annotations

import json
from typing import Optional

try:
    # Python 3.9+
    from importlib import resources
except Exception:
    # Fallback for older versions; should still work in typical environments
    import importlib_resources as resources  # type: ignore

_VERSION: Optional[str] = None


def _load_from_package() -> Optional[str]:
    try:
        # version.json 放在 src/ 包的顶层
        with resources.open_text(__package__.split('.')[0], "version.json", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("version")
    except Exception:
        return None


def get_version() -> str:
    """返回缓存的版本字符串，默认回退为 '0.0.0'。"""
    global _VERSION
    if _VERSION is None:
        _VERSION = _load_from_package() or "0.0.0"
    return _VERSION
