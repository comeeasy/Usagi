"""
services/import_service.py — rdflib 파싱 + Fuseki bulk insert
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import httpx
import rdflib
from rdflib import Graph, URIRef, Literal, BNode

from services.ontology_store import Triple, OntologyStore

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

BATCH_SIZE = 1000

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
    g = Graph()
    g.parse(data=file_content, format=format)
    triples = _graph_to_triples(g)
    logger.info("Parsed %d triples from file (rdflib, format=%s)", len(triples), format)
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


async def bulk_insert(store: OntologyStore, triples: list[Triple], graph_iri: str) -> int:
    """OntologyStore.insert_triples() 배치 호출 (BATCH_SIZE씩)."""
    total = 0
    for i in range(0, len(triples), BATCH_SIZE):
        batch = triples[i:i + BATCH_SIZE]
        await store.insert_triples(graph_iri, batch)
        total += len(batch)
        logger.debug("Inserted batch %d/%d", i + len(batch), len(triples))
    return total
