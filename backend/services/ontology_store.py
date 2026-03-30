"""
services/ontology_store.py — Oxigraph RDF Triple Store SPARQL 래퍼

Named Graph 관리 규칙:
  - TBox (스키마):      <{ontology_iri}/tbox>
  - ABox (인스턴스):    <{source_id}/{timestamp}>
  - 추론 결과:          <{ontology_iri}/inferred>
  - Provenance 메타:    <{ontology_iri}/prov>
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import pyoxigraph
from pyoxigraph import (
    NamedNode,
    Literal as RDFLiteral,
    BlankNode,
    Quad,
    Store,
    RdfFormat,
)

from config import settings

logger = logging.getLogger(__name__)

# OWL / RDF 상수
OWL_ONTOLOGY = NamedNode("http://www.w3.org/2002/07/owl#Ontology")
OWL_CLASS = NamedNode("http://www.w3.org/2002/07/owl#Class")
OWL_NAMED_INDIVIDUAL = NamedNode("http://www.w3.org/2002/07/owl#NamedIndividual")
OWL_OBJECT_PROPERTY = NamedNode("http://www.w3.org/2002/07/owl#ObjectProperty")
OWL_DATATYPE_PROPERTY = NamedNode("http://www.w3.org/2002/07/owl#DatatypeProperty")
RDF_TYPE = NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
RDFS_LABEL = NamedNode("http://www.w3.org/2000/01/rdf-schema#label")
RDFS_COMMENT = NamedNode("http://www.w3.org/2000/01/rdf-schema#comment")
XSD_STRING = NamedNode("http://www.w3.org/2001/XMLSchema#string")


@dataclass
class Triple:
    """RDF 트리플 (subject, predicate, object)."""
    subject: NamedNode | BlankNode
    predicate: NamedNode
    object_: NamedNode | BlankNode | RDFLiteral


def _term_to_dict(term: Any) -> dict:
    """pyoxigraph 항 → SPARQL 결과 딕셔너리 변환."""
    if isinstance(term, NamedNode):
        return {"type": "uri", "value": str(term.value)}
    if isinstance(term, RDFLiteral):
        result: dict = {"type": "literal", "value": str(term.value)}
        if term.datatype:
            result["datatype"] = str(term.datatype.value)
        if term.language:
            result["xml:lang"] = term.language
        return result
    if isinstance(term, BlankNode):
        return {"type": "bnode", "value": str(term.value)}
    return {"type": "unknown", "value": str(term)}


class OntologyStore:
    """
    pyoxigraph.Store 래퍼.
    블로킹 호출은 모두 executor를 통해 스레드 풀에서 실행한다.
    """

    def __init__(self, path: str | None = None):
        if path:
            self._store = Store(path=path)
        else:
            self._store = Store()
        self._write_lock = asyncio.Lock()
        logger.info("OntologyStore initialized (path=%s)", path)

    # ── 내부 헬퍼 ─────────────────────────────────────────────────────────

    def _tbox_iri(self, ontology_iri: str) -> NamedNode:
        return NamedNode(f"{ontology_iri}/tbox")

    def _inferred_iri(self, ontology_iri: str) -> NamedNode:
        return NamedNode(f"{ontology_iri}/inferred")

    async def _run(self, fn, *args):
        """블로킹 함수를 executor에서 실행."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, fn, *args)

    # ── SPARQL 읽기 ───────────────────────────────────────────────────────

    async def sparql_select(self, query: str) -> list[dict]:
        """
        SPARQL SELECT 실행 → [{변수명: {type, value, ...}}] 반환.
        타임아웃: settings.sparql_timeout_seconds
        """
        def _exec():
            results = self._store.query(query)
            # variables는 results에 있음; 변수명에서 앞의 '?' 제거
            var_names = [str(v).lstrip("?") for v in results.variables]
            rows = []
            for solution in results:
                row = {}
                for i, name in enumerate(var_names):
                    term = solution[i]
                    if term is not None:
                        row[name] = _term_to_dict(term)
                rows.append(row)
            return rows

        return await asyncio.wait_for(
            self._run(_exec),
            timeout=settings.sparql_timeout_seconds,
        )

    async def sparql_ask(self, query: str) -> bool:
        """SPARQL ASK 실행 → bool 반환."""
        def _exec():
            return bool(self._store.query(query))

        return await asyncio.wait_for(
            self._run(_exec),
            timeout=settings.sparql_timeout_seconds,
        )

    async def sparql_construct(self, query: str) -> list[Triple]:
        """SPARQL CONSTRUCT 실행 → Triple 목록 반환."""
        def _exec():
            triples = []
            for triple in self._store.query(query):
                triples.append(Triple(triple.subject, triple.predicate, triple.object))
            return triples

        return await asyncio.wait_for(
            self._run(_exec),
            timeout=settings.sparql_timeout_seconds,
        )

    # ── SPARQL 쓰기 ───────────────────────────────────────────────────────

    async def sparql_update(self, update: str) -> None:
        """
        SPARQL UPDATE 실행 (INSERT/DELETE 등).
        asyncio.Lock으로 동시 쓰기 직렬화.
        """
        async with self._write_lock:
            await self._run(self._store.update, update)

    # ── 트리플 배치 삽입 ──────────────────────────────────────────────────

    async def insert_triples(self, graph_iri: str, triples: list[Triple]) -> None:
        """Named Graph에 트리플 배치 삽입."""
        graph_node = NamedNode(graph_iri)

        def _exec():
            quads = [
                Quad(t.subject, t.predicate, t.object_, graph_node)
                for t in triples
            ]
            self._store.extend(quads)

        async with self._write_lock:
            await self._run(_exec)

    # ── Named Graph 삭제 ──────────────────────────────────────────────────

    async def delete_graph(self, graph_iri: str) -> None:
        """Named Graph와 그 안의 모든 트리플 삭제 (idempotent)."""
        node = NamedNode(graph_iri)

        def _exec():
            try:
                self._store.remove_graph(node)
            except Exception:
                pass  # 존재하지 않으면 무시

        async with self._write_lock:
            await self._run(_exec)

    # ── Turtle 직렬화 ─────────────────────────────────────────────────────

    async def export_turtle(self, tbox_iri: str) -> str:
        """TBox Named Graph를 Turtle 문자열로 직렬화."""
        import io
        graph_node = NamedNode(tbox_iri)

        def _exec():
            buf = io.BytesIO()
            self._store.dump(buf, RdfFormat.TURTLE, from_graph=graph_node)
            return buf.getvalue().decode("utf-8")

        return await self._run(_exec)

    async def export_rdfxml(self, tbox_iri: str) -> bytes:
        """TBox Named Graph를 RDF/XML bytes로 직렬화."""
        import io
        graph_node = NamedNode(tbox_iri)

        def _exec():
            buf = io.BytesIO()
            self._store.dump(buf, RdfFormat.RDF_XML, from_graph=graph_node)
            return buf.getvalue()

        return await self._run(_exec)

    # ── 온톨로지 목록 ─────────────────────────────────────────────────────

    async def list_ontologies(self, page: int = 1, page_size: int = 20) -> tuple[list[dict], int]:
        """
        owl:Ontology 목록 조회.
        반환: (items, total)
        """
        offset = (page - 1) * page_size

        count_q = """
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            SELECT (COUNT(DISTINCT ?o) AS ?cnt) WHERE {
                GRAPH ?g { ?o a owl:Ontology }
            }
        """
        select_q = f"""
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX dc: <http://purl.org/dc/terms/>
            SELECT DISTINCT ?iri ?id ?label ?version WHERE {{
                GRAPH ?g {{
                    ?iri a owl:Ontology .
                    OPTIONAL {{ ?iri dc:identifier ?id }}
                    OPTIONAL {{ ?iri rdfs:label ?label }}
                    OPTIONAL {{ ?iri owl:versionInfo ?version }}
                }}
            }}
            ORDER BY ?iri
            LIMIT {page_size} OFFSET {offset}
        """

        count_rows, items_rows = await asyncio.gather(
            self.sparql_select(count_q),
            self.sparql_select(select_q),
        )

        total = int(count_rows[0]["cnt"]["value"]) if count_rows else 0
        items = [
            {
                "iri": r["iri"]["value"],
                "id": r.get("id", {}).get("value", ""),
                "label": r.get("label", {}).get("value", ""),
                "version": r.get("version", {}).get("value"),
            }
            for r in items_rows
        ]
        return items, total

    # ── 통계 ──────────────────────────────────────────────────────────────

    async def get_ontology_stats(self, tbox_iri: str) -> dict:
        """
        온톨로지 TBox Named Graph 기반 통계 집계.
        asyncio.gather로 병렬 실행.
        """
        g = f"<{tbox_iri}>"

        def _count_q(rdf_type: str) -> str:
            return f"""
                PREFIX owl: <http://www.w3.org/2002/07/owl#>
                SELECT (COUNT(?x) AS ?cnt) WHERE {{ GRAPH {g} {{ ?x a {rdf_type} }} }}
            """

        named_graphs_q = f"""
            SELECT (COUNT(DISTINCT ?g) AS ?cnt) WHERE {{ GRAPH ?g {{ ?s ?p ?o }}
            FILTER(STRSTARTS(STR(?g), "{tbox_iri.replace('/tbox', '')}")) }}
        """

        # Individuals는 tbox가 아닌 abox(manual/source) 그래프에 저장되므로
        # GRAPH ?g로 전체 그래프에서 조회
        individual_count_q = """
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            SELECT (COUNT(DISTINCT ?x) AS ?cnt) WHERE { GRAPH ?g { ?x a owl:NamedIndividual } }
        """

        results = await asyncio.gather(
            self.sparql_select(_count_q("owl:Class")),
            self.sparql_select(individual_count_q),
            self.sparql_select(_count_q("owl:ObjectProperty")),
            self.sparql_select(_count_q("owl:DatatypeProperty")),
            self.sparql_select(named_graphs_q),
        )

        def _cnt(rows: list[dict]) -> int:
            return int(rows[0]["cnt"]["value"]) if rows else 0

        return {
            "concepts": _cnt(results[0]),
            "individuals": _cnt(results[1]),
            "object_properties": _cnt(results[2]),
            "data_properties": _cnt(results[3]),
            "named_graphs": _cnt(results[4]),
        }
