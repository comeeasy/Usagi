"""
api/properties.py — ObjectProperty / DataProperty CRUD 라우터

엔드포인트:
  GET    /ontologies/{id}/properties           Property 목록
  POST   /ontologies/{id}/properties           Property 생성
  GET    /ontologies/{id}/properties/{iri}     Property 상세
  PUT    /ontologies/{id}/properties/{iri}     Property 수정
  DELETE /ontologies/{id}/properties/{iri}     Property 삭제
"""

from typing import Annotated, Literal, Union
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException, Query, Request

from models.ontology import PaginatedResponse
from models.property import (
    DataProperty,
    DataPropertyCreate,
    DataPropertyUpdate,
    ObjectProperty,
    ObjectPropertyCreate,
    ObjectPropertyUpdate,
)

router = APIRouter(prefix="/ontologies/{ontology_id}/properties", tags=["properties"])

_P = """
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
"""

_XSD_BASE = "http://www.w3.org/2001/XMLSchema#"

_CHAR_MAP = {
    "Functional": "owl:FunctionalProperty",
    "InverseFunctional": "owl:InverseFunctionalProperty",
    "Transitive": "owl:TransitiveProperty",
    "Symmetric": "owl:SymmetricProperty",
    "Asymmetric": "owl:AsymmetricProperty",
    "Reflexive": "owl:ReflexiveProperty",
    "Irreflexive": "owl:IrreflexiveProperty",
}
_CHAR_FULL = {
    "http://www.w3.org/2002/07/owl#FunctionalProperty": "Functional",
    "http://www.w3.org/2002/07/owl#InverseFunctionalProperty": "InverseFunctional",
    "http://www.w3.org/2002/07/owl#TransitiveProperty": "Transitive",
    "http://www.w3.org/2002/07/owl#SymmetricProperty": "Symmetric",
    "http://www.w3.org/2002/07/owl#AsymmetricProperty": "Asymmetric",
    "http://www.w3.org/2002/07/owl#ReflexiveProperty": "Reflexive",
    "http://www.w3.org/2002/07/owl#IrreflexiveProperty": "Irreflexive",
}


async def _resolve_tbox(store, ontology_id: str, dataset: str | None = None) -> str | None:
    """UUID(dc:identifier)로 온톨로지 IRI 조회 후 tbox IRI 반환. 없으면 None."""
    rows = await store.sparql_select(f"""
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX dc:  <http://purl.org/dc/terms/>
        SELECT ?iri WHERE {{
            GRAPH ?g {{ ?iri a owl:Ontology ; dc:identifier "{ontology_id}" }}
        }} LIMIT 1
    """, dataset=dataset)
    if not rows:
        return None
    return f"{rows[0]['iri']['value']}/tbox"


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


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


# ── 내부 fetch 헬퍼 ──────────────────────────────────────────────────────

async def _fetch_object_property(store, iri: str, ontology_id: str, tbox: str, dataset: str | None = None) -> ObjectProperty:
    basic = await store.sparql_select(f"""{_P}
SELECT ?label ?comment ?inv WHERE {{
    GRAPH <{tbox}> {{ <{iri}> a owl:ObjectProperty .
        OPTIONAL {{ <{iri}> rdfs:label ?label }}
        OPTIONAL {{ <{iri}> rdfs:comment ?comment }}
        OPTIONAL {{ <{iri}> owl:inverseOf ?inv }}
    }}
}} LIMIT 1""", dataset=dataset)
    b = basic[0] if basic else {}
    label = _v(b.get("label")) or iri
    comment = _v(b.get("comment")) or None
    inverse_of = _v(b.get("inv")) or None

    domain = [_v(r.get("d")) for r in await store.sparql_select(
        f"{_P}\nSELECT ?d WHERE {{ GRAPH <{tbox}> {{ <{iri}> rdfs:domain ?d . FILTER(isIRI(?d)) }} }}", dataset=dataset)]
    range_ = [_v(r.get("r")) for r in await store.sparql_select(
        f"{_P}\nSELECT ?r WHERE {{ GRAPH <{tbox}> {{ <{iri}> rdfs:range ?r . FILTER(isIRI(?r)) }} }}", dataset=dataset)]
    super_props = [_v(r.get("sp")) for r in await store.sparql_select(
        f"{_P}\nSELECT ?sp WHERE {{ GRAPH <{tbox}> {{ <{iri}> rdfs:subPropertyOf ?sp . FILTER(isIRI(?sp)) }} }}", dataset=dataset)]

    char_rows = await store.sparql_select(f"""{_P}
SELECT ?t WHERE {{
    GRAPH <{tbox}> {{
        <{iri}> a ?t .
        FILTER(?t IN (owl:FunctionalProperty, owl:InverseFunctionalProperty,
                      owl:TransitiveProperty, owl:SymmetricProperty,
                      owl:AsymmetricProperty, owl:ReflexiveProperty, owl:IrreflexiveProperty))
    }}
}}""", dataset=dataset)
    characteristics = [_CHAR_FULL[_v(r.get("t"))] for r in char_rows if _v(r.get("t")) in _CHAR_FULL]

    return ObjectProperty(
        iri=iri, ontology_id=ontology_id, label=label, comment=comment,
        domain=domain, range=range_, super_properties=super_props,
        inverse_of=inverse_of, characteristics=characteristics,
    )


async def _fetch_data_property(store, iri: str, ontology_id: str, tbox: str, dataset: str | None = None) -> DataProperty:
    basic = await store.sparql_select(f"""{_P}
SELECT ?label ?comment WHERE {{
    GRAPH <{tbox}> {{ <{iri}> a owl:DatatypeProperty .
        OPTIONAL {{ <{iri}> rdfs:label ?label }}
        OPTIONAL {{ <{iri}> rdfs:comment ?comment }}
    }}
}} LIMIT 1""", dataset=dataset)
    b = basic[0] if basic else {}

    domain = [_v(r.get("d")) for r in await store.sparql_select(
        f"{_P}\nSELECT ?d WHERE {{ GRAPH <{tbox}> {{ <{iri}> rdfs:domain ?d . FILTER(isIRI(?d)) }} }}", dataset=dataset)]
    range_ = [_xsd_short(_v(r.get("r"))) for r in await store.sparql_select(
        f"{_P}\nSELECT ?r WHERE {{ GRAPH <{tbox}> {{ <{iri}> rdfs:range ?r }} }}", dataset=dataset)
               if r.get("r")]
    super_props = [_v(r.get("sp")) for r in await store.sparql_select(
        f"{_P}\nSELECT ?sp WHERE {{ GRAPH <{tbox}> {{ <{iri}> rdfs:subPropertyOf ?sp . FILTER(isIRI(?sp)) }} }}", dataset=dataset)]
    is_functional = await store.sparql_ask(
        f"{_P}\nASK {{ GRAPH <{tbox}> {{ <{iri}> a owl:FunctionalProperty }} }}", dataset=dataset)

    return DataProperty(
        iri=iri, ontology_id=ontology_id,
        label=_v(b.get("label")) or iri,
        comment=_v(b.get("comment")) or None,
        domain=domain, range=range_, super_properties=super_props,
        is_functional=is_functional,
    )


# ── 목록 ──────────────────────────────────────────────────────────────────

@router.get("", response_model=PaginatedResponse)
async def list_properties(
    request: Request,
    ontology_id: str,
    kind: Literal["object", "data"] | None = Query(None),
    domain: str | None = Query(None),
    range_: str | None = Query(None, alias="range"),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    dataset: str = Query("ontology"),
) -> dict:
    store = request.app.state.ontology_store
    tbox = await _resolve_tbox(store, ontology_id, dataset=dataset)
    if tbox is None:
        raise HTTPException(404, detail={"code": "ONTOLOGY_NOT_FOUND", "message": f"Ontology not found: {ontology_id}"})
    offset = (page - 1) * page_size

    domain_f = f"?iri rdfs:domain <{domain}> ." if domain else ""
    range_f = f"?iri rdfs:range <{range_}> ." if range_ else ""

    async def fetch_type(owl_type: str) -> tuple[int, list]:
        cnt = await store.sparql_select(f"""{_P}
SELECT (COUNT(DISTINCT ?iri) AS ?total) WHERE {{
    GRAPH <{tbox}> {{ ?iri a {owl_type} . {domain_f} {range_f} }}
}}""", dataset=dataset)
        total = int(_v(cnt[0].get("total"), "0")) if cnt else 0
        rows = await store.sparql_select(f"""{_P}
SELECT DISTINCT ?iri WHERE {{
    GRAPH <{tbox}> {{ ?iri a {owl_type} . {domain_f} {range_f} }}
}} ORDER BY ?iri LIMIT {page_size} OFFSET {offset}""", dataset=dataset)
        return total, rows

    items: list = []
    total = 0

    if kind != "data":
        obj_total, obj_rows = await fetch_type("owl:ObjectProperty")
        total += obj_total
        for r in obj_rows:
            items.append(await _fetch_object_property(store, _v(r.get("iri")), ontology_id, tbox, dataset=dataset))

    if kind != "object":
        data_total, data_rows = await fetch_type("owl:DatatypeProperty")
        total += data_total
        for r in data_rows:
            items.append(await _fetch_data_property(store, _v(r.get("iri")), ontology_id, tbox, dataset=dataset))

    return {"items": items, "total": total, "page": page, "page_size": page_size}


# ── 생성 ──────────────────────────────────────────────────────────────────

@router.post("", status_code=201)
async def create_property(
    request: Request,
    ontology_id: str,
    body: Union[ObjectPropertyCreate, DataPropertyCreate],
    dataset: str = Query("ontology"),
):
    store = request.app.state.ontology_store
    tbox = await _resolve_tbox(store, ontology_id, dataset=dataset)
    if tbox is None:
        raise HTTPException(404, detail={"code": "ONTOLOGY_NOT_FOUND", "message": f"Ontology not found: {ontology_id}"})

    dup = await store.sparql_ask(f"""{_P}
ASK {{ GRAPH <{tbox}> {{
    {{ <{body.iri}> a owl:ObjectProperty }} UNION {{ <{body.iri}> a owl:DatatypeProperty }}
}} }}""", dataset=dataset)
    if dup:
        raise HTTPException(409, detail={"code": "PROPERTY_IRI_DUPLICATE", "message": f"IRI exists: {body.iri}"})

    triples = []
    if isinstance(body, ObjectPropertyCreate):
        types = ["owl:ObjectProperty"] + [_CHAR_MAP[c] for c in body.characteristics if c in _CHAR_MAP]
        triples.append(f"    <{body.iri}> a {', '.join(types)} .")
        triples.append(f'    <{body.iri}> rdfs:label "{_esc(body.label)}" .')
        if body.comment:
            triples.append(f'    <{body.iri}> rdfs:comment "{_esc(body.comment)}" .')
        for d in body.domain:
            triples.append(f"    <{body.iri}> rdfs:domain <{d}> .")
        for r in body.range:
            triples.append(f"    <{body.iri}> rdfs:range <{r}> .")
        for sp in body.super_properties:
            triples.append(f"    <{body.iri}> rdfs:subPropertyOf <{sp}> .")
        if body.inverse_of:
            triples.append(f"    <{body.iri}> owl:inverseOf <{body.inverse_of}> .")
    else:
        types = ["owl:DatatypeProperty"] + (["owl:FunctionalProperty"] if body.is_functional else [])
        triples.append(f"    <{body.iri}> a {', '.join(types)} .")
        triples.append(f'    <{body.iri}> rdfs:label "{_esc(body.label)}" .')
        if body.comment:
            triples.append(f'    <{body.iri}> rdfs:comment "{_esc(body.comment)}" .')
        for d in body.domain:
            triples.append(f"    <{body.iri}> rdfs:domain <{d}> .")
        for r in body.range:
            triples.append(f"    <{body.iri}> rdfs:range <{_xsd_full(r)}> .")
        for sp in body.super_properties:
            triples.append(f"    <{body.iri}> rdfs:subPropertyOf <{sp}> .")

    await store.sparql_update(f"""{_P}
INSERT DATA {{ GRAPH <{tbox}> {{
{chr(10).join(triples)}
}} }}""", dataset=dataset)

    if isinstance(body, ObjectPropertyCreate):
        return await _fetch_object_property(store, body.iri, ontology_id, tbox, dataset=dataset)
    return await _fetch_data_property(store, body.iri, ontology_id, tbox, dataset=dataset)


# ── 상세 조회 ─────────────────────────────────────────────────────────────

@router.get("/{iri:path}")
async def get_property(
    request: Request,
    ontology_id: str,
    iri: str,
    dataset: str = Query("ontology"),
):
    store = request.app.state.ontology_store
    iri = unquote(iri)
    tbox = await _resolve_tbox(store, ontology_id, dataset=dataset)
    if tbox is None:
        raise HTTPException(404, detail={"code": "ONTOLOGY_NOT_FOUND", "message": f"Ontology not found: {ontology_id}"})

    is_obj = await store.sparql_ask(f"{_P}\nASK {{ GRAPH <{tbox}> {{ <{iri}> a owl:ObjectProperty }} }}", dataset=dataset)
    is_data = await store.sparql_ask(f"{_P}\nASK {{ GRAPH <{tbox}> {{ <{iri}> a owl:DatatypeProperty }} }}", dataset=dataset)

    if not is_obj and not is_data:
        raise HTTPException(404, detail={"code": "PROPERTY_NOT_FOUND", "message": f"Not found: {iri}"})

    return (await _fetch_object_property(store, iri, ontology_id, tbox, dataset=dataset)
            if is_obj else
            await _fetch_data_property(store, iri, ontology_id, tbox, dataset=dataset))


# ── 수정 ──────────────────────────────────────────────────────────────────

@router.put("/{iri:path}")
async def update_property(
    request: Request,
    ontology_id: str,
    iri: str,
    body: Union[ObjectPropertyUpdate, DataPropertyUpdate],
    dataset: str = Query("ontology"),
):
    store = request.app.state.ontology_store
    iri = unquote(iri)
    tbox = await _resolve_tbox(store, ontology_id, dataset=dataset)
    if tbox is None:
        raise HTTPException(404, detail={"code": "ONTOLOGY_NOT_FOUND", "message": f"Ontology not found: {ontology_id}"})

    is_obj = await store.sparql_ask(f"{_P}\nASK {{ GRAPH <{tbox}> {{ <{iri}> a owl:ObjectProperty }} }}", dataset=dataset)
    is_data = await store.sparql_ask(f"{_P}\nASK {{ GRAPH <{tbox}> {{ <{iri}> a owl:DatatypeProperty }} }}", dataset=dataset)
    if not is_obj and not is_data:
        raise HTTPException(404, detail={"code": "PROPERTY_NOT_FOUND", "message": f"Not found: {iri}"})

    async def _replace(pred: str, new_val: str | None):
        if new_val is None:
            return
        await store.sparql_update(f"""{_P}
DELETE {{ GRAPH <{tbox}> {{ <{iri}> {pred} ?o }} }}
INSERT {{ GRAPH <{tbox}> {{ <{iri}> {pred} "{_esc(new_val)}" }} }}
WHERE  {{ OPTIONAL {{ GRAPH <{tbox}> {{ <{iri}> {pred} ?o }} }} }}""", dataset=dataset)

    async def _replace_iris(pred: str, iris: list[str] | None):
        if iris is None:
            return
        await store.sparql_update(f"""{_P}
DELETE {{ GRAPH <{tbox}> {{ <{iri}> {pred} ?o }} }}
WHERE  {{ GRAPH <{tbox}> {{ <{iri}> {pred} ?o }} }}""", dataset=dataset)
        if iris:
            triples = "\n".join([f"    <{iri}> {pred} <{v}> ." for v in iris])
            await store.sparql_update(f"{_P}\nINSERT DATA {{ GRAPH <{tbox}> {{\n{triples}\n}} }}", dataset=dataset)

    await _replace("rdfs:label", body.label)
    await _replace("rdfs:comment", body.comment)
    await _replace_iris("rdfs:domain", body.domain)
    await _replace_iris("rdfs:subPropertyOf", body.super_properties)

    if body.range is not None:
        await store.sparql_update(f"""{_P}
DELETE {{ GRAPH <{tbox}> {{ <{iri}> rdfs:range ?o }} }}
WHERE  {{ GRAPH <{tbox}> {{ <{iri}> rdfs:range ?o }} }}""", dataset=dataset)
        if body.range:
            if is_obj:
                triples = "\n".join([f"    <{iri}> rdfs:range <{r}> ." for r in body.range])
            else:
                triples = "\n".join([f"    <{iri}> rdfs:range <{_xsd_full(r)}> ." for r in body.range])
            await store.sparql_update(f"{_P}\nINSERT DATA {{ GRAPH <{tbox}> {{\n{triples}\n}} }}", dataset=dataset)

    if is_obj and isinstance(body, ObjectPropertyUpdate):
        if body.inverse_of is not None:
            await store.sparql_update(f"""{_P}
DELETE {{ GRAPH <{tbox}> {{ <{iri}> owl:inverseOf ?o }} }}
WHERE  {{ GRAPH <{tbox}> {{ <{iri}> owl:inverseOf ?o }} }}""", dataset=dataset)
            if body.inverse_of:
                await store.sparql_update(
                    f"{_P}\nINSERT DATA {{ GRAPH <{tbox}> {{ <{iri}> owl:inverseOf <{body.inverse_of}> . }} }}", dataset=dataset)

        if body.characteristics is not None:
            await store.sparql_update(f"""{_P}
DELETE {{ GRAPH <{tbox}> {{ <{iri}> a ?t }} }}
WHERE  {{ GRAPH <{tbox}> {{ <{iri}> a ?t .
    FILTER(?t IN (owl:FunctionalProperty, owl:InverseFunctionalProperty,
                  owl:TransitiveProperty, owl:SymmetricProperty,
                  owl:AsymmetricProperty, owl:ReflexiveProperty, owl:IrreflexiveProperty)) }} }}""", dataset=dataset)
            if body.characteristics:
                triples = "\n".join([
                    f"    <{iri}> a {_CHAR_MAP[c]} ."
                    for c in body.characteristics if c in _CHAR_MAP
                ])
                await store.sparql_update(f"{_P}\nINSERT DATA {{ GRAPH <{tbox}> {{\n{triples}\n}} }}", dataset=dataset)

    if is_data and isinstance(body, DataPropertyUpdate) and body.is_functional is not None:
        if body.is_functional:
            await store.sparql_update(
                f"{_P}\nINSERT DATA {{ GRAPH <{tbox}> {{ <{iri}> a owl:FunctionalProperty . }} }}", dataset=dataset)
        else:
            await store.sparql_update(f"""{_P}
DELETE {{ GRAPH <{tbox}> {{ <{iri}> a owl:FunctionalProperty }} }}
WHERE  {{ GRAPH <{tbox}> {{ <{iri}> a owl:FunctionalProperty }} }}""", dataset=dataset)

    return await get_property(request, ontology_id, iri, dataset=dataset)


# ── 삭제 ──────────────────────────────────────────────────────────────────

@router.delete("/{iri:path}", status_code=204)
async def delete_property(
    request: Request,
    ontology_id: str,
    iri: str,
    dataset: str = Query("ontology"),
) -> None:
    store = request.app.state.ontology_store
    iri = unquote(iri)
    tbox = await _resolve_tbox(store, ontology_id, dataset=dataset)
    if tbox is None:
        raise HTTPException(404, detail={"code": "ONTOLOGY_NOT_FOUND", "message": f"Ontology not found: {ontology_id}"})

    exists = await store.sparql_ask(f"""{_P}
ASK {{ GRAPH <{tbox}> {{
    {{ <{iri}> a owl:ObjectProperty }} UNION {{ <{iri}> a owl:DatatypeProperty }}
}} }}""", dataset=dataset)
    if not exists:
        raise HTTPException(404, detail={"code": "PROPERTY_NOT_FOUND", "message": f"Not found: {iri}"})

    await store.sparql_update(f"""{_P}
DELETE {{ GRAPH <{tbox}> {{ <{iri}> ?p ?o }} }}
WHERE  {{ GRAPH <{tbox}> {{ <{iri}> ?p ?o }} }}""", dataset=dataset)
    await store.sparql_update(f"""{_P}
DELETE {{ GRAPH <{tbox}> {{ ?s ?p <{iri}> }} }}
WHERE  {{ GRAPH <{tbox}> {{ ?s ?p <{iri}> }} }}""", dataset=dataset)
