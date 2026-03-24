"""
api/concepts.py — Concept(owl:Class) CRUD 라우터

엔드포인트:
  GET    /ontologies/{id}/concepts           Concept 목록
  POST   /ontologies/{id}/concepts           Concept 생성
  GET    /ontologies/{id}/concepts/{iri}     Concept 상세
  PUT    /ontologies/{id}/concepts/{iri}     Concept 수정
  DELETE /ontologies/{id}/concepts/{iri}     Concept 삭제
"""

from typing import Annotated
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException, Query, Request

from models.concept import Concept, ConceptCreate, ConceptUpdate, PropertyRestriction
from models.ontology import PaginatedResponse

router = APIRouter(prefix="/ontologies/{ontology_id}/concepts", tags=["concepts"])

_P = """
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
"""


def _tbox(ontology_id: str) -> str:
    return f"{ontology_id}/tbox"


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


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
    q: str | None = Query(None),
    super_class: str | None = Query(None, alias="superClass"),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict:
    store = request.app.state.ontology_store
    tbox = _tbox(ontology_id)
    offset = (page - 1) * page_size

    extra = ""
    if q:
        extra += f'\n    FILTER(CONTAINS(LCASE(STR(?label)), "{_esc(q.lower())}"))'
    if super_class:
        extra += f"\n    ?iri rdfs:subClassOf <{super_class}> ."

    count_rows = await store.sparql_select(f"""{_P}
SELECT (COUNT(DISTINCT ?iri) AS ?total) WHERE {{
    GRAPH <{tbox}> {{ ?iri a owl:Class . OPTIONAL {{ ?iri rdfs:label ?label }} {extra} }}
}}""")
    total = int(_v(count_rows[0].get("total"), "0")) if count_rows else 0

    rows = await store.sparql_select(f"""{_P}
SELECT ?iri ?label ?comment (COUNT(DISTINCT ?ind) AS ?individualCount) WHERE {{
    GRAPH <{tbox}> {{
        ?iri a owl:Class .
        OPTIONAL {{ ?iri rdfs:label ?label }}
        OPTIONAL {{ ?iri rdfs:comment ?comment }}
        {extra}
    }}
    OPTIONAL {{ ?ind rdf:type ?iri }}
}} GROUP BY ?iri ?label ?comment
ORDER BY ?label LIMIT {page_size} OFFSET {offset}""")

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
async def create_concept(request: Request, ontology_id: str, body: ConceptCreate) -> Concept:
    store = request.app.state.ontology_store
    graph_store = request.app.state.graph_store
    tbox = _tbox(ontology_id)

    if await store.sparql_ask(f"{_P} ASK {{ GRAPH <{tbox}> {{ <{body.iri}> a owl:Class }} }}"):
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
INSERT DATA {{ GRAPH <{tbox}> {{
{chr(10).join(triples)}
}} }}""")

    await graph_store.upsert_concept(ontology_id, body.iri, body.label, body.super_classes)

    return Concept(
        iri=body.iri, ontology_id=ontology_id, label=body.label,
        comment=body.comment, super_classes=body.super_classes,
        equivalent_classes=body.equivalent_classes, disjoint_with=body.disjoint_with,
        restrictions=body.restrictions,
    )


# ── 상세 조회 ─────────────────────────────────────────────────────────────

@router.get("/{iri:path}", response_model=Concept)
async def get_concept(request: Request, ontology_id: str, iri: str) -> Concept:
    store = request.app.state.ontology_store
    iri = unquote(iri)
    tbox = _tbox(ontology_id)

    if not await store.sparql_ask(f"{_P} ASK {{ GRAPH <{tbox}> {{ <{iri}> a owl:Class }} }}"):
        raise HTTPException(404, detail={"code": "CONCEPT_NOT_FOUND", "message": f"Not found: {iri}"})

    basic = await store.sparql_select(f"""{_P}
SELECT ?label ?comment WHERE {{
    GRAPH <{tbox}> {{ <{iri}> a owl:Class .
        OPTIONAL {{ <{iri}> rdfs:label ?label }}
        OPTIONAL {{ <{iri}> rdfs:comment ?comment }}
    }}
}} LIMIT 1""")
    label = _v(basic[0].get("label")) if basic else iri
    comment = _v(basic[0].get("comment")) or None if basic else None

    sc_rows = await store.sparql_select(f"""{_P}
SELECT ?sc WHERE {{ GRAPH <{tbox}> {{ <{iri}> rdfs:subClassOf ?sc . FILTER(isIRI(?sc)) }} }}""")
    super_classes = [_v(r.get("sc")) for r in sc_rows]

    ec_rows = await store.sparql_select(f"""{_P}
SELECT ?ec WHERE {{ GRAPH <{tbox}> {{ <{iri}> owl:equivalentClass ?ec . FILTER(isIRI(?ec)) }} }}""")
    equivalent_classes = [_v(r.get("ec")) for r in ec_rows]

    dw_rows = await store.sparql_select(f"""{_P}
SELECT ?dw WHERE {{ GRAPH <{tbox}> {{ <{iri}> owl:disjointWith ?dw . FILTER(isIRI(?dw)) }} }}""")
    disjoint_with = [_v(r.get("dw")) for r in dw_rows]

    rest_rows = await store.sparql_select(f"""{_P}
SELECT ?bn ?prop ?svf ?avf ?hv ?min ?max ?exact WHERE {{
    GRAPH <{tbox}> {{
        <{iri}> rdfs:subClassOf ?bn . ?bn a owl:Restriction ; owl:onProperty ?prop .
        OPTIONAL {{ ?bn owl:someValuesFrom ?svf }}
        OPTIONAL {{ ?bn owl:allValuesFrom ?avf }}
        OPTIONAL {{ ?bn owl:hasValue ?hv }}
        OPTIONAL {{ ?bn owl:minCardinality ?min }}
        OPTIONAL {{ ?bn owl:maxCardinality ?max }}
        OPTIONAL {{ ?bn owl:qualifiedCardinality ?exact }}
        FILTER(isBlank(?bn))
    }}
}}""")
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

    cnt_rows = await store.sparql_select(f"""{_P}
SELECT (COUNT(DISTINCT ?ind) AS ?cnt) WHERE {{ ?ind rdf:type <{iri}> . }}""")
    individual_count = int(_v(cnt_rows[0].get("cnt"), "0")) if cnt_rows else 0

    return Concept(
        iri=iri, ontology_id=ontology_id, label=label or iri, comment=comment,
        super_classes=super_classes, equivalent_classes=equivalent_classes,
        disjoint_with=disjoint_with, restrictions=restrictions,
        individual_count=individual_count,
    )


# ── 수정 ──────────────────────────────────────────────────────────────────

@router.put("/{iri:path}", response_model=Concept)
async def update_concept(request: Request, ontology_id: str, iri: str, body: ConceptUpdate) -> Concept:
    store = request.app.state.ontology_store
    graph_store = request.app.state.graph_store
    iri = unquote(iri)
    tbox = _tbox(ontology_id)

    if not await store.sparql_ask(f"{_P} ASK {{ GRAPH <{tbox}> {{ <{iri}> a owl:Class }} }}"):
        raise HTTPException(404, detail={"code": "CONCEPT_NOT_FOUND", "message": f"Not found: {iri}"})

    if body.label is not None:
        await store.sparql_update(f"""{_P}
DELETE {{ GRAPH <{tbox}> {{ <{iri}> rdfs:label ?o }} }}
INSERT {{ GRAPH <{tbox}> {{ <{iri}> rdfs:label "{_esc(body.label)}" }} }}
WHERE  {{ OPTIONAL {{ GRAPH <{tbox}> {{ <{iri}> rdfs:label ?o }} }} }}""")

    if body.comment is not None:
        await store.sparql_update(f"""{_P}
DELETE {{ GRAPH <{tbox}> {{ <{iri}> rdfs:comment ?o }} }}
INSERT {{ GRAPH <{tbox}> {{ <{iri}> rdfs:comment "{_esc(body.comment)}" }} }}
WHERE  {{ OPTIONAL {{ GRAPH <{tbox}> {{ <{iri}> rdfs:comment ?o }} }} }}""")

    for pred, vals in [
        ("rdfs:subClassOf", body.super_classes),
        ("owl:equivalentClass", body.equivalent_classes),
        ("owl:disjointWith", body.disjoint_with),
    ]:
        if vals is not None:
            await store.sparql_update(f"""{_P}
DELETE {{ GRAPH <{tbox}> {{ <{iri}> {pred} ?o }} }}
WHERE  {{ GRAPH <{tbox}> {{ <{iri}> {pred} ?o . FILTER(isIRI(?o)) }} }}""")
            if vals:
                triples = "\n".join([f"    <{iri}> {pred} <{v}> ." for v in vals])
                await store.sparql_update(f"{_P}\nINSERT DATA {{ GRAPH <{tbox}> {{\n{triples}\n}} }}")

    if body.restrictions is not None:
        await store.sparql_update(f"""{_P}
DELETE {{ GRAPH <{tbox}> {{ <{iri}> rdfs:subClassOf ?bn . ?bn ?p ?o }} }}
WHERE  {{ GRAPH <{tbox}> {{ <{iri}> rdfs:subClassOf ?bn . ?bn a owl:Restriction ; ?p ?o . FILTER(isBlank(?bn)) }} }}""")
        if body.restrictions:
            block = _restriction_triples(iri, body.restrictions, "upd")
            await store.sparql_update(f"{_P}\nINSERT DATA {{ GRAPH <{tbox}> {{\n{block}\n}} }}")

    updated = await get_concept(request, ontology_id, iri)
    await graph_store.upsert_concept(ontology_id, iri, updated.label, updated.super_classes)
    return updated


# ── 삭제 ──────────────────────────────────────────────────────────────────

@router.delete("/{iri:path}", status_code=204)
async def delete_concept(request: Request, ontology_id: str, iri: str) -> None:
    store = request.app.state.ontology_store
    iri = unquote(iri)
    tbox = _tbox(ontology_id)

    if not await store.sparql_ask(f"{_P} ASK {{ GRAPH <{tbox}> {{ <{iri}> a owl:Class }} }}"):
        raise HTTPException(404, detail={"code": "CONCEPT_NOT_FOUND", "message": f"Not found: {iri}"})

    # blank node restrictions 먼저 삭제
    await store.sparql_update(f"""{_P}
DELETE {{ GRAPH <{tbox}> {{ <{iri}> rdfs:subClassOf ?bn . ?bn ?p ?o }} }}
WHERE  {{ GRAPH <{tbox}> {{ <{iri}> rdfs:subClassOf ?bn . ?bn a owl:Restriction ; ?p ?o . FILTER(isBlank(?bn)) }} }}""")
    # subject 트리플 삭제
    await store.sparql_update(f"""{_P}
DELETE {{ GRAPH <{tbox}> {{ <{iri}> ?p ?o }} }}
WHERE  {{ GRAPH <{tbox}> {{ <{iri}> ?p ?o }} }}""")
    # object 트리플 삭제 (subClassOf 대상 등)
    await store.sparql_update(f"""{_P}
DELETE {{ GRAPH <{tbox}> {{ ?s ?p <{iri}> }} }}
WHERE  {{ GRAPH <{tbox}> {{ ?s ?p <{iri}> }} }}""")
