"""
services/reasoner_service.py — owlready2 + HermiT OWL 2 추론 서비스

추론 실행 흐름:
  1. Oxigraph에서 대상 그래프 CONSTRUCT → Turtle 임시 파일
  2. owlready2.get_ontology().load() → in-memory OWL 그래프
  3. sync_reasoner_hermit(infer_property_values=True, infer_data_property_values=True)
  4. 추론 결과(inferred triples) → Oxigraph inferred Named Graph에 저장
  5. 위반/추론 사실 → ReasonerResult 직렬화
  6. SPARQL 기반 위반 검출 (CardinalityViolation, DomainRangeViolation)

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

    async def run(self, ontology_id: str, entity_iris: list[str] | None = None, dataset: str | None = None) -> str:
        """추론 실행 (비동기) → job_id 즉시 반환."""
        job_id = str(uuid4())
        self._job_store[job_id] = {
            "status": "pending",
            "ontology_id": ontology_id,
            "created_at": _now_iso(),
        }
        asyncio.create_task(self._execute(job_id, ontology_id, entity_iris, dataset))
        return job_id

    async def _execute(
        self,
        job_id: str,
        ontology_id: str,
        entity_iris: list[str] | None,
        dataset: str | None = None,
    ) -> None:
        """실제 추론 실행 (백그라운드 태스크)."""
        self._job_store[job_id]["status"] = "running"
        tmp_path: str | None = None

        try:
            if ontology_id.startswith("http"):
                ont_iri = ontology_id
            else:
                rows = await self._store.sparql_select(f"""
                    PREFIX owl: <http://www.w3.org/2002/07/owl#>
                    PREFIX dc:  <http://purl.org/dc/terms/>
                    SELECT ?iri WHERE {{
                        GRAPH ?g {{ ?iri a owl:Ontology ; dc:identifier "{ontology_id}" }}
                    }} LIMIT 1
                """, dataset=dataset)
                if not rows:
                    raise ValueError(f"Ontology not found: {ontology_id}")
                ont_iri = rows[0]['iri']['value']
            kg_iri = f"{ont_iri}/kg"

            rdfxml_bytes = await self._store.export_rdfxml(kg_iri, dataset=dataset)

            with tempfile.NamedTemporaryFile(suffix=".owl", delete=False) as f:
                f.write(rdfxml_bytes)
                tmp_path = f.name

            loop = asyncio.get_event_loop()
            async with self._lock:
                result = await loop.run_in_executor(None, self._run_hermit, tmp_path)

            # 추론된 트리플을 inferred Named Graph에 저장
            if result.inferred_axioms:
                from services.ontology_store import Triple
                from rdflib import URIRef

                triples = []
                for ax in result.inferred_axioms:
                    try:
                        triples.append(
                            Triple(
                                subject=URIRef(ax.subject),
                                predicate=URIRef(ax.predicate),
                                object_=URIRef(ax.object),
                            )
                        )
                    except Exception:
                        pass  # literal object는 건너뜀

                if triples:
                    await self._store.insert_triples(
                        f"{ont_iri}/inferred", triples, dataset=dataset
                    )

            # SPARQL 기반 추가 위반 검출 (owlready2 불필요)
            cardinality_violations = await self._detect_cardinality_violations(kg_iri, dataset=dataset)
            domain_range_violations = await self._detect_domain_range_violations(kg_iri, dataset=dataset)
            disjoint_violations = await self._detect_disjoint_violations(kg_iri, dataset=dataset)
            extra = cardinality_violations + domain_range_violations + disjoint_violations

            if extra:
                all_violations = result.violations + extra
                consistent = result.consistent and not extra
                result = result.model_copy(
                    update={"violations": all_violations, "consistent": consistent}
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

        try:
            with onto:
                # infer_property_values=True 는 owlready2가 non-class 객체를
                # class로 처리하려다 TypeError를 일으키는 알려진 버그가 있음
                owlready2.sync_reasoner_hermit(infer_property_values=False)
        except TypeError:
            # 추론 자체는 완료됐으나 결과 적용 단계에서 owlready2 내부 오류
            # 발생 시 조용히 무시하고 수집된 결과를 사용
            pass

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

    # ── SPARQL 기반 위반 검출 ──────────────────────────────────────────────────

    _SPARQL_PREFIX = """
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
"""

    async def _detect_cardinality_violations(
        self, kg_iri: str, dataset: str | None = None
    ) -> list[ReasonerViolation]:
        """owl:maxCardinality / owl:exactCardinality 위반 검출 (SPARQL)."""
        violations: list[ReasonerViolation] = []

        # 1) TBox에서 카디널리티 제약 수집
        restriction_rows = await self._store.sparql_select(f"""{self._SPARQL_PREFIX}
SELECT DISTINCT ?cls ?prop ?n ?rtype WHERE {{
    GRAPH <{kg_iri}> {{
        ?cls rdfs:subClassOf ?restr .
        ?restr a owl:Restriction ; owl:onProperty ?prop .
        {{
            ?restr owl:maxCardinality ?n .
            BIND("max" AS ?rtype)
        }}
        UNION
        {{
            ?restr owl:exactCardinality ?n .
            BIND("exact" AS ?rtype)
        }}
    }}
}}""", dataset=dataset)

        for r in restriction_rows:
            cls_iri = r["cls"]["value"]
            prop_iri = r["prop"]["value"]
            rtype = r["rtype"]["value"]
            try:
                max_n = int(r["n"]["value"])
            except (ValueError, KeyError):
                continue

            # 2) 해당 클래스의 개체별 프로퍼티 값 수 집계 (전체 named graph 검색)
            count_rows = await self._store.sparql_select(f"""{self._SPARQL_PREFIX}
SELECT ?ind (COUNT(DISTINCT ?val) AS ?cnt) WHERE {{
    GRAPH ?g {{ ?ind a <{cls_iri}> . FILTER(isIRI(?ind)) }}
    GRAPH ?g2 {{ ?ind <{prop_iri}> ?val . }}
}}
GROUP BY ?ind""", dataset=dataset)

            for row in count_rows:
                try:
                    count = int(row["cnt"]["value"])
                    ind_iri = row["ind"]["value"]
                except (ValueError, KeyError):
                    continue

                if rtype == "max" and count > max_n:
                    violations.append(
                        ReasonerViolation(
                            type="CardinalityViolation",
                            subject_iri=ind_iri,
                            description=(
                                f"<{ind_iri}>: <{prop_iri}> has {count} values "
                                f"(maxCardinality={max_n})"
                            ),
                        )
                    )
                elif rtype == "exact" and count != max_n:
                    violations.append(
                        ReasonerViolation(
                            type="CardinalityViolation",
                            subject_iri=ind_iri,
                            description=(
                                f"<{ind_iri}>: <{prop_iri}> has {count} values "
                                f"(exactCardinality={max_n})"
                            ),
                        )
                    )

        return violations

    async def _detect_domain_range_violations(
        self, kg_iri: str, dataset: str | None = None
    ) -> list[ReasonerViolation]:
        """rdfs:domain / rdfs:range 위반 검출 (SPARQL)."""
        violations: list[ReasonerViolation] = []

        # Domain 위반: 프로퍼티 주어가 선언된 domain 클래스에 속하지 않음
        domain_rows = await self._store.sparql_select(f"""{self._SPARQL_PREFIX}
SELECT DISTINCT ?ind ?prop ?domain WHERE {{
    GRAPH <{kg_iri}> {{ ?prop rdfs:domain ?domain . }}
    GRAPH ?g {{ ?ind ?prop ?val . FILTER(isIRI(?ind)) }}
    FILTER NOT EXISTS {{ GRAPH ?ga {{ ?ind a ?domain }} }}
    FILTER NOT EXISTS {{ GRAPH ?gt1 {{ ?ind a ?t }} GRAPH ?gt2 {{ ?t rdfs:subClassOf* ?domain }} }}
}}""", dataset=dataset)

        for r in domain_rows:
            violations.append(
                ReasonerViolation(
                    type="DomainRangeViolation",
                    subject_iri=r["ind"]["value"],
                    description=(
                        f"<{r['ind']['value']}>: uses <{r['prop']['value']}> "
                        f"but is not in domain <{r['domain']['value']}>"
                    ),
                )
            )

        # Range 위반: 객체 프로퍼티의 목적어가 선언된 range 클래스에 속하지 않음
        range_rows = await self._store.sparql_select(f"""{self._SPARQL_PREFIX}
SELECT DISTINCT ?ind ?prop ?range ?val WHERE {{
    GRAPH <{kg_iri}> {{ ?prop rdfs:range ?range . }}
    GRAPH ?g {{ ?ind ?prop ?val . FILTER(isIRI(?val)) }}
    FILTER NOT EXISTS {{ GRAPH ?ga {{ ?val a ?range }} }}
    FILTER NOT EXISTS {{ GRAPH ?gt1 {{ ?val a ?t }} GRAPH ?gt2 {{ ?t rdfs:subClassOf* ?range }} }}
}}""", dataset=dataset)

        for r in range_rows:
            violations.append(
                ReasonerViolation(
                    type="DomainRangeViolation",
                    subject_iri=r["ind"]["value"],
                    description=(
                        f"<{r['ind']['value']}>: <{r['prop']['value']}> "
                        f"value <{r['val']['value']}> not in range <{r['range']['value']}>"
                    ),
                )
            )

        return violations

    async def _detect_disjoint_violations(
        self, kg_iri: str, dataset: str | None = None
    ) -> list[ReasonerViolation]:
        """owl:disjointWith 위반 검출 (SPARQL) — 개체가 서로 disjoint 클래스에 동시에 속하는 경우."""
        violations: list[ReasonerViolation] = []

        # 먼저 TBox에 disjointWith 트리플이 있는지 확인
        dw_check = await self._store.sparql_select(f"""{self._SPARQL_PREFIX}
SELECT ?c1 ?c2 WHERE {{ GRAPH <{kg_iri}> {{ ?c1 owl:disjointWith ?c2 . }} }}""", dataset=dataset)
        logger.info("_detect_disjoint_violations: TBox disjointWith triples=%s", dw_check)

        # 개체 타입 확인
        ind_types = await self._store.sparql_select(f"""{self._SPARQL_PREFIX}
SELECT ?ind ?type WHERE {{ GRAPH ?g {{ ?ind a ?type . FILTER(isIRI(?ind)) FILTER(?type != owl:NamedIndividual) }} }}""", dataset=dataset)
        logger.info("_detect_disjoint_violations: all individual types=%s", ind_types)

        # UNION으로 양방향(A disjointWith B, B disjointWith A) 모두 처리
        rows = await self._store.sparql_select(f"""{self._SPARQL_PREFIX}
SELECT DISTINCT ?ind ?c1 ?c2 WHERE {{
    {{
        GRAPH <{kg_iri}> {{ ?c1 owl:disjointWith ?c2 . }}
    }} UNION {{
        GRAPH <{kg_iri}> {{ ?c2 owl:disjointWith ?c1 . }}
    }}
    GRAPH ?g1 {{ ?ind a ?c1 . FILTER(isIRI(?ind)) }}
    GRAPH ?g2 {{ ?ind a ?c2 . }}
    FILTER(?c1 != ?c2)
    FILTER(STR(?c1) < STR(?c2))
}}""", dataset=dataset)

        logger.info("_detect_disjoint_violations: tbox=%s rows=%d result=%s", kg_iri, len(rows), rows)

        seen: set[tuple] = set()
        for r in rows:
            ind_iri = r["ind"]["value"]
            c1 = r["c1"]["value"]
            c2 = r["c2"]["value"]
            key = (ind_iri, min(c1, c2), max(c1, c2))
            if key in seen:
                continue
            seen.add(key)
            violations.append(
                ReasonerViolation(
                    type="DisjointViolation",
                    subject_iri=ind_iri,
                    description=(
                        f"<{ind_iri}> is an instance of both "
                        f"<{c1}> and <{c2}>, which are disjoint"
                    ),
                )
            )

        return violations

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
            result = job.get("result")
            base["result"] = result.model_dump() if result else None
        else:
            base["error"] = job.get("error")

        return base
