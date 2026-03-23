"""
services/reasoner_service.py — owlready2 + HermiT OWL 2 추론 서비스

추론 실행 흐름:
  1. Oxigraph에서 대상 그래프 CONSTRUCT → Turtle 임시 파일
  2. owlready2.get_ontology().load() → in-memory OWL 그래프
  3. sync_reasoner_hermit(infer_property_values=True, infer_data_property_values=True)
  4. 추론 결과(inferred triples) → Oxigraph inferred Named Graph에 저장
  5. 위반/추론 사실 → ReasonerResult 직렬화

전제 조건: JVM 설치 필요 (Dockerfile에서 default-jre-headless 설치)
"""

import asyncio
import time
import tempfile
from typing import Any

from models.reasoner import ReasonerResult, ReasonerViolation, InferredAxiom

# import owlready2
# from services.ontology_store import OntologyStore


class ReasonerService:
    """owlready2 HermiT 추론기 서비스."""

    def __init__(self, ontology_store: Any):
        """
        구현 세부사항:
        - self._store = ontology_store
        - self._job_store: dict = {} — job_id → { status, result, error, createdAt, completedAt }
        - asyncio.Lock() — 동시 추론 실행 방지 (HermiT은 싱글 인스턴스 권장)
        """
        pass

    async def run(self, ontology_id: str, entity_iris: list[str] | None = None) -> str:
        """
        추론 실행 (비동기) → job_id 즉시 반환.

        구현 세부사항:
        - job_id = str(uuid4())
        - self._job_store[job_id] = { status: "pending", createdAt: now() }
        - asyncio.create_task(self._execute(job_id, ontology_id, entity_iris)) 생성
        - job_id 반환 (API 레이어에서 폴링)
        """
        pass

    async def _execute(
        self,
        job_id: str,
        ontology_id: str,
        entity_iris: list[str] | None,
    ) -> None:
        """
        실제 추론 실행 (백그라운드 태스크).

        구현 세부사항:
        1. self._job_store[job_id]["status"] = "running"
        2. turtle_str = await self._store.export_turtle(ontology_id)
           entity_iris 있을 경우: SPARQL로 서브그래프만 추출 후 Turtle 변환
        3. with tempfile.NamedTemporaryFile(suffix=".owl", delete=False) as f:
               f.write(turtle_str.encode())
               tmp_path = f.name
        4. loop = asyncio.get_event_loop()
           result = await loop.run_in_executor(None, self._run_hermit, tmp_path)
        5. 추론된 트리플을 Oxigraph inferred Named Graph에 저장:
           await self._store.insert_triples(f"{ontology_iri}/inferred", result.inferred_triples)
        6. self._job_store[job_id] = { status: "completed", result: result, completedAt: now() }
        7. 오류 발생 시: self._job_store[job_id] = { status: "failed", error: str(e) }
        """
        pass

    def _run_hermit(self, owl_path: str) -> ReasonerResult:
        """
        HermiT 추론기 동기 실행 (run_in_executor에서 호출).

        구현 세부사항:
        - start = time.perf_counter()
        - onto = owlready2.get_ontology(f"file://{owl_path}").load()
        - with onto:
              owlready2.sync_reasoner_hermit(
                  infer_property_values=True,
                  infer_data_property_values=True,
              )
        - violations 수집:
          - UnsatisfiableClass: onto.inconsistent_classes() → ReasonerViolation(type="UnsatisfiableClass")
          - CardinalityViolation: 각 Individual의 Property 값 수 검사 (restriction 기준)
          - DisjointViolation: owl:disjointWith 위반
        - inferredAxioms 수집:
          - 추론 전후 트리플 비교로 새로 생긴 트리플 목록
          - 각 트리플을 InferredAxiom(subject, predicate, object, inferenceRule) 변환
        - execution_ms = (time.perf_counter() - start) * 1000
        - ReasonerResult 반환
        """
        pass

    async def get_result(self, job_id: str) -> dict:
        """
        추론 Job 상태 및 결과 조회.

        구현 세부사항:
        - self._job_store.get(job_id) → None이면 KeyError(→ 404)
        - 상태별 반환:
          - "pending"/"running": { jobId, status, createdAt }
          - "completed": { jobId, status, createdAt, completedAt, result: ReasonerResult }
          - "failed": { jobId, status, createdAt, completedAt, error: str }
        """
        pass
