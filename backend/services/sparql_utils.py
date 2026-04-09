"""
services/sparql_utils.py — SPARQL 공통 유틸리티

함수:
  v(term)           SPARQL result binding → str
  esc(s)            SPARQL 리터럴 이스케이프
  xsd_full(xsd)     축약 XSD → 완전 IRI
  xsd_short(full)   완전 IRI → 축약 XSD
  paginated_class_query(...)  count + paginated fetch 병렬 실행

여러 api/*.py 모듈에서 중복 정의되던 헬퍼 함수와 PREFIX 상수를 통합.
"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.ontology_store import OntologyStore

# ── 공통 PREFIX 블록 ──────────────────────────────────────────────────────────
COMMON_PREFIXES = """\
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
PREFIX dc:   <http://purl.org/dc/terms/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX prov: <http://www.w3.org/ns/prov#>
"""

# XSD base IRI
_XSD_BASE = "http://www.w3.org/2001/XMLSchema#"
_RDFS_LITERAL_FULL = "http://www.w3.org/2000/01/rdf-schema#Literal"


# ── 결과 파싱 헬퍼 ────────────────────────────────────────────────────────────

def v(term: dict | None, default: str = "") -> str:
    """SPARQL result term → str 변환.

    Fuseki 응답 binding의 단일 항목 `{"type": ..., "value": ...}` 을 str로 추출한다.
    None 또는 예상치 못한 타입이 오면 default 반환.
    """
    if term is None:
        return default
    if isinstance(term, dict):
        return term.get("value", default)
    return str(term)


# ── 리터럴 이스케이프 ─────────────────────────────────────────────────────────

def esc(s: str) -> str:
    """SPARQL 리터럴 안에 삽입하기 위한 문자열 이스케이프.

    역슬래시 → \\\\, 큰따옴표 → \\", 줄바꿈 → \\n, 캐리지 리턴 → \\r
    """
    return (
        s.replace("\\", "\\\\")
         .replace('"', '\\"')
         .replace("\n", "\\n")
         .replace("\r", "\\r")
    )


# ── XSD 타입 변환 ─────────────────────────────────────────────────────────────

def xsd_full(xsd: str) -> str:
    """축약 XSD 타입 문자열 → 완전 IRI 변환.

    Examples:
        "xsd:string"   → "http://www.w3.org/2001/XMLSchema#string"
        "string"       → "http://www.w3.org/2001/XMLSchema#string"
        "rdfs:Literal" → "http://www.w3.org/2000/01/rdf-schema#Literal"
        "http://..."   → 그대로 반환
    """
    if xsd == "rdfs:Literal":
        return _RDFS_LITERAL_FULL
    if xsd.startswith("xsd:"):
        return _XSD_BASE + xsd[4:]
    if xsd.startswith("http"):
        return xsd
    return _XSD_BASE + xsd


# ── Protégé 방식 클래스·개체 SPARQL 패턴 ─────────────────────────────────────

CLASS_FILTER = """
    FILTER(isIRI(?iri))
    FILTER(?iri NOT IN (
        owl:Class, owl:NamedIndividual, owl:Ontology,
        owl:ObjectProperty, owl:DatatypeProperty, owl:AnnotationProperty,
        rdfs:Class, rdfs:Datatype, rdf:Property,
        owl:Thing, rdfs:Resource
    ))
"""

CLASS_PATTERN = f"""
    {{ ?iri a owl:Class . {CLASS_FILTER} }}
    UNION
    {{ ?iri a rdfs:Class . FILTER NOT EXISTS {{ ?iri a owl:Ontology }} {CLASS_FILTER} }}
    UNION
    {{ ?iri a skos:Concept . {CLASS_FILTER} }}
    UNION
    {{
        {{ ?iri rdfs:subClassOf ?_sc }} UNION {{ ?_sc rdfs:subClassOf ?iri }}
        {CLASS_FILTER}
    }}
    UNION
    {{
        {{ ?_p rdfs:domain ?iri }} UNION {{ ?_p rdfs:range ?iri }}
        {CLASS_FILTER}
    }}
"""

INDIVIDUAL_PATTERN = """
    {
      ?iri a owl:NamedIndividual
    } UNION {
      ?iri rdf:type ?ctype .
      FILTER(isIRI(?ctype))
      FILTER(?ctype NOT IN (
          owl:Class, owl:NamedIndividual, owl:Ontology,
          owl:ObjectProperty, owl:DatatypeProperty, owl:AnnotationProperty,
          rdfs:Class, rdfs:Datatype, rdf:Property
      ))
      FILTER NOT EXISTS { GRAPH ?_any { ?iri a owl:Class } }
      FILTER NOT EXISTS { GRAPH ?_any { ?iri a rdfs:Class } }
    }
"""


def xsd_short(full: str) -> str:
    """완전 XSD IRI → 축약 타입 문자열 변환.

    Examples:
        "http://www.w3.org/2001/XMLSchema#string"          → "xsd:string"
        "http://www.w3.org/2000/01/rdf-schema#Literal"     → "rdfs:Literal"
        기타                                                 → 그대로 반환
    """
    if full == _RDFS_LITERAL_FULL:
        return "rdfs:Literal"
    if full.startswith(_XSD_BASE):
        return "xsd:" + full[len(_XSD_BASE):]
    return full


# ── 페이지네이션 헬퍼 ─────────────────────────────────────────────────────────

async def paginated_class_query(
    store: "OntologyStore",
    graph_pattern: str,
    gf: str,
    page: int,
    page_size: int,
    dataset: str | None = None,
) -> tuple[int, list[dict]]:
    """count + paginated fetch를 asyncio.gather로 병렬 실행.

    graph_pattern: GRAPH ?_g { ... } 안에 들어갈 SPARQL 패턴
                   (class detection + 추가 필터 모두 포함)
    gf:            graphs_filter_clause 결과 문자열
    반환: (total, rows) — rows는 raw SPARQL binding dict 리스트
    """
    offset = (page - 1) * page_size

    count_q = f"""{COMMON_PREFIXES}
SELECT (COUNT(DISTINCT ?iri) AS ?total) WHERE {{
    GRAPH ?_g {{
        {graph_pattern}
    }}
    {gf}
}}"""

    fetch_q = f"""{COMMON_PREFIXES}
SELECT ?iri (MIN(?lbl) AS ?label) (MIN(?cmt) AS ?comment)
       (COUNT(DISTINCT ?child) AS ?subclassCount)
       (COUNT(DISTINCT ?ind) AS ?individualCount) WHERE {{
    {{
        SELECT DISTINCT ?iri WHERE {{
            GRAPH ?_g {{
                {graph_pattern}
            }}
            {gf}
        }}
    }}
    OPTIONAL {{ GRAPH ?_lg {{ ?iri rdfs:label ?_rdfsLbl }} }}
    OPTIONAL {{ GRAPH ?_lg {{ ?iri skos:prefLabel ?_skosLbl }} }}
    BIND(COALESCE(?_rdfsLbl, ?_skosLbl) AS ?lbl)
    OPTIONAL {{ GRAPH ?_lg {{ ?iri rdfs:comment ?cmt }} }}
    OPTIONAL {{ GRAPH ?_lg {{ ?child rdfs:subClassOf ?iri }} }}
    OPTIONAL {{ GRAPH ?_lg {{ ?ind rdf:type ?iri }} }}
}} GROUP BY ?iri
ORDER BY ?lbl LIMIT {page_size} OFFSET {offset}"""

    count_rows, rows = await asyncio.gather(
        store.sparql_select(count_q, dataset=dataset),
        store.sparql_select(fetch_q, dataset=dataset),
    )
    total = int(v(count_rows[0].get("total"), "0")) if count_rows else 0
    return total, rows
