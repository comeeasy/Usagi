"""
Tests for OntologyStore service — 실행 중인 Fuseki 인스턴스 필요.

실행 방법:
    pytest -m integration  (Fuseki가 localhost:3030 에서 실행 중일 때)

기본 pytest 실행 시에는 스킵된다.
"""
import pytest
from rdflib import URIRef, Literal
from rdflib.namespace import XSD

from services.ontology_store import OntologyStore, Triple


pytestmark = pytest.mark.integration

FUSEKI_URL = "http://localhost:3030"
DATASET = "ontology"

GRAPH = "https://example.org/test/tbox"
ONT = "https://example.org/test"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
OWL_CLASS = "http://www.w3.org/2002/07/owl#Class"
OWL_NAMED_IND = "http://www.w3.org/2002/07/owl#NamedIndividual"
OWL_OBJ_PROP = "http://www.w3.org/2002/07/owl#ObjectProperty"


@pytest.fixture
async def store():
    s = OntologyStore(FUSEKI_URL, DATASET)
    yield s
    await s.close()


def test_store_init(store):
    """OntologyStore 초기화 성공."""
    assert store is not None
    assert store._query_url == f"{FUSEKI_URL}/{DATASET}/sparql"


async def test_insert_and_select_triples(store):
    """insert_triples → sparql_select로 읽기."""
    triples = [
        Triple(
            subject=URIRef(f"{ONT}#Alice"),
            predicate=URIRef(RDF_TYPE),
            object_=URIRef(OWL_NAMED_IND),
        )
    ]
    await store.insert_triples(GRAPH, triples)
    rows = await store.sparql_select(f"""
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT ?s WHERE {{ GRAPH <{GRAPH}> {{ ?s rdf:type owl:NamedIndividual }} }}
    """)
    assert any(r["s"]["value"] == f"{ONT}#Alice" for r in rows)
    await store.delete_graph(GRAPH)


async def test_sparql_select_returns_dict_types(store):
    """URIRef → type=uri, Literal → type=literal 변환 확인."""
    await store.insert_triples(GRAPH, [
        Triple(
            subject=URIRef(f"{ONT}#Bob"),
            predicate=URIRef(RDFS_LABEL),
            object_=Literal("Bob Smith"),
        )
    ])
    rows = await store.sparql_select(f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?s ?label WHERE {{ GRAPH <{GRAPH}> {{ ?s rdfs:label ?label }} }}
    """)
    assert rows[0]["s"]["type"] == "uri"
    assert rows[0]["label"]["type"] == "literal"
    assert rows[0]["label"]["value"] == "Bob Smith"
    await store.delete_graph(GRAPH)


async def test_sparql_update_insert(store):
    """SPARQL INSERT DATA → 트리플 추가 확인."""
    await store.sparql_update(f"""
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        INSERT DATA {{ GRAPH <{GRAPH}> {{ <{ONT}#Cat> a owl:Class }} }}
    """)
    rows = await store.sparql_select(f"""
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        SELECT ?c WHERE {{ GRAPH <{GRAPH}> {{ ?c a owl:Class }} }}
    """)
    assert any(r["c"]["value"] == f"{ONT}#Cat" for r in rows)
    await store.delete_graph(GRAPH)


async def test_delete_graph(store):
    """Named Graph 삭제 → 해당 그래프 트리플 없어짐."""
    await store.insert_triples(GRAPH, [
        Triple(subject=URIRef(f"{ONT}#X"), predicate=URIRef(RDF_TYPE), object_=URIRef(OWL_CLASS))
    ])
    await store.delete_graph(GRAPH)
    rows = await store.sparql_select(f"SELECT ?s WHERE {{ GRAPH <{GRAPH}> {{ ?s ?p ?o }} }}")
    assert rows == []


async def test_delete_graph_idempotent(store):
    """존재하지 않는 그래프 삭제도 오류 없이 처리."""
    await store.delete_graph("https://example.org/nonexistent/graph")


async def test_get_ontology_stats(store):
    """concepts/individuals/properties 카운트 정확성."""
    tbox = f"{ONT}/tbox"
    await store.sparql_update(f"""
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        INSERT DATA {{
            GRAPH <{tbox}> {{
                <{ONT}#Cls1> a owl:Class .
                <{ONT}#Cls2> a owl:Class .
                <{ONT}#ind1> a owl:NamedIndividual .
                <{ONT}#hasProp> a owl:ObjectProperty .
                <{ONT}#ageProp> a owl:DatatypeProperty .
            }}
        }}
    """)
    stats = await store.get_ontology_stats(tbox)
    assert stats["concepts"] == 2
    assert stats["individuals"] == 1
    assert stats["object_properties"] == 1
    assert stats["data_properties"] == 1
    await store.delete_graph(tbox)


async def test_sparql_ask_true(store):
    """ASK → True."""
    await store.insert_triples(GRAPH, [
        Triple(subject=URIRef(f"{ONT}#Whale"), predicate=URIRef(RDF_TYPE), object_=URIRef(OWL_CLASS))
    ])
    result = await store.sparql_ask(f"""
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        ASK {{ GRAPH <{GRAPH}> {{ <{ONT}#Whale> a owl:Class }} }}
    """)
    assert result is True
    await store.delete_graph(GRAPH)


async def test_sparql_ask_false(store):
    """ASK → False (없는 트리플)."""
    result = await store.sparql_ask(f"""
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        ASK {{ GRAPH <{GRAPH}> {{ <{ONT}#NONEXISTENT> a owl:Class }} }}
    """)
    assert result is False
