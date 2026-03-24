"""
Tests for OntologyStore service — pyoxigraph 인메모리 인스턴스로 SPARQL 동작 직접 검증.
"""
import pytest
from pyoxigraph import NamedNode, Literal as RDFLiteral

from services.ontology_store import OntologyStore, Triple


GRAPH = "https://example.org/test/tbox"
ONT = "https://example.org/test"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
OWL_CLASS = "http://www.w3.org/2002/07/owl#Class"
OWL_NAMED_IND = "http://www.w3.org/2002/07/owl#NamedIndividual"
OWL_OBJ_PROP = "http://www.w3.org/2002/07/owl#ObjectProperty"


@pytest.fixture
def store():
    return OntologyStore(path=None)


def test_store_init_in_memory(store):
    """OntologyStore(path=None) 초기화 성공."""
    assert store is not None
    assert store._store is not None


async def test_insert_and_select_triples(store):
    """insert_triples → sparql_select로 읽기."""
    triples = [
        Triple(
            subject=NamedNode(f"{ONT}#Alice"),
            predicate=NamedNode(RDF_TYPE),
            object_=NamedNode(OWL_NAMED_IND),
        )
    ]
    await store.insert_triples(GRAPH, triples)
    rows = await store.sparql_select(f"""
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT ?s WHERE {{ GRAPH <{GRAPH}> {{ ?s rdf:type owl:NamedIndividual }} }}
    """)
    assert len(rows) == 1
    assert rows[0]["s"]["value"] == f"{ONT}#Alice"


async def test_sparql_select_returns_dict_types(store):
    """NamedNode → type=uri, RDFLiteral → type=literal 변환 확인."""
    await store.insert_triples(GRAPH, [
        Triple(
            subject=NamedNode(f"{ONT}#Bob"),
            predicate=NamedNode(RDFS_LABEL),
            object_=RDFLiteral("Bob Smith"),
        )
    ])
    rows = await store.sparql_select(f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?s ?label WHERE {{ GRAPH <{GRAPH}> {{ ?s rdfs:label ?label }} }}
    """)
    assert rows[0]["s"]["type"] == "uri"
    assert rows[0]["label"]["type"] == "literal"
    assert rows[0]["label"]["value"] == "Bob Smith"


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


async def test_sparql_update_delete(store):
    """SPARQL DELETE DATA → 트리플 제거 확인."""
    await store.sparql_update(f"""
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        INSERT DATA {{ GRAPH <{GRAPH}> {{ <{ONT}#Dog> a owl:Class }} }}
    """)
    await store.sparql_update(f"""
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        DELETE DATA {{ GRAPH <{GRAPH}> {{ <{ONT}#Dog> a owl:Class }} }}
    """)
    rows = await store.sparql_select(f"""
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        SELECT ?c WHERE {{ GRAPH <{GRAPH}> {{ <{ONT}#Dog> a owl:Class }} }}
    """)
    assert rows == []


async def test_delete_graph(store):
    """Named Graph 삭제 → 해당 그래프 트리플 없어짐."""
    await store.insert_triples(GRAPH, [
        Triple(
            subject=NamedNode(f"{ONT}#X"),
            predicate=NamedNode(RDF_TYPE),
            object_=NamedNode(OWL_CLASS),
        )
    ])
    await store.delete_graph(GRAPH)
    rows = await store.sparql_select(f"SELECT ?s WHERE {{ GRAPH <{GRAPH}> {{ ?s ?p ?o }} }}")
    assert rows == []


async def test_delete_graph_idempotent(store):
    """존재하지 않는 그래프 삭제도 오류 없이 처리."""
    await store.delete_graph("https://example.org/nonexistent/graph")


async def test_export_turtle(store):
    """export_turtle → 유효한 Turtle 문자열 반환."""
    await store.sparql_update(f"""
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        INSERT DATA {{ GRAPH <{GRAPH}> {{ <{ONT}#Elephant> a owl:Class }} }}
    """)
    turtle = await store.export_turtle(GRAPH)
    assert isinstance(turtle, str)
    assert len(turtle) > 0
    # Turtle에 triple 내용이 포함됨
    assert "Elephant" in turtle or "owl" in turtle.lower()


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


async def test_sparql_ask_true(store):
    """ASK → True."""
    await store.insert_triples(GRAPH, [
        Triple(
            subject=NamedNode(f"{ONT}#Whale"),
            predicate=NamedNode(RDF_TYPE),
            object_=NamedNode(OWL_CLASS),
        )
    ])
    result = await store.sparql_ask(f"""
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        ASK {{ GRAPH <{GRAPH}> {{ <{ONT}#Whale> a owl:Class }} }}
    """)
    assert result is True


async def test_sparql_ask_false(store):
    """ASK → False (없는 트리플)."""
    result = await store.sparql_ask(f"""
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        ASK {{ GRAPH <{GRAPH}> {{ <{ONT}#NONEXISTENT> a owl:Class }} }}
    """)
    assert result is False


async def test_sparql_syntax_error_raises(store):
    """잘못된 SPARQL 쿼리 → 예외 발생."""
    with pytest.raises(Exception):
        await store.sparql_select("THIS IS NOT VALID SPARQL !!!!")
