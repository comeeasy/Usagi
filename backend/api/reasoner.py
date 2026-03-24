"""
api/reasoner.py — Reasoner 실행/결과 조회 라우터

엔드포인트:
  POST /ontologies/{id}/reasoner/run             추론 실행 (비동기 Job)
  GET  /ontologies/{id}/reasoner/jobs/{job_id}   추론 작업 상태 + 결과 조회
"""

from fastapi import APIRouter, HTTPException, Request

from models.ontology import JobResponse
from models.reasoner import ReasonerRunRequest

router = APIRouter(
    prefix="/ontologies/{ontology_id}/reasoner",
    tags=["reasoner"],
)


@router.post("/run", status_code=202)
async def run_reasoner(
    request: Request, ontology_id: str, body: ReasonerRunRequest
) -> dict:
    """OWL 2 추론 실행 (비동기). 202 Accepted + jobId 즉시 반환."""
    reasoner: "ReasonerService" = request.app.state.reasoner_service  # type: ignore
    job_id = await reasoner.run(ontology_id, body.subgraph_entity_iris)
    return {"job_id": job_id, "status": "pending"}


@router.get("/jobs/{job_id}")
async def get_reasoner_job(
    request: Request, ontology_id: str, job_id: str
) -> dict:
    """추론 작업 상태 및 결과 조회."""
    reasoner = request.app.state.reasoner_service

    try:
        job = await reasoner.get_result(job_id)
    except KeyError:
        raise HTTPException(
            404, detail={"code": "JOB_NOT_FOUND", "message": f"Job {job_id} not found"}
        )

    if job.get("ontology_id") != ontology_id:
        raise HTTPException(
            403,
            detail={"code": "JOB_ACCESS_DENIED", "message": "Job does not belong to this ontology"},
        )

    return job
