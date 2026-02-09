from __future__ import annotations

from pathlib import Path
from typing import Dict


class ConfigService:
    def __init__(self, env_path: Path):
        self.env_path = env_path

    def load(self) -> Dict[str, str]:
        if not self.env_path.exists():
            return {}
        data: Dict[str, str] = {}
        for line in self.env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            data[key.strip()] = value.strip()
        return data

    def save(self, values: Dict[str, str]) -> None:
        current = self.load()
        current.update(values)
        lines = [f"{key}={value}" for key, value in current.items()]
        self.env_path.parent.mkdir(parents=True, exist_ok=True)
        self.env_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
