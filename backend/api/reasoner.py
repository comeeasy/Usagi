"""
api/reasoner.py — Reasoner 실행/결과 조회 라우터

엔드포인트:
  POST /ontologies/{id}/reasoner/run             추론 실행 (비동기 Job)
  GET  /ontologies/{id}/reasoner/jobs/{job_id}   추론 작업 상태 + 결과 조회
"""

from fastapi import APIRouter, HTTPException

from models.reasoner import ReasonerRunRequest, ReasonerResult, JobResponse

router = APIRouter(
    prefix="/ontologies/{ontology_id}/reasoner",
    tags=["reasoner"],
)


@router.post("/run", response_model=JobResponse, status_code=202)
async def run_reasoner(ontology_id: str, body: ReasonerRunRequest) -> JobResponse:
    """
    OWL 2 추론 실행 (비동기).

    구현 세부사항:
    - job_id = str(uuid4())
    - job_store[job_id] = { status: "pending", createdAt: now(), ontologyId: ontology_id }
    - asyncio.create_task(_execute_reasoner(job_id, ontology_id, body.subgraph_entity_iris))
      → 백그라운드에서 ReasonerService.run() 호출
    - _execute_reasoner:
        1. job_store[job_id]["status"] = "running"
        2. result = await ReasonerService.run(ontology_id, entity_iris)
        3. job_store[job_id] = { status: "completed", result: result, completedAt: now() }
        4. 오류 발생 시 job_store[job_id]["status"] = "failed", error = str(e)
    - JobResponse(jobId=job_id, status="pending") 즉시 반환 (202 Accepted)
    """
    pass


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_reasoner_job(ontology_id: str, job_id: str) -> JobResponse:
    """
    추론 작업 상태 및 결과 조회.

    구현 세부사항:
    - job_store[job_id] 조회
    - 없으면 HTTPException(404, code="JOB_NOT_FOUND")
    - ontology_id 불일치 시 HTTPException(403, code="JOB_ACCESS_DENIED")
    - status="running": JobResponse(status="running") 반환 (프론트엔드 폴링용)
    - status="completed": JobResponse(status="completed", result=ReasonerResult) 반환
    - status="failed": JobResponse(status="failed", error=오류메시지) 반환
    """
    pass
