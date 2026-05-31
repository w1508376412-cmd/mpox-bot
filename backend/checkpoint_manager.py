"""Lightweight checkpoint tracking for raw knowledge preprocessing."""
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
import json

from preprocess_utils import generate_file_fingerprint


class CheckpointManager:
    """Record processed and failed source files for resumable preprocessing."""

    def __init__(self, checkpoint_path: Path):
        self.checkpoint_path = Path(checkpoint_path)
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        if not self.checkpoint_path.exists():
            return self._empty()

        try:
            return json.loads(self.checkpoint_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            backup_path = self.checkpoint_path.with_suffix(".corrupt.json")
            self.checkpoint_path.replace(backup_path)
            return self._empty()

    def _empty(self) -> Dict[str, Any]:
        return {
            "processed": {},
            "failed": {},
            "summary": {
                "total_successful": 0,
                "total_failed": 0,
                "last_updated": None,
            },
        }

    def _save(self) -> None:
        self.data["summary"] = self.get_summary()
        temp_path = self.checkpoint_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_path.replace(self.checkpoint_path)

    def _key(self, file_path: Path) -> str:
        return generate_file_fingerprint(Path(file_path))

    def is_processed(self, file_path: Path) -> bool:
        return self._key(file_path) in self.data["processed"]

    def record_success(self, file_path: Path, details: Dict[str, Any]) -> None:
        key = self._key(file_path)
        self.data["processed"][key] = {
            "file_path": str(Path(file_path)),
            "file_name": Path(file_path).name,
            "processed_at": datetime.now().isoformat(),
            "details": details,
        }
        self.data["failed"].pop(key, None)
        self._save()

    def record_failure(self, file_path: Path, error: str, details: Dict[str, Any] | None = None) -> None:
        key = self._key(file_path)
        self.data["failed"][key] = {
            "file_path": str(Path(file_path)),
            "file_name": Path(file_path).name,
            "failed_at": datetime.now().isoformat(),
            "error": error,
            "details": details or {},
        }
        self._save()

    def get_summary(self) -> Dict[str, Any]:
        return {
            "total_successful": len(self.data["processed"]),
            "total_failed": len(self.data["failed"]),
            "last_updated": datetime.now().isoformat(),
        }
