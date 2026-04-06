"""
api/concepts.py — Concept(owl:Class) CRUD 라우터

엔드포인트:
  GET    /ontologies/{id}/concepts           Concept 목록
  POST   /ontologies/{id}/concepts           Concept 생성
  GET    /ontologies/{id}/concepts/{iri}     Concept 상세
  PUT    /ontologies/{id}/concepts/{iri}     Concept 수정
  DELETE /ontologies/{id}/concepts/{iri}     Concept 삭제
"""

import asyncio
from typing import Annotated
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException, Query, Request

from models.concept import Concept, ConceptCreate, ConceptUpdate, PropertyRestriction
from models.ontology import PaginatedResponse
from services.ontology_graph import resolve_kg_graph_iri

router = APIRouter(prefix="/ontologies/{ontology_id}/concepts", tags=["concepts"])

_P = """
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
PREFIX dc:   <http://purl.org/dc/terms/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
"""


async def _resolve_kg_graph(store, ontology_id: str, dataset: str | None = None) -> str | None:
    """UUID(dc:identifier)로 kg Named Graph IRI 반환. 없으면 None."""
    return await resolve_kg_graph_iri(store, ontology_id, dataset=dataset)


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


# 임포트·LOD 호환: owl:Class, rdfs:Class, SKOS Concept
_CLASS_PATTERN = """
    { ?iri a owl:Class }
    UNION
    { ?iri a rdfs:Class . FILTER NOT EXISTS { ?iri a owl:Ontology } }
    UNION
    { ?iri a skos:Concept }
"""


def _concept_keyword_filter(q: str | None) -> str:
    """검색어가 있을 때 IRI(로컬 이름)·rdfs:label 둘 다 매칭. 라벨 없는 클래스도 검색 가능."""
    if not q or not str(q).strip():
        return ""
    ql = _esc(q.lower())
    return f"""
    FILTER(
      CONTAINS(LCASE(STR(?iri)), "{ql}") ||
      (bound(?label) && CONTAINS(LCASE(STR(?label)), "{ql}"))
    )"""


def _v(term: dict | None, default: str = "") -> str:
    """SPARQL result term → string value."""
    if term is None:
        return default
    if isinstance(term, dict):
        return term.get("value", default)
    return str(term)


def _restriction_triples(iri: str, restrictions: list[PropertyRestriction], prefix: str = "r") -> str:
    lines = []
    for i, r in enumerate(restrictions):
        bn = f"_:{prefix}{i}"
        lines.append(f"    {bn} a owl:Restriction ; owl:onProperty <{r.property_iri}> ;")
        if r.type == "someValuesFrom":
            lines.append(f"        owl:someValuesFrom <{r.value}> .")
        elif r.type == "allValuesFrom":
            lines.append(f"        owl:allValuesFrom <{r.value}> .")
        elif r.type == "hasValue":
            lines.append(f"        owl:hasValue <{r.value}> .")
        elif r.type == "minCardinality":
            lines.append(f"        owl:minCardinality {r.cardinality or 1} .")
        elif r.type == "maxCardinality":
            lines.append(f"        owl:maxCardinality {r.cardinality or 1} .")
        elif r.type == "exactCardinality":
            lines.append(f"        owl:qualifiedCardinality {r.cardinality or 1} .")
        lines.append(f"    <{iri}> rdfs:subClassOf {bn} .")
    return "\n".join(lines)


# ── 목록 ──────────────────────────────────────────────────────────────────

@router.get("", response_model=PaginatedResponse)
async def list_concepts(
    request: Request,
    ontology_id: str,
    q: str | None = Query(None, alias="search"),
    super_class: str | None = Query(None, alias="superClass"),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    dataset: str | None = Query(None),
) -> dict:
    store = request.app.state.ontology_store
    kg = await _resolve_kg_graph(store, ontology_id, dataset=dataset)
    if kg is None:
        raise HTTPException(404, detail={"code": "ONTOLOGY_NOT_FOUND", "message": f"Ontology not found: {ontology_id}"})
    offset = (page - 1) * page_size

    extra = ""
    extra += _concept_keyword_filter(q)
    if super_class:
        extra += f"\n    ?iri rdfs:subClassOf <{super_class}> ."

    count_rows = await store.sparql_select(f"""{_P}
SELECT (COUNT(DISTINCT ?iri) AS ?total) WHERE {{
    GRAPH <{kg}> {{
        {_CLASS_PATTERN}
        OPTIONAL {{ ?iri rdfs:label ?label }}
        {extra}
    }}
}}""", dataset=dataset)
    total = int(_v(count_rows[0].get("total"), "0")) if count_rows else 0

    rows = await store.sparql_select(f"""{_P}
SELECT ?iri ?label ?comment (COUNT(DISTINCT ?ind) AS ?individualCount) WHERE {{
    GRAPH <{kg}> {{
        {_CLASS_PATTERN}
        OPTIONAL {{ ?iri rdfs:label ?label }}
        OPTIONAL {{ ?iri rdfs:comment ?comment }}
        {extra}
    }}
    OPTIONAL {{ GRAPH <{kg}> {{ ?ind rdf:type ?iri }} }}
}} GROUP BY ?iri ?label ?comment
ORDER BY ?label LIMIT {page_size} OFFSET {offset}""", dataset=dataset)

    items = [
        Concept(
            iri=_v(r.get("iri")),
            ontology_id=ontology_id,
            label=_v(r.get("label")) or _v(r.get("iri")),
            comment=_v(r.get("comment")) or None,
            individual_count=int(_v(r.get("individualCount"), "0")),
        )
        for r in rows
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


# ── 생성 ──────────────────────────────────────────────────────────────────

@router.post("", response_model=Concept, status_code=201)
async def create_concept(
    request: Request,
    ontology_id: str,
    body: ConceptCreate,
    dataset: str | None = Query(None),
) -> Concept:
    store = request.app.state.ontology_store
    kg = await _resolve_kg_graph(store, ontology_id, dataset=dataset)
    if kg is None:
        raise HTTPException(404, detail={"code": "ONTOLOGY_NOT_FOUND", "message": f"Ontology not found: {ontology_id}"})

    if await store.sparql_ask(f"{_P} ASK {{ GRAPH <{kg}> {{ <{body.iri}> a owl:Class }} }}", dataset=dataset):
        raise HTTPException(409, detail={"code": "CONCEPT_IRI_DUPLICATE", "message": f"IRI exists: {body.iri}"})

    triples = [
        f'    <{body.iri}> a owl:Class ; rdfs:label "{_esc(body.label)}" .',
    ]
    if body.comment:
        triples.append(f'    <{body.iri}> rdfs:comment "{_esc(body.comment)}" .')
    for sc in body.super_classes:
        triples.append(f"    <{body.iri}> rdfs:subClassOf <{sc}> .")
    for ec in body.equivalent_classes:
        triples.append(f"    <{body.iri}> owl:equivalentClass <{ec}> .")
    for dw in body.disjoint_with:
        triples.append(f"    <{body.iri}> owl:disjointWith <{dw}> .")
    if body.restrictions:
        triples.append(_restriction_triples(body.iri, body.restrictions))

    await store.sparql_update(f"""{_P}
INSERT DATA {{ GRAPH <{kg}> {{
{chr(10).join(triples)}
}} }}""", dataset=dataset)

    return Concept(
        iri=body.iri, ontology_id=ontology_id, label=body.label,
        comment=body.comment, super_classes=body.super_classes,
        equivalent_classes=body.equivalent_classes, disjoint_with=body.disjoint_with,
        restrictions=body.restrictions,
    )


# ── 상세 조회 ─────────────────────────────────────────────────────────────

@router.get("/{iri:path}", response_model=Concept)
async def get_concept(
    request: Request,
    ontology_id: str,
    iri: str,
    dataset: str | None = Query(None),
) -> Concept:
    store = request.app.state.ontology_store
    iri = unquote(iri)
    kg = await _resolve_kg_graph(store, ontology_id, dataset=dataset)
    if kg is None:
        raise HTTPException(404, detail={"code": "ONTOLOGY_NOT_FOUND", "message": f"Ontology not found: {ontology_id}"})

    if not await store.sparql_ask(f"{_P} ASK {{ GRAPH <{kg}> {{ <{iri}> a owl:Class }} }}", dataset=dataset):
        raise HTTPException(404, detail={"code": "CONCEPT_NOT_FOUND", "message": f"Not found: {iri}"})

    basic_q = f"""{_P}
SELECT ?label ?comment WHERE {{
    GRAPH <{kg}> {{ <{iri}> a owl:Class .
        OPTIONAL {{ <{iri}> rdfs:label ?label }}
        OPTIONAL {{ <{iri}> rdfs:comment ?comment }}
    }}
}} LIMIT 1"""
    sc_q = f"""{_P}
SELECT ?sc WHERE {{ GRAPH <{kg}> {{ <{iri}> rdfs:subClassOf ?sc . FILTER(isIRI(?sc)) }} }}"""
    ec_q = f"""{_P}
SELECT ?ec WHERE {{ GRAPH <{kg}> {{ <{iri}> owl:equivalentClass ?ec . FILTER(isIRI(?ec)) }} }}"""
    dw_q = f"""{_P}
SELECT ?dw WHERE {{ GRAPH <{kg}> {{ <{iri}> owl:disjointWith ?dw . FILTER(isIRI(?dw)) }} }}"""
    rest_q = f"""{_P}
SELECT ?bn ?prop ?svf ?avf ?hv ?min ?max ?exact WHERE {{
    GRAPH <{kg}> {{
        <{iri}> rdfs:subClassOf ?bn . ?bn a owl:Restriction ; owl:onProperty ?prop .
        OPTIONAL {{ ?bn owl:someValuesFrom ?svf }}
        OPTIONAL {{ ?bn owl:allValuesFrom ?avf }}
        OPTIONAL {{ ?bn owl:hasValue ?hv }}
        OPTIONAL {{ ?bn owl:minCardinality ?min }}
        OPTIONAL {{ ?bn owl:maxCardinality ?max }}
        OPTIONAL {{ ?bn owl:qualifiedCardinality ?exact }}
        FILTER(isBlank(?bn))
    }}
}}"""
    cnt_q = f"""{_P}
SELECT (COUNT(DISTINCT ?ind) AS ?cnt) WHERE {{ GRAPH <{kg}> {{ ?ind rdf:type <{iri}> }} }}"""

    basic, sc_rows, ec_rows, dw_rows, rest_rows, cnt_rows = await asyncio.gather(
        store.sparql_select(basic_q, dataset=dataset),
        store.sparql_select(sc_q,   dataset=dataset),
        store.sparql_select(ec_q,   dataset=dataset),
        store.sparql_select(dw_q,   dataset=dataset),
        store.sparql_select(rest_q, dataset=dataset),
        store.sparql_select(cnt_q,  dataset=dataset),
    )

    label = _v(basic[0].get("label")) if basic else iri
    comment = _v(basic[0].get("comment")) or None if basic else None
    super_classes = [_v(r.get("sc")) for r in sc_rows]
    equivalent_classes = [_v(r.get("ec")) for r in ec_rows]
    disjoint_with = [_v(r.get("dw")) for r in dw_rows]

    restrictions: list[PropertyRestriction] = []
    for r in rest_rows:
        prop = _v(r.get("prop"))
        if r.get("svf"):
            restrictions.append(PropertyRestriction(property_iri=prop, type="someValuesFrom", value=_v(r["svf"])))
        elif r.get("avf"):
            restrictions.append(PropertyRestriction(property_iri=prop, type="allValuesFrom", value=_v(r["avf"])))
        elif r.get("hv"):
            restrictions.append(PropertyRestriction(property_iri=prop, type="hasValue", value=_v(r["hv"])))
        elif r.get("min"):
            c = int(_v(r["min"], "1"))
            restrictions.append(PropertyRestriction(property_iri=prop, type="minCardinality", value=str(c), cardinality=c))
        elif r.get("max"):
            c = int(_v(r["max"], "1"))
            restrictions.append(PropertyRestriction(property_iri=prop, type="maxCardinality", value=str(c), cardinality=c))
        elif r.get("exact"):
            c = int(_v(r["exact"], "1"))
            restrictions.append(PropertyRestriction(property_iri=prop, type="exactCardinality", value=str(c), cardinality=c))

    individual_count = int(_v(cnt_rows[0].get("cnt"), "0")) if cnt_rows else 0

    return Concept(
        iri=iri, ontology_id=ontology_id, label=label or iri, comment=comment,
        super_classes=super_classes, equivalent_classes=equivalent_classes,
        disjoint_with=disjoint_with, restrictions=restrictions,
        individual_count=individual_count,
    )


# ── 수정 ──────────────────────────────────────────────────────────────────

@router.put("/{iri:path}", response_model=Concept)
async def update_concept(
    request: Request,
    ontology_id: str,
    iri: str,
    body: ConceptUpdate,
    dataset: str | None = Query(None),
) -> Concept:
    store = request.app.state.ontology_store
    iri = unquote(iri)
    kg = await _resolve_kg_graph(store, ontology_id, dataset=dataset)
    if kg is None:
        raise HTTPException(404, detail={"code": "ONTOLOGY_NOT_FOUND", "message": f"Ontology not found: {ontology_id}"})

    if not await store.sparql_ask(f"{_P} ASK {{ GRAPH <{kg}> {{ <{iri}> a owl:Class }} }}", dataset=dataset):
        raise HTTPException(404, detail={"code": "CONCEPT_NOT_FOUND", "message": f"Not found: {iri}"})

    if body.label is not None:
        await store.sparql_update(f"""{_P}
DELETE {{ GRAPH <{kg}> {{ <{iri}> rdfs:label ?o }} }}
INSERT {{ GRAPH <{kg}> {{ <{iri}> rdfs:label "{_esc(body.label)}" }} }}
WHERE  {{ OPTIONAL {{ GRAPH <{kg}> {{ <{iri}> rdfs:label ?o }} }} }}""", dataset=dataset)

    if body.comment is not None:
        await store.sparql_update(f"""{_P}
DELETE {{ GRAPH <{kg}> {{ <{iri}> rdfs:comment ?o }} }}
INSERT {{ GRAPH <{kg}> {{ <{iri}> rdfs:comment "{_esc(body.comment)}" }} }}
WHERE  {{ OPTIONAL {{ GRAPH <{kg}> {{ <{iri}> rdfs:comment ?o }} }} }}""", dataset=dataset)

    for pred, vals in [
        ("rdfs:subClassOf", body.super_classes),
        ("owl:equivalentClass", body.equivalent_classes),
        ("owl:disjointWith", body.disjoint_with),
    ]:
        if vals is not None:
            await store.sparql_update(f"""{_P}
DELETE {{ GRAPH <{kg}> {{ <{iri}> {pred} ?o }} }}
WHERE  {{ GRAPH <{kg}> {{ <{iri}> {pred} ?o . FILTER(isIRI(?o)) }} }}""", dataset=dataset)
            if vals:
                triples = "\n".join([f"    <{iri}> {pred} <{v}> ." for v in vals])
                await store.sparql_update(f"{_P}\nINSERT DATA {{ GRAPH <{kg}> {{\n{triples}\n}} }}", dataset=dataset)

    if body.restrictions is not None:
        await store.sparql_update(f"""{_P}
DELETE {{ GRAPH <{kg}> {{ <{iri}> rdfs:subClassOf ?bn . ?bn ?p ?o }} }}
WHERE  {{ GRAPH <{kg}> {{ <{iri}> rdfs:subClassOf ?bn . ?bn a owl:Restriction ; ?p ?o . FILTER(isBlank(?bn)) }} }}""", dataset=dataset)
        if body.restrictions:
            block = _restriction_triples(iri, body.restrictions, "upd")
            await store.sparql_update(f"{_P}\nINSERT DATA {{ GRAPH <{kg}> {{\n{block}\n}} }}", dataset=dataset)

    return await get_concept(request, ontology_id, iri, dataset=dataset)


# ── 삭제 ──────────────────────────────────────────────────────────────────

@router.delete("/{iri:path}", status_code=204)
async def delete_concept(
    request: Request,
    ontology_id: str,
    iri: str,
    dataset: str | None = Query(None),
) -> None:
    store = request.app.state.ontology_store
    iri = unquote(iri)
    kg = await _resolve_kg_graph(store, ontology_id, dataset=dataset)
    if kg is None:
        raise HTTPException(404, detail={"code": "ONTOLOGY_NOT_FOUND", "message": f"Ontology not found: {ontology_id}"})

    if not await store.sparql_ask(f"{_P} ASK {{ GRAPH <{kg}> {{ <{iri}> a owl:Class }} }}", dataset=dataset):
        raise HTTPException(404, detail={"code": "CONCEPT_NOT_FOUND", "message": f"Not found: {iri}"})

    # blank node restrictions 먼저 삭제
    await store.sparql_update(f"""{_P}
DELETE {{ GRAPH <{kg}> {{ <{iri}> rdfs:subClassOf ?bn . ?bn ?p ?o }} }}
WHERE  {{ GRAPH <{kg}> {{ <{iri}> rdfs:subClassOf ?bn . ?bn a owl:Restriction ; ?p ?o . FILTER(isBlank(?bn)) }} }}""", dataset=dataset)
    # subject 트리플 삭제
    await store.sparql_update(f"""{_P}
DELETE {{ GRAPH <{kg}> {{ <{iri}> ?p ?o }} }}
WHERE  {{ GRAPH <{kg}> {{ <{iri}> ?p ?o }} }}""", dataset=dataset)
    # object 트리플 삭제 (subClassOf 대상 등)
    await store.sparql_update(f"""{_P}
DELETE {{ GRAPH <{kg}> {{ ?s ?p <{iri}> }} }}
WHERE  {{ GRAPH <{kg}> {{ ?s ?p <{iri}> }} }}""", dataset=dataset)
