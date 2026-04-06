"""
api/individuals.py — Individual(owl:NamedIndividual) CRUD + Provenance 라우터

엔드포인트:
  GET    /ontologies/{id}/individuals               Individual 목록
  POST   /ontologies/{id}/individuals               Individual 생성 (수동 입력)
  GET    /ontologies/{id}/individuals/{iri}         Individual 상세
  PUT    /ontologies/{id}/individuals/{iri}         Individual 수정
  DELETE /ontologies/{id}/individuals/{iri}         Individual 삭제
  GET    /ontologies/{id}/individuals/{iri}/provenance  Provenance 기록 목록
"""

from datetime import datetime, timezone
from typing import Annotated
from urllib.parse import unquote

from collections import defaultdict

from fastapi import APIRouter, HTTPException, Query, Request

from api.concepts import _resolve_kg_graph
from models.individual import (
    DataPropertyValue,
    Individual,
    IndividualCreate,
    IndividualUpdate,
    ObjectPropertyValue,
    ProvenanceRecord,
)
from models.ontology import PaginatedResponse

router = APIRouter(prefix="/ontologies/{ontology_id}/individuals", tags=["individuals"])

_P = """
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
PREFIX prov: <http://www.w3.org/ns/prov#>
"""

_XSD_BASE = "http://www.w3.org/2001/XMLSchema#"


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _individual_pattern(kg: str) -> str:
    """
    owl:NamedIndividual 또는 rdf:type의 대상으로 사용된 IRI의 인스턴스.
    RDFS 의미론상 rdf:type 대상은 클래스이므로, 선언 여부와 무관하게 인스턴스로 취급.
    ABox-only KG (foaf:Person 등 외부 어휘 참조)에서도 동작.
    """
    return f"""
    {{
      ?iri a owl:NamedIndividual
    }} UNION {{
      ?iri rdf:type ?ctype .
      FILTER(isIRI(?ctype))
      FILTER(?ctype NOT IN (
          owl:Class, owl:NamedIndividual, owl:Ontology,
          owl:ObjectProperty, owl:DatatypeProperty, owl:AnnotationProperty,
          rdfs:Class, rdfs:Datatype, rdf:Property
      ))
      FILTER NOT EXISTS {{ GRAPH <{kg}> {{ ?iri a owl:Class }} }}
      FILTER NOT EXISTS {{ GRAPH <{kg}> {{ ?iri a rdfs:Class }} }}
    }}
"""


def _individual_keyword_filter(q: str | None) -> str:
    if not q or not str(q).strip():
        return ""
    ql = _esc(q.lower())
    return f"""
    FILTER(
      CONTAINS(LCASE(STR(?iri)), "{ql}") ||
      (bound(?label) && CONTAINS(LCASE(STR(?label)), "{ql}"))
    )"""


def _v(term: dict | None, default: str = "") -> str:
    if term is None:
        return default
    if isinstance(term, dict):
        return term.get("value", default)
    return str(term)


def _xsd_full(xsd: str) -> str:
    if xsd.startswith("xsd:"):
        return _XSD_BASE + xsd[4:]
    return xsd if xsd.startswith("http") else _XSD_BASE + xsd


def _xsd_short(full: str) -> str:
    if full.startswith(_XSD_BASE):
        return "xsd:" + full[len(_XSD_BASE):]
    return full


# ── 목록 ──────────────────────────────────────────────────────────────────

@router.get("", response_model=PaginatedResponse)
async def list_individuals(
    request: Request,
    ontology_id: str,
    type_iri: str | None = Query(None, alias="type"),
    concept_iri: str | None = Query(None),
    q: str | None = Query(None),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    dataset: str | None = Query(None),
) -> dict:
    store = request.app.state.ontology_store
    kg = await _resolve_kg_graph(store, ontology_id, dataset=dataset)
    if kg is None:
        raise HTTPException(404, detail={"code": "ONTOLOGY_NOT_FOUND", "message": f"Ontology not found: {ontology_id}"})

    offset = (page - 1) * page_size
    filter_type = type_iri or concept_iri

    extra = ""
    if filter_type:
        extra += f"\n    ?iri rdf:type <{filter_type}> ."
    extra += _individual_keyword_filter(q)

    count_rows = await store.sparql_select(f"""{_P}
SELECT (COUNT(DISTINCT ?iri) AS ?total) WHERE {{
    GRAPH <{kg}> {{
        {_individual_pattern(kg)}
        {extra}
    }}
}}""", dataset=dataset)
    total = int(_v(count_rows[0].get("total"), "0")) if count_rows else 0

    rows = await store.sparql_select(f"""{_P}
SELECT ?iri (MIN(?lbl) AS ?label) WHERE {{
    {{
        SELECT DISTINCT ?iri WHERE {{
            GRAPH <{kg}> {{
                {_individual_pattern(kg)}
                {extra}
            }}
        }}
    }}
    OPTIONAL {{ GRAPH <{kg}> {{ ?iri rdfs:label ?lbl }} }}
}} GROUP BY ?iri
ORDER BY ?label LIMIT {page_size} OFFSET {offset}""", dataset=dataset)

    types_by_iri: dict[str, list[str]] = defaultdict(list)
    if rows:
        iris_vals = " ".join(f"<{_v(r.get('iri'))}>" for r in rows)
        type_rows = await store.sparql_select(f"""{_P}
SELECT ?iri ?type WHERE {{
    VALUES ?iri {{ {iris_vals} }}
    GRAPH <{kg}> {{
        ?iri rdf:type ?type .
        FILTER(?type != owl:NamedIndividual) FILTER(isIRI(?type))
    }}
}}""", dataset=dataset)
        for tr in type_rows:
            types_by_iri[_v(tr.get("iri"))].append(_v(tr.get("type")))

    items = [
        Individual(
            iri=_v(row.get("iri")),
            ontology_id=ontology_id,
            label=_v(row.get("label")) or None,
            types=types_by_iri.get(_v(row.get("iri")), []),
        )
        for row in rows
    ]

    return {"items": items, "total": total, "page": page, "page_size": page_size, "has_next": (page * page_size) < total}


# ── 생성 ──────────────────────────────────────────────────────────────────

@router.post("", response_model=Individual, status_code=201)
async def create_individual(
    request: Request,
    ontology_id: str,
    body: IndividualCreate,
    dataset: str | None = Query(None),
) -> Individual:
    store = request.app.state.ontology_store
    graph_iri = await _resolve_kg_graph(store, ontology_id, dataset=dataset)
    if graph_iri is None:
        raise HTTPException(404, detail={"code": "ONTOLOGY_NOT_FOUND", "message": f"Ontology not found: {ontology_id}"})

    if await store.sparql_ask(
        f"{_P} ASK {{ GRAPH <{graph_iri}> {{ <{body.iri}> a owl:NamedIndividual }} }}", dataset=dataset
    ):
        raise HTTPException(409, detail={"code": "INDIVIDUAL_IRI_DUPLICATE", "message": f"IRI exists: {body.iri}"})

    now = datetime.now(timezone.utc).isoformat()
    triples = [f"    <{body.iri}> a owl:NamedIndividual ."]
    if body.label:
        triples.append(f'    <{body.iri}> rdfs:label "{_esc(body.label)}" .')
    for t in body.types:
        triples.append(f"    <{body.iri}> rdf:type <{t}> .")
    for dpv in body.data_property_values:
        triples.append(f'    <{body.iri}> <{dpv.property_iri}> "{_esc(dpv.value)}"^^<{_xsd_full(dpv.datatype)}> .')
    for opv in body.object_property_values:
        triples.append(f"    <{body.iri}> <{opv.property_iri}> <{opv.target_iri}> .")
    for s in body.same_as:
        triples.append(f"    <{body.iri}> owl:sameAs <{s}> .")
    for d in body.different_from:
        triples.append(f"    <{body.iri}> owl:differentFrom <{d}> .")
    triples.append(f'    <{body.iri}> prov:generatedAtTime "{now}"^^xsd:dateTime .')
    triples.append(f'    <{body.iri}> prov:wasAttributedTo "manual" .')

    await store.sparql_update(f"""{_P}
INSERT DATA {{ GRAPH <{graph_iri}> {{
{chr(10).join(triples)}
}} }}""", dataset=dataset)

    return Individual(
        iri=body.iri, ontology_id=ontology_id, label=body.label, types=body.types,
        data_property_values=[
            DataPropertyValue(property_iri=d.property_iri, value=d.value, datatype=d.datatype, graph_iri=graph_iri)
            for d in body.data_property_values
        ],
        object_property_values=[
            ObjectPropertyValue(property_iri=o.property_iri, target_iri=o.target_iri, graph_iri=graph_iri)
            for o in body.object_property_values
        ],
        same_as=body.same_as,
        different_from=body.different_from,
    )


# ── Provenance (/{iri}/provenance 먼저 등록해야 /{iri:path} 라우트보다 우선) ──

@router.get("/{iri:path}/provenance", response_model=list[ProvenanceRecord])
async def get_provenance(
    request: Request,
    ontology_id: str,
    iri: str,
    dataset: str | None = Query(None),
) -> list[ProvenanceRecord]:
    store = request.app.state.ontology_store
    iri = unquote(iri)

    graph_rows = await store.sparql_select(f"""{_P}
SELECT DISTINCT ?g WHERE {{ GRAPH ?g {{ <{iri}> ?p ?o }} }}""", dataset=dataset)

    records = []
    for row in graph_rows:
        g = _v(row.get("g"))
        prov_rows = await store.sparql_select(f"""{_P}
SELECT ?ingestedAt ?attr (COUNT(*) AS ?cnt) WHERE {{
    GRAPH <{g}> {{
        <{iri}> ?p ?o .
        OPTIONAL {{ <{iri}> prov:generatedAtTime ?ingestedAt }}
        OPTIONAL {{ <{iri}> prov:wasAttributedTo ?attr }}
    }}
}} GROUP BY ?ingestedAt ?attr""", dataset=dataset)

        pr = prov_rows[0] if prov_rows else {}
        ingested_at = _v(pr.get("ingestedAt")) or datetime.now(timezone.utc).isoformat()
        source_id = _v(pr.get("attr")) or "unknown"
        triple_count = int(_v(pr.get("cnt"), "0"))
        src = str(source_id).lower()
        source_type = (
            "manual" if src == "manual" else ("api-stream" if "kafka" in src else ("api-rest" if "api" in src else "unknown"))
        )

        records.append(ProvenanceRecord(
            graph_iri=g, source_id=source_id, source_type=source_type,
            ingested_at=ingested_at, triple_count=triple_count,
        ))

    records.sort(key=lambda r: r.ingested_at, reverse=True)
    return records


# ── 상세 조회 ─────────────────────────────────────────────────────────────

@router.get("/{iri:path}", response_model=Individual)
async def get_individual(
    request: Request,
    ontology_id: str,
    iri: str,
    dataset: str | None = Query(None),
) -> Individual:
    store = request.app.state.ontology_store
    iri = unquote(iri)
    g = await _resolve_kg_graph(store, ontology_id, dataset=dataset)
    if g is None:
        raise HTTPException(404, detail={"code": "ONTOLOGY_NOT_FOUND", "message": f"Ontology not found: {ontology_id}"})

    # 존재 확인: outgoing 트리플이 하나라도 있으면 유효 (owl:NamedIndividual 선언 불필요)
    if not await store.sparql_ask(f"{_P} ASK {{ GRAPH <{g}> {{ <{iri}> ?p ?o }} }}", dataset=dataset):
        raise HTTPException(404, detail={"code": "INDIVIDUAL_NOT_FOUND", "message": f"Not found: {iri}"})

    # 모든 outgoing 트리플 한 번에 가져오기 — predicate 분류는 Python에서
    rows = await store.sparql_select(f"""{_P}
SELECT ?p ?o WHERE {{
    GRAPH <{g}> {{
        <{iri}> ?p ?o .
        FILTER(!isBlank(?o))
    }}
}}""", dataset=dataset)

    _LABEL_PREDS = {
        "http://www.w3.org/2000/01/rdf-schema#label",
        "http://www.w3.org/2004/02/skos/core#prefLabel",
        "http://www.w3.org/2004/02/skos/core#altLabel",
    }
    _META_PREDS = {
        "http://www.w3.org/ns/prov#generatedAtTime",
        "http://www.w3.org/ns/prov#wasAttributedTo",
    }
    _RDF_TYPE      = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
    _OWL_SAME      = "http://www.w3.org/2002/07/owl#sameAs"
    _OWL_DIFF      = "http://www.w3.org/2002/07/owl#differentFrom"
    _OWL_NAMED_IND = "http://www.w3.org/2002/07/owl#NamedIndividual"

    label: str | None = None
    types: list[str] = []
    data_property_values: list[DataPropertyValue] = []
    object_property_values: list[ObjectPropertyValue] = []
    same_as: list[str] = []
    different_from: list[str] = []

    for row in rows:
        p = _v(row.get("p"))
        o = row.get("o", {})
        o_val = _v(o)
        o_type = o.get("type", "")

        if p in _LABEL_PREDS:
            if label is None:
                label = o_val
        elif p in _META_PREDS:
            pass  # provenance 전용 엔드포인트에서 처리
        elif p == _RDF_TYPE and o_type == "uri":
            if o_val != _OWL_NAMED_IND:
                types.append(o_val)
        elif p == _OWL_SAME and o_type == "uri":
            same_as.append(o_val)
        elif p == _OWL_DIFF and o_type == "uri":
            different_from.append(o_val)
        elif o_type == "literal":
            data_property_values.append(DataPropertyValue(
                property_iri=p,
                value=o_val,
                datatype=_xsd_short(o.get("datatype", _XSD_BASE + "string")),
                graph_iri=g,
            ))
        elif o_type == "uri":
            object_property_values.append(ObjectPropertyValue(
                property_iri=p, target_iri=o_val, graph_iri=g,
            ))

    return Individual(
        iri=iri, ontology_id=ontology_id, label=label, types=types,
        data_property_values=data_property_values,
        object_property_values=object_property_values,
        same_as=same_as,
        different_from=different_from,
    )


# ── 수정 ──────────────────────────────────────────────────────────────────

@router.put("/{iri:path}", response_model=Individual)
async def update_individual(
    request: Request,
    ontology_id: str,
    iri: str,
    body: IndividualUpdate,
    dataset: str | None = Query(None),
) -> Individual:
    store = request.app.state.ontology_store
    iri = unquote(iri)
    g = await _resolve_kg_graph(store, ontology_id, dataset=dataset)
    if g is None:
        raise HTTPException(404, detail={"code": "ONTOLOGY_NOT_FOUND", "message": f"Ontology not found: {ontology_id}"})

    if not await store.sparql_ask(f"{_P} ASK {{ GRAPH <{g}> {{ <{iri}> ?p ?o }} }}", dataset=dataset):
        raise HTTPException(404, detail={"code": "INDIVIDUAL_NOT_FOUND", "message": f"Not found: {iri}"})

    if body.label is not None:
        await store.sparql_update(f"""{_P}
DELETE {{ GRAPH <{g}> {{ <{iri}> rdfs:label ?o }} }}
INSERT {{ GRAPH <{g}> {{ <{iri}> rdfs:label "{_esc(body.label)}" }} }}
WHERE  {{ OPTIONAL {{ GRAPH <{g}> {{ <{iri}> rdfs:label ?o }} }} }}""", dataset=dataset)

    if body.types is not None:
        await store.sparql_update(f"""{_P}
DELETE {{ GRAPH <{g}> {{ <{iri}> rdf:type ?t }} }}
WHERE  {{ GRAPH <{g}> {{ <{iri}> rdf:type ?t . FILTER(?t != owl:NamedIndividual) }} }}""", dataset=dataset)
        if body.types:
            triples = "\n".join([f"    <{iri}> rdf:type <{t}> ." for t in body.types])
            await store.sparql_update(f"{_P}\nINSERT DATA {{ GRAPH <{g}> {{\n{triples}\n}} }}", dataset=dataset)

    if body.data_property_values is not None:
        await store.sparql_update(f"""{_P}
DELETE {{ GRAPH <{g}> {{ <{iri}> ?p ?o }} }}
WHERE  {{ GRAPH <{g}> {{ <{iri}> ?p ?o . FILTER(isLiteral(?o))
    FILTER(?p NOT IN (rdfs:label, prov:generatedAtTime, prov:wasAttributedTo)) }} }}""", dataset=dataset)
        if body.data_property_values:
            triples = "\n".join([
                f'    <{iri}> <{d.property_iri}> "{_esc(d.value)}"^^<{_xsd_full(d.datatype)}> .'
                for d in body.data_property_values
            ])
            await store.sparql_update(f"{_P}\nINSERT DATA {{ GRAPH <{g}> {{\n{triples}\n}} }}", dataset=dataset)

    if body.object_property_values is not None:
        await store.sparql_update(f"""{_P}
DELETE {{ GRAPH <{g}> {{ <{iri}> ?p ?o }} }}
WHERE  {{ GRAPH <{g}> {{ <{iri}> ?p ?o . FILTER(isIRI(?o))
    FILTER(?p NOT IN (rdf:type, owl:sameAs, owl:differentFrom)) }} }}""", dataset=dataset)
        if body.object_property_values:
            triples = "\n".join([f"    <{iri}> <{o.property_iri}> <{o.target_iri}> ." for o in body.object_property_values])
            await store.sparql_update(f"{_P}\nINSERT DATA {{ GRAPH <{g}> {{\n{triples}\n}} }}", dataset=dataset)

    for pred, vals in [("owl:sameAs", body.same_as), ("owl:differentFrom", body.different_from)]:
        if vals is not None:
            await store.sparql_update(f"""{_P}
DELETE {{ GRAPH <{g}> {{ <{iri}> {pred} ?o }} }}
WHERE  {{ GRAPH <{g}> {{ <{iri}> {pred} ?o }} }}""", dataset=dataset)
            if vals:
                triples = "\n".join([f"    <{iri}> {pred} <{v}> ." for v in vals])
                await store.sparql_update(f"{_P}\nINSERT DATA {{ GRAPH <{g}> {{\n{triples}\n}} }}", dataset=dataset)

    return await get_individual(request, ontology_id, iri, dataset=dataset)


# ── 삭제 ──────────────────────────────────────────────────────────────────

@router.delete("/{iri:path}", status_code=204)
async def delete_individual(
    request: Request,
    ontology_id: str,
    iri: str,
    dataset: str | None = Query(None),
) -> None:
    store = request.app.state.ontology_store
    iri = unquote(iri)
    g = await _resolve_kg_graph(store, ontology_id, dataset=dataset)
    if g is None:
        raise HTTPException(404, detail={"code": "ONTOLOGY_NOT_FOUND", "message": f"Ontology not found: {ontology_id}"})

    if not await store.sparql_ask(f"{_P} ASK {{ GRAPH <{g}> {{ <{iri}> ?p ?o }} }}", dataset=dataset):
        raise HTTPException(404, detail={"code": "INDIVIDUAL_NOT_FOUND", "message": f"Not found: {iri}"})

    await store.sparql_update(f"""{_P}
DELETE {{ GRAPH <{g}> {{ <{iri}> ?p ?o }} }}
WHERE  {{ GRAPH <{g}> {{ <{iri}> ?p ?o }} }}""", dataset=dataset)
