"""
api/datasets.py — Fuseki Dataset 관리 라우터

엔드포인트:
  GET  /datasets          Fuseki dataset 목록 조회 (Admin API 프록시)
  POST /datasets          새 dataset 생성
  DELETE /datasets/{name} dataset 삭제
"""
import logging

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/datasets", tags=["datasets"])


def _admin_url(path: str = "") -> str:
    return f"{settings.fuseki_url}/$/{path.lstrip('/')}"


# ── 목록 ─────────────────────────────────────────────────────────────────────

@router.get("")
async def list_datasets(request: Request) -> list[dict]:
    """Fuseki Admin API에서 dataset 목록을 가져온다."""
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(_admin_url("datasets"), headers={"Accept": "application/json"})
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("Fuseki admin list failed: %s", exc)
            raise HTTPException(status_code=502, detail=f"Fuseki admin API error: {exc}")

    data = resp.json()
    datasets = data.get("datasets", [])
    return [
        {
            "name": ds.get("ds.name", "").lstrip("/"),
            "type": ds.get("ds.state", "active"),
        }
        for ds in datasets
    ]


# ── 생성 ─────────────────────────────────────────────────────────────────────

class DatasetCreate(BaseModel):
    name: str
    db_type: str = "TDB2"  # TDB2 | mem


@router.post("", status_code=201)
async def create_dataset(body: DatasetCreate) -> dict:
    """Fuseki Admin API로 새 dataset을 생성한다."""
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.post(
                _admin_url("datasets"),
                data={"dbName": body.name, "dbType": body.db_type},
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 409:
                raise HTTPException(status_code=409, detail=f"Dataset '{body.name}' already exists")
            logger.error("Fuseki dataset create failed: %s", exc)
            raise HTTPException(status_code=502, detail=f"Fuseki admin API error: {exc}")
        except httpx.HTTPError as exc:
            logger.error("Fuseki dataset create failed: %s", exc)
            raise HTTPException(status_code=502, detail=f"Fuseki admin API error: {exc}")

    logger.info("Dataset created: %s (%s)", body.name, body.db_type)
    return {"name": body.name, "db_type": body.db_type, "status": "created"}


# ── 삭제 ─────────────────────────────────────────────────────────────────────

@router.delete("/{name}", status_code=204)
async def delete_dataset(name: str) -> None:
    """Fuseki Admin API로 dataset을 삭제한다."""
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.delete(_admin_url(f"datasets/{name}"))
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise HTTPException(status_code=404, detail=f"Dataset '{name}' not found")
            logger.error("Fuseki dataset delete failed: %s", exc)
            raise HTTPException(status_code=502, detail=f"Fuseki admin API error: {exc}")
        except httpx.HTTPError as exc:
            logger.error("Fuseki dataset delete failed: %s", exc)
            raise HTTPException(status_code=502, detail=f"Fuseki admin API error: {exc}")

    logger.info("Dataset deleted: %s", name)
