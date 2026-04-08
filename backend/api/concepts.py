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

from models.concept import Concept, ConceptCreate, ConceptUpdate, PropertyRestriction, PropertyValue
from models.ontology import PaginatedResponse
from services.ontology_graph import (
    resolve_ontology_iri,
    manual_graph_iri,
    graphs_filter_clause,
)

router = APIRouter(prefix="/ontologies/{ontology_id}/concepts", tags=["concepts"])

_P = """
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
PREFIX dc:   <http://purl.org/dc/terms/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
"""


async def _resolve_ont(store, ontology_id: str, dataset: str | None = None) -> str | None:
    """UUID(dc:identifier)로 온톨로지 IRI 반환. 없으면 None."""
    return await resolve_ontology_iri(store, ontology_id, dataset=dataset)


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _looks_like_iri(value: str) -> bool:
    v = value.strip()
    return v.startswith("http://") or v.startswith("https://") or v.startswith("urn:")


# Protege 방식: TBox axiom에 명시적으로 등장하는 named class만 포함
# (ABox [] rdf:type ?iri 패턴 제거 — 노이즈 클래스 오염 방지)
_CLASS_FILTER = """
    FILTER(isIRI(?iri))
    FILTER(?iri NOT IN (
        owl:Class, owl:NamedIndividual, owl:Ontology,
        owl:ObjectProperty, owl:DatatypeProperty, owl:AnnotationProperty,
        rdfs:Class, rdfs:Datatype, rdf:Property,
        owl:Thing, rdfs:Resource
    ))
"""

_CLASS_PATTERN = f"""
    {{ ?iri a owl:Class . {_CLASS_FILTER} }}
    UNION
    {{ ?iri a rdfs:Class . FILTER NOT EXISTS {{ ?iri a owl:Ontology }} {_CLASS_FILTER} }}
    UNION
    {{ ?iri a skos:Concept . {_CLASS_FILTER} }}
    UNION
    {{
        {{ ?iri rdfs:subClassOf ?_sc }} UNION {{ ?_sc rdfs:subClassOf ?iri }}
        {_CLASS_FILTER}
    }}
    UNION
    {{
        {{ ?_p rdfs:domain ?iri }} UNION {{ ?_p rdfs:range ?iri }}
        {_CLASS_FILTER}
    }}
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
            if _looks_like_iri(r.value):
                lines.append(f"        owl:hasValue <{r.value}> .")
            else:
                lines.append(f'        owl:hasValue "{_esc(r.value)}" .')
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
    root: bool = Query(False),            # True: 부모 없는 루트 클래스만
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    dataset: str | None = Query(None),
    graph_iris: list[str] = Query(default=[]),
) -> dict:
    store = request.app.state.ontology_store
    ont = await _resolve_ont(store, ontology_id, dataset=dataset)
    if ont is None:
        raise HTTPException(404, detail={"code": "ONTOLOGY_NOT_FOUND", "message": f"Ontology not found: {ontology_id}"})
    offset = (page - 1) * page_size
    gf = graphs_filter_clause(graph_iris, ont)

    extra = ""
    extra += _concept_keyword_filter(q)
    if super_class:
        extra += f"\n    ?iri rdfs:subClassOf <{super_class}> ."
    if root:
        # owl:Thing / rdfs:Resource 이외의 IRI 부모가 없는 클래스 = 루트
        extra += (
            f"\n    OPTIONAL {{ ?iri rdfs:subClassOf ?rootPar ."
            f" FILTER(isIRI(?rootPar)"
            f" && ?rootPar != owl:Thing"
            f" && ?rootPar != rdfs:Resource) }}"
            f"\n    FILTER(!BOUND(?rootPar))"
        )

    count_rows = await store.sparql_select(f"""{_P}
SELECT (COUNT(DISTINCT ?iri) AS ?total) WHERE {{
    GRAPH ?_g {{
        {_CLASS_PATTERN}
        {extra}
    }}
    {gf}
}}""", dataset=dataset)
    total = int(_v(count_rows[0].get("total"), "0")) if count_rows else 0

    rows = await store.sparql_select(f"""{_P}
SELECT ?iri (MIN(?lbl) AS ?label) (MIN(?cmt) AS ?comment)
       (COUNT(DISTINCT ?child) AS ?subclassCount)
       (COUNT(DISTINCT ?ind) AS ?individualCount) WHERE {{
    {{
        SELECT DISTINCT ?iri WHERE {{
            GRAPH ?_g {{
                {_CLASS_PATTERN}
                {extra}
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
ORDER BY ?lbl LIMIT {page_size} OFFSET {offset}""", dataset=dataset)

    items = [
        Concept(
            iri=_v(r.get("iri")),
            ontology_id=ontology_id,
            label=_v(r.get("label")) or _v(r.get("iri")),
            comment=_v(r.get("comment")) or None,
            individual_count=int(_v(r.get("individualCount"), "0")),
            subclass_count=int(_v(r.get("subclassCount"), "0")),
        )
        for r in rows
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size, "has_next": (page * page_size) < total}


# ── 직계 하위 클래스 (트리 lazy load) ────────────────────────────────────────

@router.get("/{iri:path}/subclasses", response_model=PaginatedResponse)
async def list_subclasses(
    request: Request,
    ontology_id: str,
    iri: str,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
    dataset: str | None = Query(None),
    graph_iris: list[str] = Query(default=[]),
) -> dict:
    """직계 하위 클래스 목록 (rdfs:subClassOf <iri>). 트리 뷰 toggle 시 호출."""
    store = request.app.state.ontology_store
    iri = unquote(iri)
    ont = await _resolve_ont(store, ontology_id, dataset=dataset)
    if ont is None:
        raise HTTPException(404, detail={"code": "ONTOLOGY_NOT_FOUND", "message": f"Ontology not found: {ontology_id}"})
    offset = (page - 1) * page_size
    gf = graphs_filter_clause(graph_iris, ont)

    count_rows = await store.sparql_select(f"""{_P}
SELECT (COUNT(DISTINCT ?iri) AS ?total) WHERE {{
    GRAPH ?_g {{ ?iri rdfs:subClassOf <{iri}> . FILTER(isIRI(?iri)) }}
    {gf}
}}""", dataset=dataset)
    total = int(_v(count_rows[0].get("total"), "0")) if count_rows else 0

    rows = await store.sparql_select(f"""{_P}
SELECT ?iri (MIN(?lbl) AS ?label) (MIN(?cmt) AS ?comment)
       (COUNT(DISTINCT ?child) AS ?subclassCount)
       (COUNT(DISTINCT ?ind) AS ?individualCount) WHERE {{
    {{
        SELECT DISTINCT ?iri WHERE {{
            GRAPH ?_g {{ ?iri rdfs:subClassOf <{iri}> . FILTER(isIRI(?iri)) }}
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
ORDER BY ?lbl LIMIT {page_size} OFFSET {offset}""", dataset=dataset)

    items = [
        Concept(
            iri=_v(r.get("iri")),
            ontology_id=ontology_id,
            label=_v(r.get("label")) or _v(r.get("iri")),
            comment=_v(r.get("comment")) or None,
            individual_count=int(_v(r.get("individualCount"), "0")),
            subclass_count=int(_v(r.get("subclassCount"), "0")),
        )
        for r in rows
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size, "has_next": (page * page_size) < total}


# ── 생성 ──────────────────────────────────────────────────────────────────

@router.post("", response_model=Concept, status_code=201)
async def create_concept(
    request: Request,
    ontology_id: str,
    body: ConceptCreate,
    dataset: str | None = Query(None),
) -> Concept:
    store = request.app.state.ontology_store
    ont = await _resolve_ont(store, ontology_id, dataset=dataset)
    if ont is None:
        raise HTTPException(404, detail={"code": "ONTOLOGY_NOT_FOUND", "message": f"Ontology not found: {ontology_id}"})
    manual = manual_graph_iri(ont)

    if await store.sparql_ask(f"{_P} ASK {{ GRAPH ?_g {{ <{body.iri}> a owl:Class }} }}", dataset=dataset):
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
INSERT DATA {{ GRAPH <{manual}> {{
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
    graph_iris: list[str] = Query(default=[]),
) -> Concept:
    store = request.app.state.ontology_store
    iri = unquote(iri)
    ont = await _resolve_ont(store, ontology_id, dataset=dataset)
    if ont is None:
        raise HTTPException(404, detail={"code": "ONTOLOGY_NOT_FOUND", "message": f"Ontology not found: {ontology_id}"})
    gf = graphs_filter_clause(graph_iris, ont)

    # 존재 확인: outgoing 트리플, rdf:type 대상, subClassOf 참여 중 하나라도 있으면 유효
    _exists = await store.sparql_ask(f"""{_P}
ASK {{
    GRAPH ?_g {{
        {{ <{iri}> ?p ?o }}
        UNION {{ [] rdf:type <{iri}> }}
        UNION {{ <{iri}> rdfs:subClassOf [] }}
        UNION {{ [] rdfs:subClassOf <{iri}> }}
    }}
    {gf}
}}""", dataset=dataset)
    if not _exists:
        raise HTTPException(404, detail={"code": "CONCEPT_NOT_FOUND", "message": f"Not found: {iri}"})

    # 이 IRI의 모든 outgoing 트리플 (blank node 제외) — 어떤 어휘든 자동 처리
    triples_q = f"""{_P}
SELECT ?p ?o WHERE {{
    GRAPH ?_g {{
        <{iri}> ?p ?o .
        FILTER(!isBlank(?o))
    }}
    {gf}
}}"""
    # blank node owl:Restriction 전용 쿼리
    rest_q = f"""{_P}
SELECT ?bn ?prop ?svf ?avf ?hv ?min ?max ?exact WHERE {{
    GRAPH ?_g {{
        <{iri}> rdfs:subClassOf ?bn . ?bn a owl:Restriction ; owl:onProperty ?prop .
        OPTIONAL {{ ?bn owl:someValuesFrom ?svf }}
        OPTIONAL {{ ?bn owl:allValuesFrom ?avf }}
        OPTIONAL {{ ?bn owl:hasValue ?hv }}
        OPTIONAL {{ ?bn owl:minCardinality ?min }}
        OPTIONAL {{ ?bn owl:maxCardinality ?max }}
        OPTIONAL {{ ?bn owl:qualifiedCardinality ?exact }}
        FILTER(isBlank(?bn))
    }}
    {gf}
}}"""
    cnt_q = f"""{_P}
SELECT (COUNT(DISTINCT ?ind) AS ?cnt) WHERE {{
    GRAPH ?_g {{ ?ind rdf:type <{iri}> }}
    {gf}
}}"""

    triples_rows, rest_rows, cnt_rows = await asyncio.gather(
        store.sparql_select(triples_q, dataset=dataset),
        store.sparql_select(rest_q,    dataset=dataset),
        store.sparql_select(cnt_q,     dataset=dataset),
    )

    # predicate URI 기반 분류 — 어휘 추가 시 여기만 수정
    _LABEL_PREDS    = {
        "http://www.w3.org/2000/01/rdf-schema#label",
        "http://www.w3.org/2004/02/skos/core#prefLabel",
        "http://www.w3.org/2004/02/skos/core#altLabel",
    }
    _COMMENT_PREDS  = {
        "http://www.w3.org/2000/01/rdf-schema#comment",
        "http://www.w3.org/2004/02/skos/core#definition",
    }
    _SUBCLASSOF  = "http://www.w3.org/2000/01/rdf-schema#subClassOf"
    _EQUIVALENT  = "http://www.w3.org/2002/07/owl#equivalentClass"
    _DISJOINT    = "http://www.w3.org/2002/07/owl#disjointWith"

    label: str = iri
    comment: str | None = None
    super_classes: list[str] = []
    equivalent_classes: list[str] = []
    disjoint_with: list[str] = []
    properties: list[PropertyValue] = []

    _KNOWN_PREDS = _LABEL_PREDS | _COMMENT_PREDS | {_SUBCLASSOF, _EQUIVALENT, _DISJOINT}

    for row in triples_rows:
        p = _v(row.get("p"))
        o = row.get("o", {})
        o_val = _v(o)
        o_type = o.get("type", "") if isinstance(o, dict) else ""
        o_is_iri = o_type == "uri"

        if p in _LABEL_PREDS:
            if label == iri:
                label = o_val
        elif p in _COMMENT_PREDS:
            if comment is None:
                comment = o_val
        elif p == _SUBCLASSOF and o_is_iri:
            super_classes.append(o_val)
        elif p == _EQUIVALENT and o_is_iri:
            equivalent_classes.append(o_val)
        elif p == _DISJOINT and o_is_iri:
            disjoint_with.append(o_val)
        elif p not in _KNOWN_PREDS:
            properties.append(PropertyValue(
                predicate=p,
                value=o_val,
                value_type="uri" if o_is_iri else "literal",
                datatype=o.get("datatype") if isinstance(o, dict) else None,
                language=o.get("xml:lang") if isinstance(o, dict) else None,
            ))

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
        individual_count=individual_count, properties=properties,
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
    ont = await _resolve_ont(store, ontology_id, dataset=dataset)
    if ont is None:
        raise HTTPException(404, detail={"code": "ONTOLOGY_NOT_FOUND", "message": f"Ontology not found: {ontology_id}"})
    manual = manual_graph_iri(ont)

    if not await store.sparql_ask(f"{_P} ASK {{ GRAPH ?_g {{ <{iri}> a owl:Class }} }}", dataset=dataset):
        raise HTTPException(404, detail={"code": "CONCEPT_NOT_FOUND", "message": f"Not found: {iri}"})

    if body.label is not None:
        await store.sparql_update(f"""{_P}
DELETE {{ GRAPH ?_g {{ <{iri}> rdfs:label ?o }} }}
INSERT {{ GRAPH <{manual}> {{ <{iri}> rdfs:label "{_esc(body.label)}" }} }}
WHERE  {{ OPTIONAL {{ GRAPH ?_g {{ <{iri}> rdfs:label ?o }} }} }}""", dataset=dataset)

    if body.comment is not None:
        await store.sparql_update(f"""{_P}
DELETE {{ GRAPH ?_g {{ <{iri}> rdfs:comment ?o }} }}
INSERT {{ GRAPH <{manual}> {{ <{iri}> rdfs:comment "{_esc(body.comment)}" }} }}
WHERE  {{ OPTIONAL {{ GRAPH ?_g {{ <{iri}> rdfs:comment ?o }} }} }}""", dataset=dataset)

    for pred, vals in [
        ("rdfs:subClassOf", body.super_classes),
        ("owl:equivalentClass", body.equivalent_classes),
        ("owl:disjointWith", body.disjoint_with),
    ]:
        if vals is not None:
            await store.sparql_update(f"""{_P}
DELETE {{ GRAPH ?_g {{ <{iri}> {pred} ?o }} }}
WHERE  {{ GRAPH ?_g {{ <{iri}> {pred} ?o . FILTER(isIRI(?o)) }} }}""", dataset=dataset)
            if vals:
                triples = "\n".join([f"    <{iri}> {pred} <{v}> ." for v in vals])
                await store.sparql_update(f"{_P}\nINSERT DATA {{ GRAPH <{manual}> {{\n{triples}\n}} }}", dataset=dataset)

    if body.restrictions is not None:
        await store.sparql_update(f"""{_P}
DELETE {{ GRAPH ?_g {{ <{iri}> rdfs:subClassOf ?bn . ?bn ?p ?o }} }}
WHERE  {{ GRAPH ?_g {{ <{iri}> rdfs:subClassOf ?bn . ?bn a owl:Restriction ; ?p ?o . FILTER(isBlank(?bn)) }} }}""", dataset=dataset)
        if body.restrictions:
            block = _restriction_triples(iri, body.restrictions, "upd")
            await store.sparql_update(f"{_P}\nINSERT DATA {{ GRAPH <{manual}> {{\n{block}\n}} }}", dataset=dataset)

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
    ont = await _resolve_ont(store, ontology_id, dataset=dataset)
    if ont is None:
        raise HTTPException(404, detail={"code": "ONTOLOGY_NOT_FOUND", "message": f"Ontology not found: {ontology_id}"})

    if not await store.sparql_ask(f"{_P} ASK {{ GRAPH ?_g {{ <{iri}> a owl:Class }} }}", dataset=dataset):
        raise HTTPException(404, detail={"code": "CONCEPT_NOT_FOUND", "message": f"Not found: {iri}"})

    # blank node restrictions 먼저 삭제 (모든 그래프에서)
    await store.sparql_update(f"""{_P}
DELETE {{ GRAPH ?_g {{ <{iri}> rdfs:subClassOf ?bn . ?bn ?p ?o }} }}
WHERE  {{ GRAPH ?_g {{ <{iri}> rdfs:subClassOf ?bn . ?bn a owl:Restriction ; ?p ?o . FILTER(isBlank(?bn)) }} }}""", dataset=dataset)
    # subject 트리플 삭제 (모든 그래프에서)
    await store.sparql_update(f"""{_P}
DELETE {{ GRAPH ?_g {{ <{iri}> ?p ?o }} }}
WHERE  {{ GRAPH ?_g {{ <{iri}> ?p ?o }} }}""", dataset=dataset)
    # object 트리플 삭제 (subClassOf 대상 등, 모든 그래프에서)
    await store.sparql_update(f"""{_P}
DELETE {{ GRAPH ?_g {{ ?s ?p <{iri}> }} }}
WHERE  {{ GRAPH ?_g {{ ?s ?p <{iri}> }} }}""", dataset=dataset)
