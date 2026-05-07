"""Local-filesystem storage. Mirrors the subset of apollo's Storage interface."""

from __future__ import annotations

import shutil
from pathlib import Path


class Storage:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self.root / key

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def get(self, key: str) -> Path:
        return self._path(key)

    def put(self, key: str, src_path: str) -> None:
        dest = self._path(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src_path, dest)

    def put_text(self, key: str, content: str) -> None:
        dest = self._path(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")

    def list(self, prefix: str) -> list[str]:
        base = self._path(prefix)
        if not base.exists():
            return []
        if base.is_file():
            return [prefix]
        keys = []
        for p in base.rglob("*"):
            if p.is_file():
                # Storage keys are logical (always forward-slash), not OS paths.
                # On Windows, str(relative_to(...)) yields backslashes, which
                # breaks downstream key parsing (e.g. ChatManager splits on "/").
                keys.append(p.relative_to(self.root).as_posix())
        return keys
