"""
services/ontology_store.py — Apache Jena Fuseki SPARQL HTTP 래퍼

Named Graph 관리 규칙:
  - 온톨로지 본문(스키마+인스턴스): <{ontology_iri}/kg>
  - 추론 결과(선택):              <{ontology_iri}/inferred>

Fuseki HTTP 엔드포인트:
  - SPARQL Query  : POST {fuseki_url}/{dataset}/sparql   (application/sparql-query)
  - SPARQL Update : POST {fuseki_url}/{dataset}/update   (application/sparql-update)
  - GSP (Graph Store Protocol): GET/POST/PUT {fuseki_url}/{dataset}/data?graph=<iri>
    · POST = 그래프에 추가 · PUT = 그래프 전체 교체
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import httpx
from rdflib import URIRef, Literal, BNode

from config import settings

logger = logging.getLogger(__name__)


@dataclass
class Triple:
    """RDF 트리플 (subject, predicate, object)."""
    subject: URIRef | BNode
    predicate: URIRef
    object_: URIRef | BNode | Literal


def _term_to_dict(term: dict) -> dict:
    """Fuseki SPARQL JSON 결과 항 → 내부 딕셔너리 변환 (기존 API 호환)."""
    t = term.get("type", "")
    if t == "uri":
        return {"type": "uri", "value": term["value"]}
    if t == "literal":
        result: dict = {"type": "literal", "value": term["value"]}
        if "datatype" in term:
            result["datatype"] = term["datatype"]
        if "xml:lang" in term:
            result["xml:lang"] = term["xml:lang"]
        return result
    if t == "bnode":
        return {"type": "bnode", "value": term["value"]}
    return {"type": "unknown", "value": str(term)}


def _term_to_sparql(term: Any) -> str:
    """rdflib 항 → SPARQL 문자열 직렬화."""
    if isinstance(term, URIRef):
        return f"<{term}>"
    if isinstance(term, BNode):
        return f"_:{term}"
    if isinstance(term, Literal):
        escaped = (
            str(term)
            .replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
        )
        if term.language:
            return f'"{escaped}"@{term.language}'
        if term.datatype:
            return f'"{escaped}"^^<{term.datatype}>'
        return f'"{escaped}"'
    return f"<{term}>"


class OntologyStore:
    """
    Apache Jena Fuseki HTTP 클라이언트 래퍼.
    모든 I/O는 비동기(httpx.AsyncClient) 로 처리한다.

    dataset 파라미터를 각 메서드에 전달하면 해당 dataset으로 요청을 보낸다.
    생략하면 초기화 시 지정한 default dataset을 사용한다.
    """

    def __init__(self, fuseki_url: str, dataset: str = "ontology"):
        self._fuseki_base = fuseki_url
        self._default_dataset = dataset
        self._client = httpx.AsyncClient(
            timeout=settings.sparql_timeout_seconds,
            follow_redirects=True,
            auth=settings.fuseki_basic_auth(),
        )
        logger.info("OntologyStore initialized (fuseki=%s, dataset=%s)", fuseki_url, dataset)

    def _ds(self, dataset: str | None) -> str:
        return dataset or self._default_dataset

    def _query_url(self, dataset: str | None = None) -> str:
        return f"{self._fuseki_base}/{self._ds(dataset)}/sparql"

    def _update_url(self, dataset: str | None = None) -> str:
        return f"{self._fuseki_base}/{self._ds(dataset)}/update"

    def _gsp_url(self, dataset: str | None = None) -> str:
        return f"{self._fuseki_base}/{self._ds(dataset)}/data"

    async def close(self) -> None:
        await self._client.aclose()
        logger.info("OntologyStore closed.")

    # ── 내부 헬퍼 ─────────────────────────────────────────────────────────

    def _inferred_iri(self, ontology_iri: str) -> str:
        return f"{ontology_iri}/inferred"

    # ── SPARQL 읽기 ───────────────────────────────────────────────────────

    async def count_graph_triples(self, graph_iri: str, dataset: str | None = None) -> int:
        """Named Graph 안의 트리플 개수 (SPARQL COUNT). graph_iri는 임의 문자를 허용하도록 STR 비교."""
        esc = graph_iri.replace("\\", "\\\\").replace('"', '\\"')
        q = (
            "SELECT (COUNT(?s) AS ?cnt) WHERE { "
            f'GRAPH ?g {{ ?s ?p ?o }} FILTER(STR(?g) = "{esc}") '
            "}"
        )
        rows = await self.sparql_select(q, dataset)
        if not rows or "cnt" not in rows[0]:
            return 0
        return int(rows[0]["cnt"]["value"])

    async def sparql_select(self, query: str, dataset: str | None = None) -> list[dict]:
        """
        SPARQL SELECT 실행 → [{변수명: {type, value, ...}}] 반환.
        Fuseki가 반환하는 W3C SPARQL JSON 포맷을 파싱한다.
        """
        resp = await self._client.post(
            self._query_url(dataset),
            content=query.encode("utf-8"),
            headers={
                "Content-Type": "application/sparql-query",
                "Accept": "application/sparql-results+json",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        # W3C SPARQL JSON: variables live under head.vars, not results.vars
        vars_ = data.get("head", {}).get("vars", [])
        rows = []
        for binding in data.get("results", {}).get("bindings", []):
            row = {}
            for var in vars_:
                if var in binding:
                    row[var] = _term_to_dict(binding[var])
            rows.append(row)
        return rows

    async def sparql_ask(self, query: str, dataset: str | None = None) -> bool:
        """SPARQL ASK 실행 → bool 반환."""
        resp = await self._client.post(
            self._query_url(dataset),
            content=query.encode("utf-8"),
            headers={
                "Content-Type": "application/sparql-query",
                "Accept": "application/sparql-results+json",
            },
        )
        resp.raise_for_status()
        return resp.json().get("boolean", False)

    async def sparql_construct(self, query: str, dataset: str | None = None) -> list[Triple]:
        """SPARQL CONSTRUCT 실행 → Triple 목록 반환."""
        resp = await self._client.post(
            self._query_url(dataset),
            content=query.encode("utf-8"),
            headers={
                "Content-Type": "application/sparql-query",
                "Accept": "text/turtle",
            },
        )
        resp.raise_for_status()
        import rdflib
        g = rdflib.Graph()
        g.parse(data=resp.text, format="turtle")
        return [
            Triple(subject=s, predicate=p, object_=o)
            for s, p, o in g
        ]

    # ── SPARQL 쓰기 ───────────────────────────────────────────────────────

    async def sparql_update(self, update: str, dataset: str | None = None) -> None:
        """SPARQL UPDATE 실행 (INSERT DATA / DELETE / DROP 등)."""
        resp = await self._client.post(
            self._update_url(dataset),
            content=update.encode("utf-8"),
            headers={"Content-Type": "application/sparql-update"},
        )
        resp.raise_for_status()

    # ── 트리플 배치 삽입 ──────────────────────────────────────────────────

    async def insert_triples(self, graph_iri: str, triples: list[Triple], dataset: str | None = None) -> None:
        """Named Graph에 트리플 배치 삽입 (SPARQL INSERT DATA)."""
        if not triples:
            return
        lines = [
            f"    {_term_to_sparql(t.subject)} "
            f"{_term_to_sparql(t.predicate)} "
            f"{_term_to_sparql(t.object_)} ."
            for t in triples
        ]
        update = (
            f"INSERT DATA {{ GRAPH <{graph_iri}> {{\n"
            + "\n".join(lines)
            + "\n} }"
        )
        await self.sparql_update(update, dataset)

    # ── Named Graph 삭제 ──────────────────────────────────────────────────

    async def delete_graph(self, graph_iri: str, dataset: str | None = None) -> None:
        """Named Graph와 그 안의 모든 트리플 삭제 (idempotent)."""
        await self.sparql_update(f"DROP SILENT GRAPH <{graph_iri}>", dataset)

    # ── GSP 직렬화 ────────────────────────────────────────────────────────

    async def export_turtle(self, graph_iri: str, dataset: str | None = None) -> str:
        """Named Graph를 Turtle 문자열로 직렬화 (GSP GET)."""
        resp = await self._client.get(
            self._gsp_url(dataset),
            params={"graph": graph_iri},
            headers={"Accept": "text/turtle"},
        )
        resp.raise_for_status()
        return resp.text

    async def export_rdfxml(self, graph_iri: str, dataset: str | None = None) -> bytes:
        """Named Graph를 RDF/XML bytes로 직렬화 (GSP GET)."""
        resp = await self._client.get(
            self._gsp_url(dataset),
            params={"graph": graph_iri},
            headers={"Accept": "application/rdf+xml"},
        )
        resp.raise_for_status()
        return resp.content

    async def post_graph_rdf(
        self,
        graph_iri: str,
        body: bytes,
        content_type: str,
        dataset: str | None = None,
    ) -> None:
        """
        GSP HTTP POST — Named Graph에 RDF 본문을 Content-Type에 맞게 추가(merge).
        Fuseki/Jena가 지원하는 표준 시리얼라이제이션(Turtle, RDF/XML, NT, JSON-LD, TriG, N-Quads 등)에 사용.
        """
        resp = await self._client.post(
            self._gsp_url(dataset),
            params={"graph": graph_iri},
            content=body,
            headers={"Content-Type": content_type},
        )
        resp.raise_for_status()

    async def post_graph_turtle(
        self,
        graph_iri: str,
        turtle: bytes | str,
        dataset: str | None = None,
    ) -> None:
        """
        GSP HTTP POST — 해당 Named Graph에 Turtle을 추가(merge). 기존 트리플은 유지.
        배치 INSERT DATA 대신 한 번의 요청으로 대량 적재할 때 사용.
        """
        body = turtle if isinstance(turtle, bytes) else turtle.encode("utf-8")
        await self.post_graph_rdf(graph_iri, body, "text/turtle", dataset=dataset)

    async def put_graph_turtle(
        self,
        graph_iri: str,
        turtle: bytes | str,
        dataset: str | None = None,
    ) -> None:
        """
        GSP HTTP PUT — Named Graph 내용을 Turtle로 전부 교체. 기존 그래프는 삭제됨.
        온톨로지 메타(owl:Ontology 등)가 같은 그래프에 있으면 함께 사라지므로 주의.
        """
        body = turtle if isinstance(turtle, bytes) else turtle.encode("utf-8")
        resp = await self._client.put(
            self._gsp_url(dataset),
            params={"graph": graph_iri},
            content=body,
            headers={"Content-Type": "text/turtle"},
        )
        resp.raise_for_status()

    # ── 온톨로지 목록 ─────────────────────────────────────────────────────

    async def list_ontologies(self, page: int = 1, page_size: int = 20, dataset: str | None = None) -> tuple[list[dict], int]:
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
            self.sparql_select(count_q, dataset),
            self.sparql_select(select_q, dataset),
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

    async def get_ontology_stats(self, kg_iri: str, dataset: str | None = None) -> dict:
        """
        단일 kg Named Graph 기준 통계 (클래스/속성/개체 수 등).
        asyncio.gather로 병렬 실행.
        """
        g = f"<{kg_iri}>"

        def _count_q(rdf_type: str) -> str:
            return f"""
                PREFIX owl: <http://www.w3.org/2002/07/owl#>
                SELECT (COUNT(?x) AS ?cnt) WHERE {{ GRAPH {g} {{ ?x a {rdf_type} }} }}
            """

        base = kg_iri.replace("/kg", "", 1) if kg_iri.endswith("/kg") else kg_iri
        named_graphs_q = f"""
            SELECT (COUNT(DISTINCT ?g) AS ?cnt) WHERE {{ GRAPH ?g {{ ?s ?p ?o }}
            FILTER(STRSTARTS(STR(?g), "{base}")) }}
        """

        individual_count_q = f"""
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            SELECT (COUNT(DISTINCT ?x) AS ?cnt) WHERE {{ GRAPH {g} {{ ?x a owl:NamedIndividual }} }}
        """

        results = await asyncio.gather(
            self.sparql_select(_count_q("owl:Class"), dataset),
            self.sparql_select(individual_count_q, dataset),
            self.sparql_select(_count_q("owl:ObjectProperty"), dataset),
            self.sparql_select(_count_q("owl:DatatypeProperty"), dataset),
            self.sparql_select(named_graphs_q, dataset),
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
