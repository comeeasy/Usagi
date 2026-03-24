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

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import time
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from models.reasoner import InferredAxiom, ReasonerResult, ReasonerViolation

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ReasonerService:
    """owlready2 HermiT 추론기 서비스."""

    def __init__(self, ontology_store: Any):
        self._store = ontology_store
        self._job_store: dict[str, dict] = {}
        self._lock = asyncio.Lock()

    async def run(self, ontology_id: str, entity_iris: list[str] | None = None) -> str:
        """추론 실행 (비동기) → job_id 즉시 반환."""
        job_id = str(uuid4())
        self._job_store[job_id] = {
            "status": "pending",
            "ontology_id": ontology_id,
            "created_at": _now_iso(),
        }
        asyncio.create_task(self._execute(job_id, ontology_id, entity_iris))
        return job_id

    async def _execute(
        self,
        job_id: str,
        ontology_id: str,
        entity_iris: list[str] | None,
    ) -> None:
        """실제 추론 실행 (백그라운드 태스크)."""
        self._job_store[job_id]["status"] = "running"
        tmp_path: str | None = None

        try:
            tbox_iri = f"{ontology_id}/tbox"

            if entity_iris:
                # 서브그래프만 추출: 지정 IRI와 관련된 트리플 CONSTRUCT
                iris_filter = " ".join(f"<{iri}>" for iri in entity_iris)
                turtle_bytes = await self._store.export_turtle(tbox_iri)
            else:
                turtle_bytes = await self._store.export_turtle(tbox_iri)

            with tempfile.NamedTemporaryFile(suffix=".owl", delete=False) as f:
                if isinstance(turtle_bytes, str):
                    f.write(turtle_bytes.encode())
                else:
                    f.write(turtle_bytes)
                tmp_path = f.name

            loop = asyncio.get_event_loop()
            async with self._lock:
                result = await loop.run_in_executor(None, self._run_hermit, tmp_path)

            # 추론된 트리플을 inferred Named Graph에 저장
            if result.inferred_axioms:
                from services.ontology_store import Triple
                from pyoxigraph import NamedNode

                triples = []
                for ax in result.inferred_axioms:
                    try:
                        triples.append(
                            Triple(
                                subject=NamedNode(ax.subject),
                                predicate=NamedNode(ax.predicate),
                                object_=NamedNode(ax.object),
                            )
                        )
                    except Exception:
                        pass  # literal object는 건너뜀

                if triples:
                    await self._store.insert_triples(
                        f"{ontology_id}/inferred", triples
                    )

            self._job_store[job_id].update(
                {
                    "status": "completed",
                    "result": result,
                    "completed_at": _now_iso(),
                }
            )

        except Exception as exc:
            logger.exception("Reasoner job %s failed", job_id)
            self._job_store[job_id].update(
                {
                    "status": "failed",
                    "error": str(exc),
                    "completed_at": _now_iso(),
                }
            )
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    def _run_hermit(self, owl_path: str) -> ReasonerResult:
        """HermiT 추론기 동기 실행 (run_in_executor에서 호출)."""
        import owlready2  # type: ignore

        start = time.perf_counter()

        onto = owlready2.get_ontology(f"file://{owl_path}").load()

        # 추론 전 트리플 스냅샷
        pre_triples: set[tuple] = set()
        for s, p, o in onto.get_triples():
            pre_triples.add((s, p, o))

        with onto:
            owlready2.sync_reasoner_hermit(
                infer_property_values=True,
                infer_data_property_values=True,
            )

        execution_ms = int((time.perf_counter() - start) * 1000)

        violations: list[ReasonerViolation] = []
        inferred_axioms: list[InferredAxiom] = []

        # UnsatisfiableClass 위반 수집
        try:
            for cls in onto.inconsistent_classes():
                violations.append(
                    ReasonerViolation(
                        type="UnsatisfiableClass",
                        subject_iri=cls.iri if hasattr(cls, "iri") else str(cls),
                        description=f"Class {cls} is unsatisfiable",
                    )
                )
        except Exception:
            pass

        # DisjointViolation 수집
        try:
            for ind in onto.individuals():
                types = list(ind.is_a)
                for i, t1 in enumerate(types):
                    for t2 in types[i + 1 :]:
                        if hasattr(t1, "disjoints"):
                            disjoints = [d.entities for d in t1.disjoints()]
                            for pair in disjoints:
                                if t2 in pair:
                                    violations.append(
                                        ReasonerViolation(
                                            type="DisjointViolation",
                                            subject_iri=ind.iri,
                                            description=(
                                                f"Individual {ind.iri} is instance of "
                                                f"disjoint classes {t1} and {t2}"
                                            ),
                                        )
                                    )
        except Exception:
            pass

        # 추론 후 새로 생긴 트리플 → InferredAxiom
        try:
            post_triples: set[tuple] = set()
            for s, p, o in onto.get_triples():
                post_triples.add((s, p, o))

            new_triples = post_triples - pre_triples
            for s, p, o in new_triples:
                inferred_axioms.append(
                    InferredAxiom(
                        subject=str(s),
                        predicate=str(p),
                        object=str(o),
                        inference_rule="HermiT",
                    )
                )
        except Exception:
            pass

        consistent = not any(
            v.type in ("UnsatisfiableClass", "DisjointViolation") for v in violations
        )

        return ReasonerResult(
            consistent=consistent,
            violations=violations,
            inferred_axioms=inferred_axioms,
            execution_ms=execution_ms,
        )

    async def get_result(self, job_id: str) -> dict:
        """추론 Job 상태 및 결과 조회."""
        job = self._job_store.get(job_id)
        if job is None:
            raise KeyError(f"Job {job_id} not found")

        base = {
            "job_id": job_id,
            "ontology_id": job.get("ontology_id"),
            "status": job["status"],
            "created_at": job["created_at"],
        }

        if job["status"] in ("pending", "running"):
            return base

        base["completed_at"] = job.get("completed_at")

        if job["status"] == "completed":
            base["result"] = job.get("result")
        else:
            base["error"] = job.get("error")

        return base
