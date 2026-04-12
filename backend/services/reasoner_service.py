"""
services/reasoner_service.py — owlready2 + HermiT OWL 2 추론 서비스

추론 실행 흐름:
  1. Oxigraph에서 온톨로지 소속 Named Graph 목록 조회 (H2: 다중 그래프 통합)
  2. SPARQL CONSTRUCT → rdflib Graph → RDF/XML 임시 파일
  3. owlready2 추론기 실행 (M1: profile별 분기)
  4. 추론 결과(inferred triples) → Oxigraph inferred Named Graph에 저장
  5. M2: SPARQL 기반 TransitiveProperty/InverseOf 추론 규칙 적용
  6. SPARQL 기반 위반 검출 (M3: FunctionalProperty/minCardinality/inverseOf 추가)
  7. entity_iris 지정 시 해당 엔티티 관련 위반/추론만 응답에 포함 (H1)

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
from services.job_store import JobStore

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ReasonerService:
    """owlready2 HermiT 추론기 서비스."""

    def __init__(self, ontology_store: Any):
        self._store = ontology_store
        self._job_store = JobStore()   # H3: SQLite 영속 저장
        self._lock = asyncio.Lock()

    async def run(
        self,
        ontology_id: str,
        entity_iris: list[str] | None = None,
        reasoner_profile: str = "OWL_DL",
        dataset: str | None = None,
    ) -> str:
        """추론 실행 (비동기) → job_id 즉시 반환."""
        job_id = str(uuid4())
        await self._job_store.create(job_id, ontology_id)
        asyncio.create_task(
            self._execute(job_id, ontology_id, entity_iris, reasoner_profile, dataset)
        )
        return job_id

    async def _execute(
        self,
        job_id: str,
        ontology_id: str,
        entity_iris: list[str] | None,
        reasoner_profile: str = "OWL_DL",
        dataset: str | None = None,
    ) -> None:
        """실제 추론 실행 (백그라운드 태스크)."""
        await self._job_store.update(job_id, status="running")
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

            # H2: 온톨로지 소속 Named Graph 전체 목록 조회 (/inferred 제외)
            ont_graphs = await self._get_ont_graphs(ont_iri, dataset)
            logger.info("Reasoner job %s: found %d named graph(s) for %s [profile=%s]",
                        job_id, len(ont_graphs), ont_iri, reasoner_profile)

            # H2: 모든 그래프 트리플 합산 → RDF/XML 임시 파일
            rdfxml_bytes = await self._build_combined_rdfxml(ont_graphs, dataset)

            with tempfile.NamedTemporaryFile(suffix=".owl", delete=False) as f:
                f.write(rdfxml_bytes)
                tmp_path = f.name

            # M1: 프로파일에 따라 추론기 선택
            loop = asyncio.get_event_loop()
            async with self._lock:
                result = await loop.run_in_executor(
                    None, self._dispatch_reasoner, tmp_path, reasoner_profile
                )

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

            # M2: SPARQL 기반 추론 규칙 (TransitiveProperty / InverseOf)
            sparql_axioms = await self._apply_sparql_inference_rules(ont_iri, dataset=dataset)
            if sparql_axioms:
                all_axioms = result.inferred_axioms + sparql_axioms
                result = result.model_copy(update={"inferred_axioms": all_axioms})

            # SPARQL 기반 위반 검출 (H2: ont_iri로 전체 그래프 검색)
            # M3: FunctionalProperty / minCardinality / inverseOf 추가
            violations_extra = await asyncio.gather(
                self._detect_cardinality_violations(ont_iri, dataset=dataset),
                self._detect_domain_range_violations(ont_iri, dataset=dataset),
                self._detect_disjoint_violations(ont_iri, dataset=dataset),
                self._detect_functional_property_violations(ont_iri, dataset=dataset),
                self._detect_min_cardinality_violations(ont_iri, dataset=dataset),
                self._detect_inverse_of_violations(ont_iri, dataset=dataset),
            )
            extra: list[ReasonerViolation] = []
            for vlist in violations_extra:
                extra.extend(vlist)

            if extra:
                all_violations = result.violations + extra
                consistent = result.consistent and not extra
                result = result.model_copy(
                    update={"violations": all_violations, "consistent": consistent}
                )

            # H1: entity_iris 지정 시 해당 엔티티 관련 결과만 필터링
            if entity_iris:
                result = self._filter_by_entities(result, entity_iris)

            await self._job_store.update(
                job_id,
                status="completed",
                result=result.model_dump(),
                completed_at=_now_iso(),
            )

        except Exception as exc:
            logger.exception("Reasoner job %s failed", job_id)
            await self._job_store.update(
                job_id,
                status="failed",
                error=str(exc),
                completed_at=_now_iso(),
            )
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    # ── H2 헬퍼: Named Graph 목록 조회 ────────────────────────────────────────

    async def _get_ont_graphs(self, ont_iri: str, dataset: str | None) -> list[str]:
        """온톨로지 소속 Named Graph 목록 조회 (/inferred 제외)."""
        rows = await self._store.sparql_select(f"""
            SELECT DISTINCT ?g WHERE {{
                GRAPH ?g {{ ?s ?p ?o }}
                FILTER(STRSTARTS(STR(?g), "{ont_iri}"))
                FILTER(!STRENDS(STR(?g), "/inferred"))
            }}
        """, dataset=dataset)
        graphs = [r["g"]["value"] for r in rows]
        return graphs or [f"{ont_iri}/kg"]  # 아무것도 없으면 기본 /kg fallback

    # ── H2 헬퍼: 다중 그래프 합산 → RDF/XML ─────────────────────────────────

    async def _build_combined_rdfxml(self, ont_graphs: list[str], dataset: str | None) -> bytes:
        """여러 Named Graph 트리플을 rdflib로 합산 후 RDF/XML 직렬화."""
        import rdflib

        combined = rdflib.Graph()
        for graph_iri in ont_graphs:
            try:
                ttl = await self._store.export_turtle(graph_iri, dataset=dataset)
                combined.parse(data=ttl, format="turtle")
            except Exception as e:
                logger.warning("Failed to export graph <%s>: %s", graph_iri, e)

        xml_str = combined.serialize(format="xml")
        return xml_str.encode("utf-8") if isinstance(xml_str, str) else xml_str

    # ── H1 헬퍼: entity_iris 기준 결과 필터링 ───────────────────────────────

    @staticmethod
    def _filter_by_entities(result: ReasonerResult, entity_iris: list[str]) -> ReasonerResult:
        """violations/inferred_axioms를 entity_iris에 포함된 IRI 기준으로 필터링."""
        iri_set = set(entity_iris)
        filtered_violations = [v for v in result.violations if v.subject_iri in iri_set]
        filtered_inferred = [
            a for a in result.inferred_axioms
            if a.subject in iri_set or a.object in iri_set
        ]
        consistent = not any(
            v.type in ("UnsatisfiableClass", "DisjointViolation") for v in filtered_violations
        )
        return result.model_copy(update={
            "violations": filtered_violations,
            "inferred_axioms": filtered_inferred,
            "consistent": consistent,
        })

    # ── M1: 프로파일별 추론기 분기 (sync) ────────────────────────────────────

    def _dispatch_reasoner(self, owl_path: str, profile: str = "OWL_DL") -> ReasonerResult:
        """Profile에 따라 추론기 선택 (sync, run_in_executor에서 호출)."""
        if profile in ("OWL_RL", "OWL_QL"):
            # SPARQL rule-based only — owlready2 skip
            logger.info("Profile %s: skipping owlready2, SPARQL rules only", profile)
            return ReasonerResult(
                consistent=True, violations=[], inferred_axioms=[], execution_ms=0
            )
        elif profile == "OWL_EL":
            return self._run_pellet(owl_path)
        else:  # OWL_DL (default)
            return self._run_hermit(owl_path)

    def _run_pellet(self, owl_path: str) -> ReasonerResult:
        """Pellet 추론기 동기 실행 (OWL_EL 프로파일)."""
        import owlready2  # type: ignore

        start = time.perf_counter()
        onto = owlready2.get_ontology(f"file://{owl_path}").load()
        pre_triples: set[tuple] = set(onto.get_triples())

        try:
            with onto:
                owlready2.sync_reasoner_pellet(infer_property_values=False)
        except (TypeError, Exception) as e:
            logger.debug("Pellet reasoning warning: %s", e)

        return self._collect_reasoner_results(onto, pre_triples, start)

    def _run_hermit(self, owl_path: str) -> ReasonerResult:
        """HermiT 추론기 동기 실행 (OWL_DL 프로파일)."""
        import owlready2  # type: ignore

        start = time.perf_counter()
        onto = owlready2.get_ontology(f"file://{owl_path}").load()
        pre_triples: set[tuple] = set(onto.get_triples())

        try:
            with onto:
                # infer_property_values=True 는 owlready2 0.46에서 알려진 버그
                # M2에서 SPARQL TransitiveProperty/InverseOf 규칙으로 보완
                owlready2.sync_reasoner_hermit(infer_property_values=False)
        except TypeError:
            pass

        return self._collect_reasoner_results(onto, pre_triples, start)

    def _collect_reasoner_results(
        self, onto: Any, pre_triples: set[tuple], start: float
    ) -> ReasonerResult:
        """owlready2 추론 후 violations/inferred_axioms 수집."""
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
                    for t2 in types[i + 1:]:
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
            world = onto.world
            post_triples: set[tuple] = set(onto.get_triples())
            for s, p, o in post_triples - pre_triples:
                s_iri = world._unabbreviate(s) if isinstance(s, int) else str(s)
                p_iri = world._unabbreviate(p) if isinstance(p, int) else str(p)
                o_iri = world._unabbreviate(o) if isinstance(o, int) else str(o)
                if s_iri.startswith("http") and p_iri.startswith("http"):
                    inferred_axioms.append(
                        InferredAxiom(
                            subject=s_iri,
                            predicate=p_iri,
                            object=o_iri,
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

    # ── M2: SPARQL 기반 추론 규칙 ─────────────────────────────────────────────

    async def _apply_sparql_inference_rules(
        self, ont_iri: str, dataset: str | None = None
    ) -> list[InferredAxiom]:
        """TransitiveProperty / InverseOf SPARQL 추론 규칙 적용.

        owlready2의 infer_property_values 버그를 SPARQL로 보완.
        새로 추론된 트리플은 {ont_iri}/inferred Named Graph에 저장.
        """
        from services.ontology_store import Triple
        from rdflib import URIRef

        inferred_graph = f"{ont_iri}/inferred"
        axioms: list[InferredAxiom] = []

        # 1) TransitiveProperty 목록 조회
        trans_rows = await self._store.sparql_select(f"""{self._SPARQL_PREFIX}
SELECT DISTINCT ?p WHERE {{
    GRAPH ?_tbox {{ ?p a owl:TransitiveProperty }}
    FILTER(STRSTARTS(STR(?_tbox), "{ont_iri}"))
    FILTER(!STRENDS(STR(?_tbox), "/inferred"))
}}""", dataset=dataset)

        for row in trans_rows:
            prop_iri = row["p"]["value"]
            # SPARQL property path로 추이 클로저 계산 (직접 단언된 트리플 제외)
            pairs = await self._store.sparql_select(f"""
SELECT DISTINCT ?a ?c WHERE {{
    ?a <{prop_iri}>+ ?c .
    FILTER(?a != ?c)
    FILTER NOT EXISTS {{ ?a <{prop_iri}> ?c }}
}}""", dataset=dataset)

            triples: list[Triple] = []
            for pair in pairs:
                a_iri = pair["a"]["value"]
                c_iri = pair["c"]["value"]
                axioms.append(InferredAxiom(
                    subject=a_iri,
                    predicate=prop_iri,
                    object=c_iri,
                    inference_rule="TransitiveProperty",
                ))
                try:
                    triples.append(Triple(
                        subject=URIRef(a_iri),
                        predicate=URIRef(prop_iri),
                        object_=URIRef(c_iri),
                    ))
                except Exception:
                    pass

            if triples:
                await self._store.insert_triples(inferred_graph, triples, dataset=dataset)

        # 2) InverseOf 역방향 트리플 생성
        inv_rows = await self._store.sparql_select(f"""{self._SPARQL_PREFIX}
SELECT DISTINCT ?p ?q ?a ?b WHERE {{
    GRAPH ?_tbox {{ ?p owl:inverseOf ?q }}
    FILTER(STRSTARTS(STR(?_tbox), "{ont_iri}"))
    FILTER(!STRENDS(STR(?_tbox), "/inferred"))
    ?a ?p ?b .
    FILTER(isIRI(?a)) FILTER(isIRI(?b))
    FILTER NOT EXISTS {{ ?b ?q ?a }}
}}""", dataset=dataset)

        inv_triples: list[Triple] = []
        for row in inv_rows:
            b_iri = row["b"]["value"]
            q_iri = row["q"]["value"]
            a_iri = row["a"]["value"]
            axioms.append(InferredAxiom(
                subject=b_iri,
                predicate=q_iri,
                object=a_iri,
                inference_rule="InverseOf",
            ))
            try:
                inv_triples.append(Triple(
                    subject=URIRef(b_iri),
                    predicate=URIRef(q_iri),
                    object_=URIRef(a_iri),
                ))
            except Exception:
                pass

        if inv_triples:
            await self._store.insert_triples(inferred_graph, inv_triples, dataset=dataset)

        return axioms

    # ── SPARQL 기반 위반 검출 ──────────────────────────────────────────────────

    _SPARQL_PREFIX = """
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
"""

    async def _detect_cardinality_violations(
        self, ont_iri: str, dataset: str | None = None
    ) -> list[ReasonerViolation]:
        """owl:maxCardinality / owl:exactCardinality 위반 검출 (SPARQL).
        H2: GRAPH ?g_tbox로 ont_iri 소속 전체 그래프에서 TBox 검색."""
        violations: list[ReasonerViolation] = []

        restriction_rows = await self._store.sparql_select(f"""{self._SPARQL_PREFIX}
SELECT DISTINCT ?cls ?prop ?n ?rtype WHERE {{
    GRAPH ?_tbox {{
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
    FILTER(STRSTARTS(STR(?_tbox), "{ont_iri}"))
    FILTER(!STRENDS(STR(?_tbox), "/inferred"))
}}""", dataset=dataset)

        for r in restriction_rows:
            cls_iri = r["cls"]["value"]
            prop_iri = r["prop"]["value"]
            rtype = r["rtype"]["value"]
            try:
                max_n = int(r["n"]["value"])
            except (ValueError, KeyError):
                continue

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
        self, ont_iri: str, dataset: str | None = None
    ) -> list[ReasonerViolation]:
        """rdfs:domain / rdfs:range 위반 검출 (SPARQL).
        H2: GRAPH ?g_tbox로 ont_iri 소속 전체 그래프에서 TBox 검색."""
        violations: list[ReasonerViolation] = []

        domain_rows = await self._store.sparql_select(f"""{self._SPARQL_PREFIX}
SELECT DISTINCT ?ind ?prop ?domain WHERE {{
    GRAPH ?_tbox {{ ?prop rdfs:domain ?domain . }}
    FILTER(STRSTARTS(STR(?_tbox), "{ont_iri}"))
    FILTER(!STRENDS(STR(?_tbox), "/inferred"))
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

        range_rows = await self._store.sparql_select(f"""{self._SPARQL_PREFIX}
SELECT DISTINCT ?ind ?prop ?range ?val WHERE {{
    GRAPH ?_tbox {{ ?prop rdfs:range ?range . }}
    FILTER(STRSTARTS(STR(?_tbox), "{ont_iri}"))
    FILTER(!STRENDS(STR(?_tbox), "/inferred"))
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
        self, ont_iri: str, dataset: str | None = None
    ) -> list[ReasonerViolation]:
        """owl:disjointWith 위반 검출 (SPARQL).
        H2: GRAPH ?_tbox로 ont_iri 소속 전체 그래프에서 TBox 검색."""
        violations: list[ReasonerViolation] = []

        rows = await self._store.sparql_select(f"""{self._SPARQL_PREFIX}
SELECT DISTINCT ?ind ?c1 ?c2 WHERE {{
    {{
        GRAPH ?_tbox1 {{ ?c1 owl:disjointWith ?c2 . }}
        FILTER(STRSTARTS(STR(?_tbox1), "{ont_iri}"))
        FILTER(!STRENDS(STR(?_tbox1), "/inferred"))
    }} UNION {{
        GRAPH ?_tbox2 {{ ?c2 owl:disjointWith ?c1 . }}
        FILTER(STRSTARTS(STR(?_tbox2), "{ont_iri}"))
        FILTER(!STRENDS(STR(?_tbox2), "/inferred"))
    }}
    GRAPH ?g1 {{ ?ind a ?c1 . FILTER(isIRI(?ind)) }}
    GRAPH ?g2 {{ ?ind a ?c2 . }}
    FILTER(?c1 != ?c2)
    FILTER(STR(?c1) < STR(?c2))
}}""", dataset=dataset)

        logger.debug("_detect_disjoint_violations: ont=%s rows=%d", ont_iri, len(rows))

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

    async def _detect_functional_property_violations(
        self, ont_iri: str, dataset: str | None = None
    ) -> list[ReasonerViolation]:
        """owl:FunctionalProperty 위반 검출 — 동일 개체에 2개 이상의 값 (SPARQL).
        M3 신규."""
        violations: list[ReasonerViolation] = []

        rows = await self._store.sparql_select(f"""{self._SPARQL_PREFIX}
SELECT ?ind ?prop (COUNT(DISTINCT ?val) AS ?cnt) WHERE {{
    GRAPH ?_tbox {{ ?prop a owl:FunctionalProperty }}
    FILTER(STRSTARTS(STR(?_tbox), "{ont_iri}"))
    FILTER(!STRENDS(STR(?_tbox), "/inferred"))
    GRAPH ?g {{ ?ind ?prop ?val . FILTER(isIRI(?ind)) }}
}}
GROUP BY ?ind ?prop
HAVING (COUNT(DISTINCT ?val) > 1)
""", dataset=dataset)

        for r in rows:
            ind_iri = r["ind"]["value"]
            prop_iri = r["prop"]["value"]
            try:
                cnt = int(r["cnt"]["value"])
            except (ValueError, KeyError):
                cnt = 2
            violations.append(
                ReasonerViolation(
                    type="FunctionalPropertyViolation",
                    subject_iri=ind_iri,
                    description=(
                        f"<{ind_iri}>: FunctionalProperty <{prop_iri}> "
                        f"has {cnt} values (must be at most 1)"
                    ),
                )
            )

        return violations

    async def _detect_min_cardinality_violations(
        self, ont_iri: str, dataset: str | None = None
    ) -> list[ReasonerViolation]:
        """owl:minCardinality 위반 검출 — 개체의 프로퍼티 값 수가 최소치 미달 (SPARQL).
        M3 신규."""
        violations: list[ReasonerViolation] = []

        rows = await self._store.sparql_select(f"""{self._SPARQL_PREFIX}
SELECT ?cls ?prop ?n ?ind (COUNT(DISTINCT ?val) AS ?cnt) WHERE {{
    GRAPH ?_tbox {{
        ?cls rdfs:subClassOf ?restr .
        ?restr a owl:Restriction ; owl:onProperty ?prop ; owl:minCardinality ?n .
    }}
    FILTER(STRSTARTS(STR(?_tbox), "{ont_iri}"))
    FILTER(!STRENDS(STR(?_tbox), "/inferred"))
    GRAPH ?g {{ ?ind a ?cls . FILTER(isIRI(?ind)) }}
    OPTIONAL {{ GRAPH ?g2 {{ ?ind ?prop ?val }} }}
}}
GROUP BY ?cls ?prop ?n ?ind
""", dataset=dataset)

        for r in rows:
            try:
                min_n = int(r["n"]["value"])
                cnt = int(r["cnt"]["value"])
                ind_iri = r["ind"]["value"]
                prop_iri = r["prop"]["value"]
            except (ValueError, KeyError):
                continue

            if cnt < min_n:
                violations.append(
                    ReasonerViolation(
                        type="CardinalityViolation",
                        subject_iri=ind_iri,
                        description=(
                            f"<{ind_iri}>: <{prop_iri}> has {cnt} values "
                            f"(minCardinality={min_n})"
                        ),
                    )
                )

        return violations

    async def _detect_inverse_of_violations(
        self, ont_iri: str, dataset: str | None = None
    ) -> list[ReasonerViolation]:
        """owl:inverseOf 비일관성 검출 — A p B 존재하나 B q A 없음 (SPARQL).
        M3 신규."""
        violations: list[ReasonerViolation] = []

        rows = await self._store.sparql_select(f"""{self._SPARQL_PREFIX}
SELECT DISTINCT ?a ?p ?b ?q WHERE {{
    GRAPH ?_tbox {{ ?p owl:inverseOf ?q }}
    FILTER(STRSTARTS(STR(?_tbox), "{ont_iri}"))
    FILTER(!STRENDS(STR(?_tbox), "/inferred"))
    ?a ?p ?b .
    FILTER(isIRI(?a)) FILTER(isIRI(?b))
    FILTER NOT EXISTS {{ ?b ?q ?a }}
}}""", dataset=dataset)

        for r in rows:
            a_iri = r["a"]["value"]
            b_iri = r["b"]["value"]
            p_iri = r["p"]["value"]
            q_iri = r["q"]["value"]
            violations.append(
                ReasonerViolation(
                    type="InverseOfViolation",
                    subject_iri=a_iri,
                    description=(
                        f"<{a_iri}> <{p_iri}> <{b_iri}> exists "
                        f"but inverse <{b_iri}> <{q_iri}> <{a_iri}> is missing"
                    ),
                )
            )

        return violations

    async def get_result(self, job_id: str) -> dict:
        """추론 Job 상태 및 결과 조회."""
        job = await self._job_store.get(job_id)
        if job is None:
            raise KeyError(f"Job {job_id} not found")

        base: dict = {
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

    async def list_jobs(self, ontology_id: str) -> list[dict]:
        """온톨로지 소속 Job 목록 조회."""
        return await self._job_store.list_by_ontology(ontology_id)

    async def cleanup_expired_jobs(self) -> int:
        """7일 이상 된 완료/실패 Job 삭제."""
        return await self._job_store.cleanup_expired()
