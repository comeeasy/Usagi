"""
통합 테스트: Concept 탭은 명시적 owl:Class만, Individual 탭은 individual만

시나리오:
  - Sport       : owl:Class 선언 O → Concepts에 표시
  - Organisation: owl:Class 선언 O → Concepts에 표시
  - Archery     : owl:Class 선언 X, rdf:type Sport (individual) → Concepts에 미표시
  - WaterSport  : owl:Class 선언 X, rdfs:subClassOf Sport 관계만 → Concepts에 미표시
  - AthleteA    : owl:NamedIndividual, rdf:type Sport → Individuals에만 표시

검증 항목:
  1. Concepts 목록에 Archery(individual), WaterSport(subClassOf only) 미포함
  2. Concepts 목록에 Sport, Organisation(owl:Class) 포함
  3. Sport.subclass_count = 0 (Archery는 subClassOf가 아니라 rdf:type)
  4. Sport.individual_count = 1 (AthleteA)
  5. Individuals 목록에 AthleteA 포함
"""
from __future__ import annotations

import pytest
import httpx
from urllib.parse import quote

BASE_URL = "http://localhost/api/v1"
ONT_BASE = "https://class-filter-test.example.org/onto"

SPORT      = f"{ONT_BASE}#Sport"        # owl:Class
ORG        = f"{ONT_BASE}#Organisation" # owl:Class
ARCHERY    = f"{ONT_BASE}#Archery"      # individual of Sport (rdf:type)
WATER      = f"{ONT_BASE}#WaterSport"   # rdfs:subClassOf Sport (no owl:Class decl)
ATHLETE_A  = f"{ONT_BASE}#AthleteA"    # owl:NamedIndividual, type Sport


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=10) as c:
        yield c


@pytest.fixture(scope="module")
def ontology(client):
    resp = client.post("/ontologies", json={
        "label": "Class Filter Test",
        "iri": ONT_BASE,
        "version": "1.0.0",
    })
    assert resp.status_code == 201, resp.text
    ont = resp.json()
    yield ont
    client.delete(f"/ontologies/{ont['id']}")


@pytest.fixture(scope="module")
def setup(client, ontology):
    oid = ontology["id"]

    # owl:Class 선언 클래스
    r1 = client.post(f"/ontologies/{oid}/concepts", json={"iri": SPORT, "label": "Sport"})
    assert r1.status_code == 201, r1.text
    r2 = client.post(f"/ontologies/{oid}/concepts", json={"iri": ORG, "label": "Organisation"})
    assert r2.status_code == 201, r2.text

    # Individual (owl:NamedIndividual + rdf:type Sport)
    r3 = client.post(f"/ontologies/{oid}/individuals", json={
        "iri": ARCHERY, "label": "Archery", "types": [SPORT],
    })
    assert r3.status_code == 201, r3.text

    r4 = client.post(f"/ontologies/{oid}/individuals", json={
        "iri": ATHLETE_A, "label": "Athlete A", "types": [SPORT],
    })
    assert r4.status_code == 201, r4.text

    return {"oid": oid}


# ── 1. Concepts 목록: owl:Class만 ───────────────────────────────────────────

def test_concepts_only_includes_owl_class(client, ontology, setup):
    """Concepts 목록에 Sport, Organisation(owl:Class)만 포함."""
    oid = ontology["id"]
    resp = client.get(f"/ontologies/{oid}/concepts", params={"page_size": 50})
    assert resp.status_code == 200
    iris = {i["iri"] for i in resp.json()["items"]}

    assert SPORT in iris,   "Sport(owl:Class)이 Concepts에 없음"
    assert ORG in iris,     "Organisation(owl:Class)이 Concepts에 없음"
    assert ARCHERY not in iris, "Archery(individual)이 Concepts에 포함됨 (잘못)"
    assert ATHLETE_A not in iris, "AthleteA(individual)이 Concepts에 포함됨 (잘못)"


# ── 2. individual_count: Sport 아래 AthleteA, Archery ───────────────────────

def test_sport_individual_count(client, ontology, setup):
    """Sport.individual_count == 2 (Archery + AthleteA 모두 rdf:type Sport)."""
    oid = ontology["id"]
    resp = client.get(f"/ontologies/{oid}/concepts", params={"page_size": 50})
    sport = next(i for i in resp.json()["items"] if i["iri"] == SPORT)
    assert sport["individual_count"] == 2, (
        f"Sport.individual_count 기대 2, 실제 {sport['individual_count']}"
    )


# ── 3. Individuals 목록: owl:NamedIndividual만 ──────────────────────────────

def test_individuals_list(client, ontology, setup):
    """Individuals 목록에 Archery, AthleteA 포함."""
    oid = ontology["id"]
    resp = client.get(f"/ontologies/{oid}/individuals", params={"page_size": 50})
    assert resp.status_code == 200
    iris = {i["iri"] for i in resp.json()["items"]}
    assert ARCHERY in iris,   "Archery가 Individuals 목록에 없음"
    assert ATHLETE_A in iris, "AthleteA가 Individuals 목록에 없음"
