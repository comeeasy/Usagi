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
    owl:NamedIndividual 또는 (어떤 클래스에 rdf:type — 클래스가 owl:Class·rdfs:Class 모두 허용).
    LOD는 클래스를 rdfs:Class만 단언하는 경우가 많아 owl:Class만 보면 인스턴스가 전부 빠짐.
    NOT EXISTS는 kg 그래프를 명시(구현체에 따라 상위 GRAPH가 상속 안 될 수 있음).
    """
    return f"""
    {{
      ?iri a owl:NamedIndividual
    }} UNION {{
      ?iri rdf:type ?ctype .
      {{
        GRAPH <{kg}> {{ ?ctype a owl:Class }}
      }} UNION {{
        GRAPH <{kg}> {{ ?ctype a rdfs:Class .
        FILTER NOT EXISTS {{ ?ctype a owl:Ontology }} }}
      }}
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
        OPTIONAL {{ ?iri rdfs:label ?label }}
        {extra}
    }}
}}""", dataset=dataset)
    total = int(_v(count_rows[0].get("total"), "0")) if count_rows else 0

    rows = await store.sparql_select(f"""{_P}
SELECT DISTINCT ?iri ?label WHERE {{
    GRAPH <{kg}> {{
        {_individual_pattern(kg)}
        OPTIONAL {{ ?iri rdfs:label ?label }}
        {extra}
    }}
}} ORDER BY ?label LIMIT {page_size} OFFSET {offset}""", dataset=dataset)

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

    return {"items": items, "total": total, "page": page, "page_size": page_size}


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

    if not await store.sparql_ask(f"{_P} ASK {{ GRAPH <{g}> {{ <{iri}> a owl:NamedIndividual }} }}", dataset=dataset):
        raise HTTPException(404, detail={"code": "INDIVIDUAL_NOT_FOUND", "message": f"Not found: {iri}"})

    basic = await store.sparql_select(f"""{_P}
SELECT ?label WHERE {{ GRAPH <{g}> {{ <{iri}> a owl:NamedIndividual . OPTIONAL {{ <{iri}> rdfs:label ?label }} }} }} LIMIT 1""", dataset=dataset)
    label = _v(basic[0].get("label")) or None if basic else None

    type_rows = await store.sparql_select(f"""{_P}
SELECT DISTINCT ?type WHERE {{
    GRAPH <{g}> {{ <{iri}> rdf:type ?type . FILTER(?type != owl:NamedIndividual) FILTER(isIRI(?type)) }}
}}""", dataset=dataset)
    types = [_v(r.get("type")) for r in type_rows]

    dp_rows = await store.sparql_select(f"""{_P}
SELECT ?g ?p ?o WHERE {{
    GRAPH <{g}> {{ <{iri}> ?p ?o . FILTER(isLiteral(?o))
        FILTER(?p NOT IN (rdfs:label, prov:generatedAtTime, prov:wasAttributedTo)) }}
}}""", dataset=dataset)
    data_property_values = [
        DataPropertyValue(
            property_iri=_v(r.get("p")),
            value=_v(r.get("o")),
            datatype=_xsd_short(r["o"].get("datatype", _XSD_BASE + "string")) if r.get("o") else "xsd:string",
            graph_iri=_v(r.get("g")),
        )
        for r in dp_rows
    ]

    op_rows = await store.sparql_select(f"""{_P}
SELECT ?g ?p ?o WHERE {{
    GRAPH <{g}> {{ <{iri}> ?p ?o . FILTER(isIRI(?o))
        FILTER(?p NOT IN (rdf:type, owl:sameAs, owl:differentFrom)) }}
}}""", dataset=dataset)
    object_property_values = [
        ObjectPropertyValue(property_iri=_v(r.get("p")), target_iri=_v(r.get("o")), graph_iri=_v(r.get("g")))
        for r in op_rows
    ]

    same_rows = await store.sparql_select(f"{_P}\nSELECT ?s WHERE {{ GRAPH <{g}> {{ <{iri}> owl:sameAs ?s . FILTER(isIRI(?s)) }} }}", dataset=dataset)
    diff_rows = await store.sparql_select(f"{_P}\nSELECT ?d WHERE {{ GRAPH <{g}> {{ <{iri}> owl:differentFrom ?d . FILTER(isIRI(?d)) }} }}", dataset=dataset)

    return Individual(
        iri=iri, ontology_id=ontology_id, label=label, types=types,
        data_property_values=data_property_values,
        object_property_values=object_property_values,
        same_as=[_v(r.get("s")) for r in same_rows],
        different_from=[_v(r.get("d")) for r in diff_rows],
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

    if not await store.sparql_ask(f"{_P} ASK {{ GRAPH <{g}> {{ <{iri}> a owl:NamedIndividual }} }}", dataset=dataset):
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

    if not await store.sparql_ask(f"{_P} ASK {{ GRAPH <{g}> {{ <{iri}> a owl:NamedIndividual }} }}", dataset=dataset):
        raise HTTPException(404, detail={"code": "INDIVIDUAL_NOT_FOUND", "message": f"Not found: {iri}"})

    await store.sparql_update(f"""{_P}
DELETE {{ GRAPH <{g}> {{ <{iri}> ?p ?o }} }}
WHERE  {{ GRAPH <{g}> {{ <{iri}> ?p ?o }} }}""", dataset=dataset)
