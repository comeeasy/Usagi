"""
services/job_store.py — SQLite 기반 Reasoner Job 영속 저장소

인메모리 dict(_job_store)를 대체하여 서버 재시작 후에도 job 상태 조회 가능.
완료/실패 후 7일이 지난 job은 cleanup_expired()로 자동 삭제.
"""
from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = Path(__file__).parent.parent / "uploads" / "jobs.db"
_TTL_DAYS = 7


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobStore:
    """SQLite 기반 Job 저장소 (asyncio-safe, run_in_executor 래핑)."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = str(db_path or _DEFAULT_DB_PATH)
        self._initialized = False

    # ── 초기화 ────────────────────────────────────────────────────────────────

    def _ensure_init_sync(self) -> None:
        if self._initialized:
            return
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id       TEXT PRIMARY KEY,
                    ontology_id  TEXT NOT NULL,
                    status       TEXT NOT NULL DEFAULT 'pending',
                    created_at   TEXT NOT NULL,
                    completed_at TEXT,
                    result_json  TEXT,
                    error        TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_ontology ON jobs(ontology_id)")
            conn.commit()
        finally:
            conn.close()
        self._initialized = True

    # ── 동기 헬퍼 ─────────────────────────────────────────────────────────────

    def _create_sync(self, job_id: str, ontology_id: str) -> None:
        self._ensure_init_sync()
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute(
                "INSERT INTO jobs (job_id, ontology_id, status, created_at) VALUES (?, ?, 'pending', ?)",
                (job_id, ontology_id, _now_iso()),
            )
            conn.commit()
        finally:
            conn.close()

    def _update_sync(self, job_id: str, status: str | None = None,
                     result: dict | None = None, error: str | None = None,
                     completed_at: str | None = None) -> None:
        self._ensure_init_sync()
        fields: list[str] = []
        values: list[Any] = []
        if status is not None:
            fields.append("status = ?")
            values.append(status)
        if result is not None:
            fields.append("result_json = ?")
            values.append(json.dumps(result))
        if error is not None:
            fields.append("error = ?")
            values.append(error)
        if completed_at is not None:
            fields.append("completed_at = ?")
            values.append(completed_at)
        if not fields:
            return
        values.append(job_id)
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute(f"UPDATE jobs SET {', '.join(fields)} WHERE job_id = ?", values)
            conn.commit()
        finally:
            conn.close()

    def _get_sync(self, job_id: str) -> dict | None:
        self._ensure_init_sync()
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
            if row is None:
                return None
            d = dict(row)
            result_json = d.pop("result_json", None)
            d["result"] = json.loads(result_json) if result_json else None
            return d
        finally:
            conn.close()

    def _list_sync(self, ontology_id: str) -> list[dict]:
        self._ensure_init_sync()
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT job_id, ontology_id, status, created_at, completed_at "
                "FROM jobs WHERE ontology_id = ? ORDER BY created_at DESC LIMIT 50",
                (ontology_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def _cleanup_sync(self) -> int:
        self._ensure_init_sync()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=_TTL_DAYS)).isoformat()
        conn = sqlite3.connect(self._db_path)
        try:
            cur = conn.execute(
                "DELETE FROM jobs WHERE status IN ('completed', 'failed') AND created_at < ?",
                (cutoff,),
            )
            conn.commit()
            return cur.rowcount
        finally:
            conn.close()

    # ── 비동기 공개 API ────────────────────────────────────────────────────────

    async def create(self, job_id: str, ontology_id: str) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._create_sync, job_id, ontology_id)

    async def update(self, job_id: str, status: str | None = None,
                     result: dict | None = None, error: str | None = None,
                     completed_at: str | None = None) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, self._update_sync, job_id, status, result, error, completed_at
        )

    async def get(self, job_id: str) -> dict | None:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_sync, job_id)

    async def list_by_ontology(self, ontology_id: str) -> list[dict]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._list_sync, ontology_id)

    async def cleanup_expired(self) -> int:
        loop = asyncio.get_event_loop()
        deleted = await loop.run_in_executor(None, self._cleanup_sync)
        if deleted:
            logger.info("JobStore: expired %d old job(s)", deleted)
        return deleted
