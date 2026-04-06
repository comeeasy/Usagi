"""
Tests for ReasonerService SPARQL-based violation detection.

owlready2 / HermiT JVM은 테스트 환경에 없으므로,
_detect_cardinality_violations / _detect_domain_range_violations 만 검증한다.
"""
from __future__ import annotations

import pytest
from services.ontology_store import OntologyStore
from services.reasoner_service import ReasonerService

BASE = "https://test-reasoner.example.org"
KG = f"{BASE}/kg"

_P = """
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
"""


@pytest.fixture
async def store_svc():
    """인메모리 OntologyStore + ReasonerService 쌍."""
    store = OntologyStore(path=None)
    svc = ReasonerService(store)
    return store, svc


# ── CardinalityViolation ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cardinality_no_violation(store_svc):
    """maxCardinality=2, 값 2개 → 위반 없음."""
    store, svc = store_svc
    await store.sparql_update(f"""{_P}
INSERT DATA {{
    GRAPH <{KG}> {{
        <{BASE}#Project>  a owl:Class .
        <{BASE}#hasMember> a owl:ObjectProperty .

        _:r1 a owl:Restriction ;
            owl:onProperty <{BASE}#hasMember> ;
            owl:maxCardinality 2 .
        <{BASE}#Project> rdfs:subClassOf _:r1 .

        <{BASE}#p1> a <{BASE}#Project> ;
            <{BASE}#hasMember> <{BASE}#alice> ;
            <{BASE}#hasMember> <{BASE}#bob> .
    }}
}}""")
    violations = await svc._detect_cardinality_violations(KG)
    assert violations == []


@pytest.mark.asyncio
async def test_max_cardinality_violation(store_svc):
    """maxCardinality=1 인데 값 2개 → CardinalityViolation."""
    store, svc = store_svc
    await store.sparql_update(f"""{_P}
INSERT DATA {{
    GRAPH <{KG}> {{
        <{BASE}#Department> a owl:Class .
        <{BASE}#manages> a owl:ObjectProperty .

        _:r1 a owl:Restriction ;
            owl:onProperty <{BASE}#manages> ;
            owl:maxCardinality 1 .
        <{BASE}#Department> rdfs:subClassOf _:r1 .

        <{BASE}#dept1> a <{BASE}#Department> ;
            <{BASE}#manages> <{BASE}#emp1> ;
            <{BASE}#manages> <{BASE}#emp2> .
    }}
}}""")
    violations = await svc._detect_cardinality_violations(KG)
    assert len(violations) == 1
    v = violations[0]
    assert v.type == "CardinalityViolation"
    assert v.subject_iri == f"{BASE}#dept1"
    assert "maxCardinality=1" in v.description


@pytest.mark.asyncio
async def test_exact_cardinality_violation_too_many(store_svc):
    """exactCardinality=1 인데 값 2개 → CardinalityViolation."""
    store, svc = store_svc
    await store.sparql_update(f"""{_P}
INSERT DATA {{
    GRAPH <{KG}> {{
        <{BASE}#Task> a owl:Class .
        <{BASE}#assignedTo> a owl:ObjectProperty .

        _:r1 a owl:Restriction ;
            owl:onProperty <{BASE}#assignedTo> ;
            owl:exactCardinality 1 .
        <{BASE}#Task> rdfs:subClassOf _:r1 .

        <{BASE}#task1> a <{BASE}#Task> ;
            <{BASE}#assignedTo> <{BASE}#alice> ;
            <{BASE}#assignedTo> <{BASE}#bob> .
    }}
}}""")
    violations = await svc._detect_cardinality_violations(KG)
    assert len(violations) == 1
    assert violations[0].type == "CardinalityViolation"
    assert "exactCardinality=1" in violations[0].description


@pytest.mark.asyncio
async def test_exact_cardinality_no_violation(store_svc):
    """exactCardinality=1 이고 값 정확히 1개 → 위반 없음."""
    store, svc = store_svc
    await store.sparql_update(f"""{_P}
INSERT DATA {{
    GRAPH <{KG}> {{
        <{BASE}#Task> a owl:Class .
        <{BASE}#assignedTo> a owl:ObjectProperty .

        _:r1 a owl:Restriction ;
            owl:onProperty <{BASE}#assignedTo> ;
            owl:exactCardinality 1 .
        <{BASE}#Task> rdfs:subClassOf _:r1 .

        <{BASE}#task2> a <{BASE}#Task> ;
            <{BASE}#assignedTo> <{BASE}#alice> .
    }}
}}""")
    violations = await svc._detect_cardinality_violations(KG)
    assert violations == []


@pytest.mark.asyncio
async def test_cardinality_multiple_individuals(store_svc):
    """같은 클래스 두 개체 중 하나만 위반 → 1건만 감지."""
    store, svc = store_svc
    await store.sparql_update(f"""{_P}
INSERT DATA {{
    GRAPH <{KG}> {{
        <{BASE}#Slot> a owl:Class .
        <{BASE}#hasItem> a owl:ObjectProperty .

        _:r1 a owl:Restriction ;
            owl:onProperty <{BASE}#hasItem> ;
            owl:maxCardinality 1 .
        <{BASE}#Slot> rdfs:subClassOf _:r1 .

        <{BASE}#slotA> a <{BASE}#Slot> ;
            <{BASE}#hasItem> <{BASE}#item1> .

        <{BASE}#slotB> a <{BASE}#Slot> ;
            <{BASE}#hasItem> <{BASE}#item2> ;
            <{BASE}#hasItem> <{BASE}#item3> .
    }}
}}""")
    violations = await svc._detect_cardinality_violations(KG)
    iris = [v.subject_iri for v in violations]
    assert f"{BASE}#slotB" in iris
    assert f"{BASE}#slotA" not in iris


# ── DomainRangeViolation ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_domain_range_no_violation(store_svc):
    """올바른 domain/range → 위반 없음."""
    store, svc = store_svc
    await store.sparql_update(f"""{_P}
INSERT DATA {{
    GRAPH <{KG}> {{
        <{BASE}#Person>     a owl:Class .
        <{BASE}#Animal>     a owl:Class .
        <{BASE}#hasPet>     a owl:ObjectProperty ;
            rdfs:domain <{BASE}#Person> ;
            rdfs:range  <{BASE}#Animal> .

        <{BASE}#alice> a <{BASE}#Person> .
        <{BASE}#fluffy> a <{BASE}#Animal> .
        <{BASE}#alice> <{BASE}#hasPet> <{BASE}#fluffy> .
    }}
}}""")
    violations = await svc._detect_domain_range_violations(KG)
    assert violations == []


@pytest.mark.asyncio
async def test_domain_violation(store_svc):
    """domain=Person 인데 Animal이 프로퍼티 사용 → DomainRangeViolation."""
    store, svc = store_svc
    await store.sparql_update(f"""{_P}
INSERT DATA {{
    GRAPH <{KG}> {{
        <{BASE}#Person> a owl:Class .
        <{BASE}#Animal> a owl:Class .
        <{BASE}#drives>  a owl:ObjectProperty ;
            rdfs:domain <{BASE}#Person> .

        <{BASE}#cat> a <{BASE}#Animal> .
        <{BASE}#car> a owl:Thing .
        <{BASE}#cat> <{BASE}#drives> <{BASE}#car> .
    }}
}}""")
    violations = await svc._detect_domain_range_violations(KG)
    assert len(violations) >= 1
    v = violations[0]
    assert v.type == "DomainRangeViolation"
    assert v.subject_iri == f"{BASE}#cat"
    assert "domain" in v.description


@pytest.mark.asyncio
async def test_range_violation(store_svc):
    """range=Animal 인데 Person을 목적어로 사용 → DomainRangeViolation."""
    store, svc = store_svc
    await store.sparql_update(f"""{_P}
INSERT DATA {{
    GRAPH <{KG}> {{
        <{BASE}#Person> a owl:Class .
        <{BASE}#Animal> a owl:Class .
        <{BASE}#hasPet> a owl:ObjectProperty ;
            rdfs:range <{BASE}#Animal> .

        <{BASE}#alice> a <{BASE}#Person> .
        <{BASE}#bob>   a <{BASE}#Person> .
        <{BASE}#alice> <{BASE}#hasPet> <{BASE}#bob> .
    }}
}}""")
    violations = await svc._detect_domain_range_violations(KG)
    assert len(violations) >= 1
    v = violations[0]
    assert v.type == "DomainRangeViolation"
    assert "range" in v.description


@pytest.mark.asyncio
async def test_domain_violation_subclass_ok(store_svc):
    """domain=Person, Employee rdfs:subClassOf Person → 위반 없음."""
    store, svc = store_svc
    await store.sparql_update(f"""{_P}
INSERT DATA {{
    GRAPH <{KG}> {{
        <{BASE}#Person>   a owl:Class .
        <{BASE}#Employee> a owl:Class ;
            rdfs:subClassOf <{BASE}#Person> .
        <{BASE}#works>    a owl:ObjectProperty ;
            rdfs:domain <{BASE}#Person> .

        <{BASE}#emp1> a <{BASE}#Employee> .
        <{BASE}#emp1> <{BASE}#works> <{BASE}#companyX> .
    }}
}}""")
    violations = await svc._detect_domain_range_violations(KG)
    assert violations == []
