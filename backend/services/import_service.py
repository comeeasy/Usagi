"""
services/import_service.py — rdflib 파싱 + Fuseki bulk insert
"""
from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

import httpx
import rdflib
from rdflib import Graph, URIRef, Literal, BNode

from services.ontology_store import Triple, OntologyStore

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

STANDARD_ONTOLOGIES: dict[str, str] = {
    "schema.org": "https://schema.org/version/latest/schemaorg-current-https.ttl",
    "foaf": "http://xmlns.com/foaf/spec/index.rdf",
    "dc": "https://www.dublincore.org/specifications/dublin-core/dcmi-terms/dublin_core_terms.ttl",
    "skos": "https://www.w3.org/2009/08/skos-reference/skos.rdf",
    "owl": "https://www.w3.org/2002/07/owl",
    "rdfs": "https://www.w3.org/2000/01/rdf-schema",
}

_CONTENT_TYPE_FORMAT = {
    "text/turtle": "turtle",
    "application/x-turtle": "turtle",
    "application/rdf+xml": "xml",
    "application/ld+json": "json-ld",
    "text/n3": "n3",
    "application/n-triples": "nt",
    "application/trig": "trig",
    "application/n-quads": "nquads",
}

_EXT_FORMAT = {
    ".ttl": "turtle",
    ".owl": "xml",
    ".rdf": "xml",
    ".xml": "xml",
    ".jsonld": "json-ld",
    ".json": "json-ld",
    ".nt": "nt",
    ".n3": "n3",
    ".trig": "trig",
    ".nq": "nquads",
}

# 내부 포맷 키 → Fuseki GSP POST 시 사용할 Content-Type (rdflib 파싱·재직렬화 없이 원문 적재)
_GSP_CONTENT_TYPE: dict[str, str] = {
    "turtle": "text/turtle",
    "xml": "application/rdf+xml",
    "nt": "application/n-triples",
    "json-ld": "application/ld+json",
    "n3": "text/n3",
    "trig": "application/trig",
    "nquads": "application/n-quads",
}


def _detect_format_from_content_type(ct: str) -> str:
    ct = ct.split(";")[0].strip().lower()
    return _CONTENT_TYPE_FORMAT.get(ct, "xml")


def _detect_format_from_filename(filename: str) -> str:
    for ext, fmt in _EXT_FORMAT.items():
        if filename.lower().endswith(ext):
            return fmt
    return "xml"


def _graph_to_triples(g: Graph) -> list[Triple]:
    """rdflib Graph → Triple 목록 변환."""
    return [
        Triple(subject=s, predicate=p, object_=o)
        for s, p, o in g
    ]


async def parse_file(file_content: bytes, format: str) -> list[Triple]:
    """파일 파싱 → Triple 목록. rdflib으로 모든 포맷 처리."""
    logger.info(
        "IMPORT parse_start bytes=%d format=%s",
        len(file_content),
        format,
    )
    t0 = time.perf_counter()
    g = Graph()
    g.parse(data=file_content, format=format)
    triples = _graph_to_triples(g)
    ms = (time.perf_counter() - t0) * 1000
    logger.info(
        "IMPORT parse_done triples=%d ms=%.1f format=%s",
        len(triples),
        ms,
        format,
    )
    return triples


async def parse_url(url: str) -> list[Triple]:
    """URL에서 온톨로지 다운로드 후 파싱."""
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()

    ct = response.headers.get("content-type", "")
    fmt = _detect_format_from_content_type(ct)
    return await parse_file(response.content, fmt)


async def import_standard(name: str) -> list[Triple]:
    """사전 등록 온톨로지 임포트."""
    if name not in STANDARD_ONTOLOGIES:
        raise ValueError(f"Unknown standard ontology: {name}. Supported: {list(STANDARD_ONTOLOGIES)}")
    url = STANDARD_ONTOLOGIES[name]
    return await parse_url(url)


def gsp_content_type_for_format(fmt: str) -> str | None:
    """알려진 시리얼라이제이션 키에 대응하는 GSP Content-Type. 없으면 None (rdflib 경로 등)."""
    return _GSP_CONTENT_TYPE.get(fmt)


async def bulk_insert_raw_gsp(
    store: OntologyStore,
    body: bytes,
    graph_iri: str,
    content_type: str,
    fmt_label: str,
    dataset: str | None = None,
) -> int:
    """
    RDF 원본을 GSP POST로 그대로 적재 (rdflib 파싱/재직렬화 없음).
    반환값은 POST 전후 그래프 트리플 수 차이(이번 요청에서 늘어난 개수 근사).
    """
    if not body.strip():
        return 0
    t0 = time.perf_counter()
    before = await store.count_graph_triples(graph_iri, dataset)
    await store.post_graph_rdf(graph_iri, body, content_type, dataset=dataset)
    after = await store.count_graph_triples(graph_iri, dataset)
    ms = (time.perf_counter() - t0) * 1000
    delta = max(0, after - before)
    logger.info(
        "IMPORT raw_gsp fmt=%s ct=%s ms=%.1f bytes=%d graph=%s triples_delta=%d (before=%d after=%d)",
        fmt_label,
        content_type,
        ms,
        len(body),
        graph_iri,
        delta,
        before,
        after,
    )
    return delta


async def bulk_insert(store: OntologyStore, triples: list[Triple], graph_iri: str, dataset: str | None = None) -> int:
    """
    파싱된 트리플을 Named Graph에 적재.

    Jena Graph Store HTTP POST(text/turtle)로 한 번에 추가 — SPARQL UPDATE 다회 호출 대신
    Fuseki /data?graph=... 에 단일 요청 (로그 스팸·지연 감소).
    """
    if not triples:
        return 0
    g = Graph()
    for t in triples:
        g.add((t.subject, t.predicate, t.object_))
    t_ser = time.perf_counter()
    turtle = g.serialize(format="turtle")
    ser_bytes = turtle.encode("utf-8") if isinstance(turtle, str) else turtle
    ms_ser = (time.perf_counter() - t_ser) * 1000
    logger.info(
        "IMPORT serialize_turtle ms=%.1f body_bytes=%d triples=%d graph=%s",
        ms_ser,
        len(ser_bytes),
        len(triples),
        graph_iri,
    )
    t_gsp = time.perf_counter()
    await store.post_graph_turtle(graph_iri, turtle, dataset=dataset)
    ms_gsp = (time.perf_counter() - t_gsp) * 1000
    logger.info(
        "IMPORT gsp_post_done ms=%.1f graph=%s triples=%d",
        ms_gsp,
        graph_iri,
        len(triples),
    )
    return len(triples)
