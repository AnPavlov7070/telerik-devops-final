import json
import os
import time
from pathlib import Path
from typing import Iterable, List


class StateStore:
    """
    Simple JSON state file to remember seen message identifiers.
    Uses atomic writes and a basic lock file with timeout.
    Format:
    {
      "version": 1,
      "seen": ["<mid1>", "sha256:abcd...", ...]
    }
    """

    def __init__(self, path: str, lock_timeout_s: int = 10):
        self.path = Path(path)
        self.dir = self.path.parent
        self.lock_path = self.dir / "state.lock"
        self.lock_timeout_s = lock_timeout_s
        self.dir.mkdir(parents=True, exist_ok=True)

        if not self.path.exists():
            self._write({"version": 1, "seen": []})

        self._data = self._read()

    def _acquire_lock(self):
        start = time.time()
        while True:
            try:
                # exclusive create
                fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                return
            except FileExistsError:
                if time.time() - start > self.lock_timeout_s:
                    raise TimeoutError("Timeout waiting for state lock")
                time.sleep(0.1)

    def _release_lock(self):
        try:
            self.lock_path.unlink(missing_ok=True)
        except Exception:
            pass

    def _read(self):
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write(self, data: dict):
        tmp = self.path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    def is_seen(self, identity_key: str) -> bool:
        return identity_key in self._data.get("seen", [])

    def add_many(self, keys: Iterable[str]):
        keys = [k for k in keys if k]
        if not keys:
            return
        self._acquire_lock()
        try:
            data = self._read()
            seen = set(data.get("seen", []))
            changed = False
            for k in keys:
                if k not in seen:
                    seen.add(k)
                    changed = True
            if changed:
                data["version"] = 1
                data["seen"] = sorted(seen)
                self._write(data)
                self._data = data
        finally:
            self._release_lock()
