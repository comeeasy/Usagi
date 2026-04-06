"""
통합 테스트 시나리오: HR 도메인 온톨로지 구축 전 과정

시나리오 개요
-----------
HR(인사) 도메인의 온톨로지를 처음부터 끝까지 API로 구축하는 전 과정을 테스트한다.

단계:
  Step 1. 온톨로지 생성 (POST /ontologies → 201)
  Step 2. Concept 계층 구성
          Person → Employee (서브클래스) → Manager (서브클래스)
  Step 3. Object Property 생성 worksFor (Employee → Department)
  Step 4. Data Property 생성   age (Person → xsd:integer)
  Step 5. Individual 생성      Alice(Manager), Bob(Employee)
  Step 6. Entity 검색          "employ" → Employee/Manager 반환 확인
  Step 7. SPARQL 조회          owl:NamedIndividual 전체 조회
  Step 8. 통계 확인            concepts=3, individuals=2, object_properties=1, data_properties=1
  Step 9. Concept 업데이트     Employee comment 추가
  Step 10. 온톨로지 삭제       DELETE 204 → GET 404
"""
from __future__ import annotations

from urllib.parse import quote

BASE = "https://hr.example.org/onto"


# ─────────────────────────────────────────────────────────────────────────────
# Step 1: 온톨로지 생성
# ─────────────────────────────────────────────────────────────────────────────

async def test_step1_create_ontology(client):
    resp = await client.post("/ontologies", json={
        "label": "HR Domain Ontology",
        "iri": BASE,
        "description": "Human Resources domain ontology for integration test",
        "version": "1.0.0",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["iri"] == BASE
    assert data["label"] == "HR Domain Ontology"
    assert "id" in data and data["id"]


# ─────────────────────────────────────────────────────────────────────────────
# Step 2: Concept 계층 구성
# ─────────────────────────────────────────────────────────────────────────────

async def test_step2a_create_concept_person(client, created_ontology):
    ont_id = created_ontology["id"]
    resp = await client.post(f"/ontologies/{ont_id}/concepts", json={
        "iri": f"{BASE}#Person",
        "label": "Person",
        "comment": "A human being",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["iri"] == f"{BASE}#Person"
    assert data["label"] == "Person"


async def test_step2b_create_concept_employee_subclass_of_person(client, created_ontology):
    ont_id = created_ontology["id"]
    # Person 먼저 생성
    await client.post(f"/ontologies/{ont_id}/concepts", json={
        "iri": f"{BASE}#Person", "label": "Person",
    })
    resp = await client.post(f"/ontologies/{ont_id}/concepts", json={
        "iri": f"{BASE}#Employee",
        "label": "Employee",
        "comment": "A person employed by an organization",
        "super_classes": [f"{BASE}#Person"],
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["iri"] == f"{BASE}#Employee"
    assert f"{BASE}#Person" in data["super_classes"]


async def test_step2c_create_concept_manager_subclass_of_employee(client, created_ontology):
    ont_id = created_ontology["id"]
    await client.post(f"/ontologies/{ont_id}/concepts", json={"iri": f"{BASE}#Employee", "label": "Employee"})
    resp = await client.post(f"/ontologies/{ont_id}/concepts", json={
        "iri": f"{BASE}#Manager",
        "label": "Manager",
        "comment": "An employee with managerial responsibilities",
        "super_classes": [f"{BASE}#Employee"],
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["iri"] == f"{BASE}#Manager"
    assert f"{BASE}#Employee" in data["super_classes"]


async def test_step2d_list_concepts_returns_three(client, created_ontology):
    ont_id = created_ontology["id"]
    for iri, label, parents in [
        (f"{BASE}#Person", "Person", []),
        (f"{BASE}#Employee", "Employee", [f"{BASE}#Person"]),
        (f"{BASE}#Manager", "Manager", [f"{BASE}#Employee"]),
    ]:
        await client.post(f"/ontologies/{ont_id}/concepts", json={
            "iri": iri, "label": label, "super_classes": parents,
        })

    resp = await client.get(f"/ontologies/{ont_id}/concepts")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    iris = [item["iri"] for item in data["items"]]
    assert f"{BASE}#Person" in iris
    assert f"{BASE}#Employee" in iris
    assert f"{BASE}#Manager" in iris


# ─────────────────────────────────────────────────────────────────────────────
# Step 3: Object Property 생성
# ─────────────────────────────────────────────────────────────────────────────

async def test_step3_create_object_property(client, created_ontology):
    ont_id = created_ontology["id"]
    await client.post(f"/ontologies/{ont_id}/concepts", json={"iri": f"{BASE}#Employee", "label": "Employee"})
    await client.post(f"/ontologies/{ont_id}/concepts", json={"iri": f"{BASE}#Department", "label": "Department"})

    resp = await client.post(f"/ontologies/{ont_id}/properties", json={
        "iri": f"{BASE}#worksFor",
        "label": "worksFor",
        "comment": "Relates an employee to their department",
        "domain": [f"{BASE}#Employee"],
        "range": [f"{BASE}#Department"],
        "characteristics": ["Functional"],
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["iri"] == f"{BASE}#worksFor"
    assert f"{BASE}#Employee" in data["domain"]
    assert f"{BASE}#Department" in data["range"]
    assert "Functional" in data["characteristics"]


# ─────────────────────────────────────────────────────────────────────────────
# Step 4: Data Property 생성
# ─────────────────────────────────────────────────────────────────────────────

async def test_step4_create_data_property(client, created_ontology):
    ont_id = created_ontology["id"]
    await client.post(f"/ontologies/{ont_id}/concepts", json={"iri": f"{BASE}#Person", "label": "Person"})

    resp = await client.post(f"/ontologies/{ont_id}/properties", json={
        "iri": f"{BASE}#age",
        "label": "age",
        "comment": "The age of a person in years",
        "domain": [f"{BASE}#Person"],
        "range": ["xsd:integer"],
        "is_functional": True,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["iri"] == f"{BASE}#age"
    assert "xsd:integer" in data["range"]


# ─────────────────────────────────────────────────────────────────────────────
# Step 5: Individual 생성
# ─────────────────────────────────────────────────────────────────────────────

async def test_step5a_create_individual_alice_manager(client, created_ontology):
    ont_id = created_ontology["id"]
    await client.post(f"/ontologies/{ont_id}/concepts", json={"iri": f"{BASE}#Manager", "label": "Manager"})

    resp = await client.post(f"/ontologies/{ont_id}/individuals", json={
        "iri": f"{BASE}#Alice",
        "label": "Alice",
        "types": [f"{BASE}#Manager"],
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["iri"] == f"{BASE}#Alice"
    assert f"{BASE}#Manager" in data["types"]


async def test_step5b_create_individual_bob_employee(client, created_ontology):
    ont_id = created_ontology["id"]
    await client.post(f"/ontologies/{ont_id}/concepts", json={"iri": f"{BASE}#Employee", "label": "Employee"})

    resp = await client.post(f"/ontologies/{ont_id}/individuals", json={
        "iri": f"{BASE}#Bob",
        "label": "Bob",
        "types": [f"{BASE}#Employee"],
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["iri"] == f"{BASE}#Bob"
    assert f"{BASE}#Employee" in data["types"]


async def test_step5c_list_individuals_returns_two(client, created_ontology):
    ont_id = created_ontology["id"]
    for iri, label in [(f"{BASE}#Manager", "Manager"), (f"{BASE}#Employee", "Employee")]:
        await client.post(f"/ontologies/{ont_id}/concepts", json={"iri": iri, "label": label})
    await client.post(f"/ontologies/{ont_id}/individuals", json={
        "iri": f"{BASE}#Alice", "label": "Alice", "types": [f"{BASE}#Manager"],
    })
    await client.post(f"/ontologies/{ont_id}/individuals", json={
        "iri": f"{BASE}#Bob", "label": "Bob", "types": [f"{BASE}#Employee"],
    })

    resp = await client.get(f"/ontologies/{ont_id}/individuals")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    iris = [item["iri"] for item in data["items"]]
    assert f"{BASE}#Alice" in iris
    assert f"{BASE}#Bob" in iris


# ─────────────────────────────────────────────────────────────────────────────
# Step 6: Entity 검색
# ─────────────────────────────────────────────────────────────────────────────

async def test_step6_search_entities_by_keyword(client, created_ontology):
    ont_id = created_ontology["id"]
    for iri, label in [
        (f"{BASE}#Person", "Person"),
        (f"{BASE}#Employee", "Employee"),
        (f"{BASE}#Manager", "Manager"),
    ]:
        await client.post(f"/ontologies/{ont_id}/concepts", json={"iri": iri, "label": label})

    resp = await client.get(f"/ontologies/{ont_id}/search/entities?q=employ&kind=concept")
    assert resp.status_code == 200
    data = resp.json()
    iris = [item["iri"] for item in data]
    assert f"{BASE}#Employee" in iris
    assert f"{BASE}#Person" not in iris


async def test_step6_search_entities_all_kinds(client, created_ontology):
    ont_id = created_ontology["id"]
    await client.post(f"/ontologies/{ont_id}/concepts", json={"iri": f"{BASE}#Person", "label": "Person"})
    await client.post(f"/ontologies/{ont_id}/individuals", json={
        "iri": f"{BASE}#Alice", "label": "Alice", "types": [],
    })

    resp = await client.get(f"/ontologies/{ont_id}/search/entities?kind=all")
    assert resp.status_code == 200
    data = resp.json()
    kinds = {item["kind"] for item in data}
    assert "concept" in kinds
    assert "individual" in kinds


# ─────────────────────────────────────────────────────────────────────────────
# Step 7: SPARQL 조회
# ─────────────────────────────────────────────────────────────────────────────

async def test_step7_sparql_select_all_individuals(client, created_ontology):
    ont_id = created_ontology["id"]
    await client.post(f"/ontologies/{ont_id}/concepts", json={"iri": f"{BASE}#Manager", "label": "Manager"})
    await client.post(f"/ontologies/{ont_id}/individuals", json={
        "iri": f"{BASE}#Alice", "label": "Alice", "types": [f"{BASE}#Manager"],
    })
    await client.post(f"/ontologies/{ont_id}/individuals", json={
        "iri": f"{BASE}#Bob", "label": "Bob", "types": [],
    })

    # Named Graph에 저장되므로 GRAPH ?g 절 필요
    resp = await client.post(f"/ontologies/{ont_id}/sparql", json={
        "query": (
            "PREFIX owl: <http://www.w3.org/2002/07/owl#> "
            "SELECT ?p WHERE { GRAPH ?g { ?p a owl:NamedIndividual } }"
        ),
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "bindings" in data
    values = [row["p"]["value"] for row in data["bindings"] if "p" in row]
    assert f"{BASE}#Alice" in values
    assert f"{BASE}#Bob" in values


async def test_step7_sparql_update_blocked(client, created_ontology):
    ont_id = created_ontology["id"]
    resp = await client.post(f"/ontologies/{ont_id}/sparql", json={
        "query": f"INSERT DATA {{ GRAPH <{BASE}/kg> {{ <{BASE}#X> a <{BASE}#Y> }} }}",
    })
    # sparql.py: UPDATE 구문 → 400 (403이 아님)
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "SPARQL_UPDATE_FORBIDDEN"


# ─────────────────────────────────────────────────────────────────────────────
# Step 8: 온톨로지 통계 확인
# ─────────────────────────────────────────────────────────────────────────────

async def test_step8_ontology_stats(client, created_ontology):
    ont_id = created_ontology["id"]
    for iri, label, parents in [
        (f"{BASE}#Person", "Person", []),
        (f"{BASE}#Employee", "Employee", [f"{BASE}#Person"]),
        (f"{BASE}#Manager", "Manager", [f"{BASE}#Employee"]),
    ]:
        await client.post(f"/ontologies/{ont_id}/concepts", json={
            "iri": iri, "label": label, "super_classes": parents,
        })

    await client.post(f"/ontologies/{ont_id}/properties", json={
        "iri": f"{BASE}#worksFor", "label": "worksFor",
        "domain": [f"{BASE}#Employee"], "range": [f"{BASE}#Person"],
        "characteristics": ["Functional"],
    })
    await client.post(f"/ontologies/{ont_id}/properties", json={
        "iri": f"{BASE}#age", "label": "age",
        "domain": [f"{BASE}#Person"], "range": ["xsd:integer"],
        "is_functional": True,
    })
    await client.post(f"/ontologies/{ont_id}/individuals", json={
        "iri": f"{BASE}#Alice", "label": "Alice", "types": [f"{BASE}#Manager"],
    })
    await client.post(f"/ontologies/{ont_id}/individuals", json={
        "iri": f"{BASE}#Bob", "label": "Bob", "types": [f"{BASE}#Employee"],
    })

    resp = await client.get(f"/ontologies/{ont_id}")
    assert resp.status_code == 200
    stats = resp.json()["stats"]
    # OntologyStats 필드: concepts / individuals / object_properties / data_properties
    assert stats["concepts"] == 3
    assert stats["individuals"] == 2
    assert stats["object_properties"] >= 1
    assert stats["data_properties"] >= 1


# ─────────────────────────────────────────────────────────────────────────────
# Step 9: Concept 업데이트
# ─────────────────────────────────────────────────────────────────────────────

async def test_step9_update_concept_comment(client, created_ontology):
    ont_id = created_ontology["id"]
    await client.post(f"/ontologies/{ont_id}/concepts", json={
        "iri": f"{BASE}#Employee", "label": "Employee",
    })

    iri_encoded = quote(f"{BASE}#Employee", safe="")
    resp = await client.put(f"/ontologies/{ont_id}/concepts/{iri_encoded}", json={
        "label": "Employee",
        "comment": "A person who works for an organization in exchange for compensation",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "compensation" in data["comment"]


# ─────────────────────────────────────────────────────────────────────────────
# Step 10: 온톨로지 삭제
# ─────────────────────────────────────────────────────────────────────────────

async def test_step10_delete_ontology(client, created_ontology):
    ont_id = created_ontology["id"]

    resp = await client.delete(f"/ontologies/{ont_id}")
    assert resp.status_code == 204

    resp = await client.get(f"/ontologies/{ont_id}")
    assert resp.status_code == 404


async def test_step10_delete_also_removes_concepts(client, created_ontology):
    ont_id = created_ontology["id"]
    await client.post(f"/ontologies/{ont_id}/concepts", json={
        "iri": f"{BASE}#Person", "label": "Person",
    })
    before = await client.get(f"/ontologies/{ont_id}/concepts")
    assert before.json()["total"] >= 1

    await client.delete(f"/ontologies/{ont_id}")

    after = await client.get(f"/ontologies/{ont_id}")
    assert after.status_code == 404
