"""
Tests for SearchService — SPARQL 키워드 검색.
"""
import pytest
import pytest_asyncio
from services.ontology_store import OntologyStore
from services.search_service import search_entities, search_relations, vector_search

ONT_IRI = "https://test.example.org/onto"
KG = f"{ONT_IRI}/kg"

_PREFIXES = """
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
"""


@pytest_asyncio.fixture
async def store_with_data():
    store = OntologyStore(path=None)
    await store.sparql_update(f"""{_PREFIXES}
INSERT DATA {{
    GRAPH <{KG}> {{
        <{ONT_IRI}#Person>     a owl:Class ; rdfs:label "Person" .
        <{ONT_IRI}#Employee>   a owl:Class ; rdfs:label "Employee" .
        <{ONT_IRI}#Alice>      a owl:NamedIndividual ; rdfs:label "Alice" .
        <{ONT_IRI}#worksFor>   a owl:ObjectProperty ; rdfs:label "worksFor" .
        <{ONT_IRI}#age>        a owl:DatatypeProperty ; rdfs:label "age" .
    }}
}}""")
    return store


async def test_search_entities_returns_empty_without_store():
    result = await search_entities(ONT_IRI, "Person")
    assert result == []


async def test_search_entities_concepts_by_label(store_with_data):
    result = await search_entities(ONT_IRI, "Person", kind="concept", store=store_with_data)
    iris = [r["iri"] for r in result]
    assert f"{ONT_IRI}#Person" in iris
    assert all(r["kind"] == "concept" for r in result)


async def test_search_entities_individual_by_label(store_with_data):
    result = await search_entities(ONT_IRI, "Alice", kind="individual", store=store_with_data)
    iris = [r["iri"] for r in result]
    assert f"{ONT_IRI}#Alice" in iris
    assert all(r["kind"] == "individual" for r in result)


async def test_search_entities_all_kinds(store_with_data):
    result = await search_entities(ONT_IRI, "", kind="all", store=store_with_data)
    kinds = {r["kind"] for r in result}
    assert "concept" in kinds
    assert "individual" in kinds


async def test_search_entities_empty_result(store_with_data):
    result = await search_entities(ONT_IRI, "NONEXISTENT_XYZ_123", store=store_with_data)
    assert result == []


async def test_search_relations_returns_empty_without_store():
    result = await search_relations(ONT_IRI, "has")
    assert result == []


async def test_search_relations_by_label(store_with_data):
    result = await search_relations(ONT_IRI, "worksFor", store=store_with_data)
    iris = [r["iri"] for r in result]
    assert f"{ONT_IRI}#worksFor" in iris


async def test_search_relations_all(store_with_data):
    result = await search_relations(ONT_IRI, "", store=store_with_data)
    kinds = {r["kind"] for r in result}
    assert "object" in kinds
    assert "data" in kinds


async def test_vector_search_fallback_to_keyword(store_with_data):
    result = await vector_search(ONT_IRI, "Person", store=store_with_data)
    iris = [r["iri"] for r in result]
    assert f"{ONT_IRI}#Person" in iris
