"""
Import Service — rdflib 파싱 + Oxigraph bulk insert
"""
from __future__ import annotations

# TODO: import rdflib, httpx, and internal types
# from rdflib import Graph as RDFGraph
# import httpx
# from backend.models.ontology import Triple  # 실제 Triple 타입으로 교체
# from backend.services.ontology_store import OntologyStore

STANDARD_ONTOLOGIES: dict[str, str] = {
    "schema.org": "https://schema.org/version/latest/schemaorg-current-https.ttl",
    "foaf": "http://xmlns.com/foaf/spec/index.rdf",
    "dc": "https://www.dublincore.org/specifications/dublin-core/dcmi-terms/dublin_core_terms.ttl",
    "skos": "https://www.w3.org/2009/08/skos-reference/skos.rdf",
    "owl": "https://www.w3.org/2002/07/owl",
    "rdfs": "https://www.w3.org/2000/01/rdf-schema",
}

BATCH_SIZE = 1000


async def parse_file(file_content: bytes, format: str) -> list:
    """
    rdflib.Graph().parse() 로 OWL/TTL/RDF/JSON-LD 파싱, Triple 목록 반환.

    Args:
        file_content: 파일 바이트 데이터
        format: 'turtle' | 'xml' | 'json-ld' | 'n3' 등 rdflib 포맷 문자열

    Returns:
        list[Triple]: 파싱된 Triple 목록
    """
    # TODO: implement
    # g = RDFGraph()
    # g.parse(data=file_content, format=format)
    # return [Triple(subject=str(s), predicate=str(p), object=str(o)) for s, p, o in g]
    raise NotImplementedError


async def parse_url(url: str) -> list:
    """
    httpx.AsyncClient로 URL 다운로드 후 parse_file 호출.

    Args:
        url: 온톨로지 문서 URL

    Returns:
        list[Triple]: 파싱된 Triple 목록
    """
    # TODO: implement
    # async with httpx.AsyncClient() as client:
    #     response = await client.get(url, follow_redirects=True)
    #     response.raise_for_status()
    #     content_type = response.headers.get("content-type", "")
    #     format = _detect_format(content_type)
    #     return await parse_file(response.content, format)
    raise NotImplementedError


async def import_standard(name: str) -> list:
    """
    사전 등록 온톨로지 URL 매핑 dict에서 URL 조회 후 parse_url 호출.
    지원: schema.org, foaf, dc, skos, owl, rdfs

    Args:
        name: STANDARD_ONTOLOGIES 딕셔너리 키

    Returns:
        list[Triple]: 파싱된 Triple 목록

    Raises:
        ValueError: 지원하지 않는 온톨로지 이름
    """
    if name not in STANDARD_ONTOLOGIES:
        raise ValueError(f"Unknown standard ontology: {name}. Supported: {list(STANDARD_ONTOLOGIES)}")
    # TODO: implement
    # url = STANDARD_ONTOLOGIES[name]
    # return await parse_url(url)
    raise NotImplementedError


async def bulk_insert(ontology_id: str, triples: list, graph_iri: str) -> int:
    """
    OntologyStore.insert_triples() 배치 호출 (1000개씩), 삽입된 triple 수 반환.

    Args:
        ontology_id: 대상 온톨로지 ID
        triples: 삽입할 Triple 목록
        graph_iri: Named Graph IRI

    Returns:
        int: 삽입된 triple 수
    """
    # TODO: implement
    # store = OntologyStore.get_instance()
    # total = 0
    # for i in range(0, len(triples), BATCH_SIZE):
    #     batch = triples[i:i + BATCH_SIZE]
    #     await store.insert_triples(ontology_id, batch, graph_iri)
    #     total += len(batch)
    # return total
    raise NotImplementedError
