import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class JobStore:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def job_dir(self, job_id: str) -> Path:
        path = self.root / job_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _path(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "job.json"

    def create(self, job_id: str, filename: str, options: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "job_id": job_id,
            "filename": filename,
            "status": "queued",
            "stage": "queued",
            "progress": 0,
            "message": "Da nhan tep PDF.",
            "options": options,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "result_zip": None,
            "error": None,
        }
        self.write(job_id, payload)
        return payload

    def read(self, job_id: str) -> dict[str, Any]:
        path = self._path(job_id)
        if not path.exists():
            raise FileNotFoundError(job_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def update(self, job_id: str, **changes: Any) -> dict[str, Any]:
        with self._lock:
            payload = self.read(job_id)
            payload.update(changes)
            payload["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._path(job_id).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            return payload

    def write(self, job_id: str, payload: dict[str, Any]) -> None:
        with self._lock:
            self._path(job_id).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
