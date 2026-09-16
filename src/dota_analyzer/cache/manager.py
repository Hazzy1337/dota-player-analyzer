from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any


class CacheManager:
    def __init__(self, root: Path, ttl_hours: int = 24, enabled: bool = True):
        self.root = root
        self.ttl_seconds = ttl_hours * 3600
        self.enabled = enabled
        root.mkdir(parents=True, exist_ok=True)

    def _path(self, namespace: str, key: str, suffix: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        folder = self.root / namespace
        folder.mkdir(parents=True, exist_ok=True)
        return folder / f"{digest}.{suffix}"

    def get_text(self, namespace: str, key: str) -> str | None:
        path = self._path(namespace, key, "html")
        if not self.enabled or not path.exists():
            return None
        if time.time() - path.stat().st_mtime > self.ttl_seconds:
            return None
        return path.read_text(encoding="utf-8")

    def set_text(self, namespace: str, key: str, value: str) -> Path:
        path = self._path(namespace, key, "html")
        path.write_text(value, encoding="utf-8")
        return path

    def get_json(self, namespace: str, key: str) -> Any | None:
        path = self._path(namespace, key, "json")
        if not self.enabled or not path.exists():
            return None
        if time.time() - path.stat().st_mtime > self.ttl_seconds:
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def set_json(self, namespace: str, key: str, value: Any) -> Path:
        path = self._path(namespace, key, "json")
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return path

