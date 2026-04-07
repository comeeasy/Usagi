"""
통합 테스트: Concept 트리 루트 필터 + 서브클래스 조회

시나리오: 스포츠 온톨로지 계층
  Sport (루트)
    ├── Archery (Sport 서브클래스)
    └── Alpine Skiing (Sport 서브클래스)
  Organisation (루트, Sport와 별개)

검증 항목:
  1. root=True → Sport, Organisation만 반환 (Archery, Alpine Skiing 제외)
  2. /concepts/{sport}/subclasses → Archery, Alpine Skiing 반환
  3. subclass_count: Sport=2, Organisation=0, Archery=0
  4. individual_count: Sport에 Individual 추가 후 확인

실행:
  pytest tests/test_concept_tree.py -v  (Fuseki + Backend 실행 중 필요)
"""
from __future__ import annotations

import pytest
import httpx
from urllib.parse import quote

BASE_URL = "http://localhost/api/v1"
ONT_BASE = "https://sport.example.org/onto"
SPORT     = f"{ONT_BASE}#Sport"
ARCHERY   = f"{ONT_BASE}#Archery"
ALPINE    = f"{ONT_BASE}#AlpineSkiing"
ORG       = f"{ONT_BASE}#Organisation"
ATHLETE   = f"{ONT_BASE}#Athlete"   # Sport의 Individual


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=10) as c:
        yield c


@pytest.fixture(scope="module")
def ontology(client):
    """테스트용 온톨로지 생성, 모듈 종료 시 삭제."""
    resp = client.post("/ontologies", json={
        "label": "Sport Test Ontology",
        "iri": ONT_BASE,
        "description": "concept tree 테스트용",
        "version": "1.0.0",
    })
    assert resp.status_code == 201, resp.text
    ont = resp.json()
    yield ont
    client.delete(f"/ontologies/{ont['id']}")


@pytest.fixture(scope="module")
def hierarchy(client, ontology):
    """Sport → Archery, AlpineSkiing / Organisation (별도 루트) 계층 구성."""
    oid = ontology["id"]

    # 루트 클래스
    r1 = client.post(f"/ontologies/{oid}/concepts", json={"iri": SPORT, "label": "Sport"})
    assert r1.status_code == 201, r1.text
    r2 = client.post(f"/ontologies/{oid}/concepts", json={"iri": ORG, "label": "Organisation"})
    assert r2.status_code == 201, r2.text

    # 서브클래스
    r3 = client.post(f"/ontologies/{oid}/concepts", json={
        "iri": ARCHERY, "label": "Archery", "super_classes": [SPORT],
    })
    assert r3.status_code == 201, r3.text
    r4 = client.post(f"/ontologies/{oid}/concepts", json={
        "iri": ALPINE, "label": "Alpine Skiing", "super_classes": [SPORT],
    })
    assert r4.status_code == 201, r4.text

    # Individual: Athlete (Sport 타입)
    r5 = client.post(f"/ontologies/{oid}/individuals", json={
        "iri": ATHLETE, "label": "Athlete Example", "types": [SPORT],
    })
    assert r5.status_code == 201, r5.text

    return {"oid": oid}


# ── 1. root=True: 루트 클래스만 반환 ──────────────────────────────────────────

def test_root_only_returns_top_level_classes(client, ontology, hierarchy):
    """root=True → Sport, Organisation만 포함. Archery, Alpine Skiing 없어야 함."""
    oid = ontology["id"]
    resp = client.get(f"/ontologies/{oid}/concepts", params={"root": "true", "page_size": 50})
    assert resp.status_code == 200, resp.text
    data = resp.json()

    iris = {item["iri"] for item in data["items"]}
    assert SPORT in iris,      f"Sport이 루트 목록에 없음: {iris}"
    assert ORG in iris,        f"Organisation이 루트 목록에 없음: {iris}"
    assert ARCHERY not in iris, f"Archery가 루트 목록에 포함됨 (잘못): {iris}"
    assert ALPINE not in iris,  f"Alpine Skiing이 루트 목록에 포함됨 (잘못): {iris}"


# ── 2. subclass_count 검증 ────────────────────────────────────────────────────

def test_root_sport_has_correct_subclass_count(client, ontology, hierarchy):
    """root=True 결과에서 Sport.subclass_count == 2."""
    oid = ontology["id"]
    resp = client.get(f"/ontologies/{oid}/concepts", params={"root": "true", "page_size": 50})
    data = resp.json()

    sport_item = next((i for i in data["items"] if i["iri"] == SPORT), None)
    assert sport_item is not None, "Sport이 루트 목록에 없음"
    assert sport_item["subclass_count"] == 2, (
        f"Sport.subclass_count 기대 2, 실제 {sport_item['subclass_count']}"
    )

def test_root_organisation_has_zero_subclass_count(client, ontology, hierarchy):
    """Organisation.subclass_count == 0 (서브클래스 없음)."""
    oid = ontology["id"]
    resp = client.get(f"/ontologies/{oid}/concepts", params={"root": "true", "page_size": 50})
    data = resp.json()

    org_item = next((i for i in data["items"] if i["iri"] == ORG), None)
    assert org_item is not None
    assert org_item["subclass_count"] == 0


# ── 3. individual_count 검증 ──────────────────────────────────────────────────

def test_sport_individual_count(client, ontology, hierarchy):
    """Sport.individual_count == 1 (Athlete가 Sport 타입)."""
    oid = ontology["id"]
    resp = client.get(f"/ontologies/{oid}/concepts", params={"root": "true", "page_size": 50})
    data = resp.json()

    sport_item = next((i for i in data["items"] if i["iri"] == SPORT), None)
    assert sport_item is not None
    assert sport_item["individual_count"] == 1, (
        f"Sport.individual_count 기대 1, 실제 {sport_item['individual_count']}"
    )


# ── 4. /subclasses 엔드포인트 ─────────────────────────────────────────────────

def test_subclasses_of_sport(client, ontology, hierarchy):
    """GET /concepts/{sport}/subclasses → Archery, Alpine Skiing 반환."""
    oid = ontology["id"]
    encoded = quote(SPORT, safe="")
    resp = client.get(f"/ontologies/{oid}/concepts/{encoded}/subclasses")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    iris = {item["iri"] for item in data["items"]}
    assert ARCHERY in iris, f"Archery가 subclasses에 없음: {iris}"
    assert ALPINE in iris,  f"Alpine Skiing이 subclasses에 없음: {iris}"
    assert data["total"] == 2, f"total 기대 2, 실제 {data['total']}"

def test_subclasses_of_leaf_class(client, ontology, hierarchy):
    """Archery(leaf)의 subclasses → 빈 목록."""
    oid = ontology["id"]
    encoded = quote(ARCHERY, safe="")
    resp = client.get(f"/ontologies/{oid}/concepts/{encoded}/subclasses")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


# ── 5. owl:Thing 명시 선언 케이스 ─────────────────────────────────────────────

OWL_THING = "http://www.w3.org/2002/07/owl#Thing"
WATER_SPORT = f"{ONT_BASE}#WaterSport"  # owl:Thing 자식, Sport와 별개 루트

@pytest.fixture(scope="module")
def hierarchy_with_owl_thing(client, ontology):
    """owl:Thing을 명시 부모로 갖는 클래스 추가 (DBpedia 스타일 임포트 시뮬레이션)."""
    oid = ontology["id"]
    resp = client.post(f"/ontologies/{oid}/concepts", json={
        "iri": WATER_SPORT,
        "label": "Water Sport",
        "super_classes": [OWL_THING],  # 실제 OWL 파일에서 자주 등장
    })
    assert resp.status_code == 201, resp.text
    return {"oid": oid}


def test_class_with_only_owl_thing_parent_is_root(client, ontology, hierarchy, hierarchy_with_owl_thing):
    """owl:Thing만 부모인 클래스 → 루트로 간주해야 함."""
    oid = ontology["id"]
    resp = client.get(f"/ontologies/{oid}/concepts", params={"root": "true", "page_size": 50})
    data = resp.json()
    iris = {item["iri"] for item in data["items"]}
    assert WATER_SPORT in iris, (
        f"owl:Thing만 부모인 WaterSport가 루트에 없음. 실제 루트 목록: {iris}"
    )
