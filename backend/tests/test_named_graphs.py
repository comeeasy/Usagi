"""
tests/test_named_graphs.py — Named Graph per Import 분리 + Graph 선택 필터 테스트 (Part D)

D1: import/file 후 named graph IRI가 /imports/{filename} 패턴인지 검증
D2: graph_iris 파라미터로 선택된 그래프만 조회되는지 검증
"""
from __future__ import annotations

import io
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch


ONT_IRI = "https://test.example.org/ontology"


# ─────────────────────────────────────────────────────────────────
# D1: import_graph_iri 헬퍼 단위 테스트
# ─────────────────────────────────────────────────────────────────

class TestImportGraphIri:
    """services/ontology_graph.py — import_graph_iri(), manual_graph_iri() 함수 테스트."""

    def test_manual_graph_iri(self):
        from services.ontology_graph import manual_graph_iri
        result = manual_graph_iri(ONT_IRI)
        assert result == f"{ONT_IRI}/manual"

    def test_import_graph_iri_file(self):
        from services.ontology_graph import import_graph_iri
        result = import_graph_iri(ONT_IRI, "file", "my_ontology.ttl")
        assert result == f"{ONT_IRI}/imports/my_ontology.ttl"

    def test_import_graph_iri_url(self):
        from services.ontology_graph import import_graph_iri
        result = import_graph_iri(ONT_IRI, "url", "schema.org")
        assert result == f"{ONT_IRI}/imports/url/schema.org"

    def test_import_graph_iri_standard(self):
        from services.ontology_graph import import_graph_iri
        result = import_graph_iri(ONT_IRI, "standard", "foaf")
        assert result == f"{ONT_IRI}/imports/standard/foaf"

    def test_import_graph_iri_file_strips_path(self):
        """파일 경로에서 basename만 사용."""
        from services.ontology_graph import import_graph_iri
        result = import_graph_iri(ONT_IRI, "file", "some/dir/data.owl")
        assert result == f"{ONT_IRI}/imports/data.owl"

    def test_import_graph_iri_file_sanitizes_spaces(self):
        """공백/특수문자는 언더스코어로 교체."""
        from services.ontology_graph import import_graph_iri
        result = import_graph_iri(ONT_IRI, "file", "my ontology.ttl")
        assert result == f"{ONT_IRI}/imports/my_ontology.ttl"


# ─────────────────────────────────────────────────────────────────
# D1 (continued): import API → named graph IRI 검증
# ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_import_file_uses_import_graph_iri(
    client: AsyncClient, created_ontology: dict
) -> None:
    """POST /import/file → sparql_update가 import_graph_iri를 사용한다."""
    oid = created_ontology["id"]

    ttl_content = b"@prefix owl: <http://www.w3.org/2002/07/owl#> .\n<http://ex.org/A> a owl:Class ."
    files = {"file": ("test_onto.ttl", io.BytesIO(ttl_content), "text/turtle")}

    with patch("api.import_.resolve_ontology_iri", return_value=ONT_IRI), \
         patch("api.import_.import_graph_iri") as mock_iri_fn, \
         patch("api.import_.import_svc.bulk_insert_raw_gsp", return_value=1), \
         patch("api.import_.import_svc.gsp_content_type_for_format", return_value="text/turtle"), \
         patch("api.import_.record_import_provenance"):
        mock_iri_fn.return_value = f"{ONT_IRI}/imports/test_onto.ttl"
        response = await client.post(
            f"/ontologies/{oid}/import/file",
            files=files,
        )

    assert response.status_code in (200, 201, 202)
    mock_iri_fn.assert_called_once()
    call_args = mock_iri_fn.call_args
    assert call_args[0][1] == "file"  # source_type


@pytest.mark.asyncio
async def test_import_standard_uses_import_graph_iri(
    client: AsyncClient, created_ontology: dict
) -> None:
    """POST /import/standard → import_graph_iri(ont_iri, 'standard', name) 호출."""
    oid = created_ontology["id"]

    with patch("api.import_.resolve_ontology_iri", return_value=ONT_IRI), \
         patch("api.import_.import_graph_iri") as mock_iri_fn, \
         patch("api.import_.import_svc.import_standard", return_value=[]), \
         patch("api.import_.import_svc.bulk_insert", return_value=0), \
         patch("api.import_.record_import_provenance"):
        mock_iri_fn.return_value = f"{ONT_IRI}/imports/standard/foaf"
        response = await client.post(
            f"/ontologies/{oid}/import/standard",
            json={"name": "foaf"},
        )

    assert response.status_code in (200, 201, 202)
    mock_iri_fn.assert_called_once()
    call_args = mock_iri_fn.call_args
    assert call_args[0][1] == "standard"
    assert call_args[0][2] == "foaf"


# ─────────────────────────────────────────────────────────────────
# D2: graph_iris 파라미터 필터 테스트
# ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_concepts_with_graph_iris_passes_filter(
    client: AsyncClient, created_ontology: dict
) -> None:
    """GET /concepts?graph_iris=... → SPARQL 쿼리에 필터가 적용된다."""
    oid = created_ontology["id"]
    store = client._transport.app.state.ontology_store  # type: ignore[attr-defined]
    store.sparql_select.return_value = [{"total": {"value": "0"}}]

    graph1 = f"{ONT_IRI}/manual"
    graph2 = f"{ONT_IRI}/imports/test.ttl"

    with patch("api.concepts.resolve_ontology_iri", return_value=ONT_IRI):
        response = await client.get(
            f"/ontologies/{oid}/concepts",
            params={"graph_iris": [graph1, graph2]},
        )
    assert response.status_code == 200
    # sparql_select가 호출됐는지 확인
    assert store.sparql_select.called
    # 호출된 쿼리에 graph IRI가 포함되는지 검증
    call_args = store.sparql_select.call_args_list
    queries_called = [str(c.args[0]) if c.args else "" for c in call_args]
    # 적어도 하나의 쿼리에 graph1 IRI가 포함돼야 함
    assert any(graph1 in q for q in queries_called), (
        f"Expected graph IRI '{graph1}' in SPARQL queries, got: {queries_called}"
    )


@pytest.mark.asyncio
async def test_list_concepts_without_graph_iris_uses_prefix_filter(
    client: AsyncClient, created_ontology: dict
) -> None:
    """graph_iris 없으면 → STRSTARTS prefix 방식으로 전체 조회."""
    oid = created_ontology["id"]
    store = client._transport.app.state.ontology_store  # type: ignore[attr-defined]
    store.sparql_select.return_value = [{"total": {"value": "0"}}]

    with patch("api.concepts.resolve_ontology_iri", return_value=ONT_IRI):
        response = await client.get(f"/ontologies/{oid}/concepts")
    assert response.status_code == 200
    assert store.sparql_select.called


@pytest.mark.asyncio
async def test_list_individuals_with_graph_iris(
    client: AsyncClient, created_ontology: dict
) -> None:
    """GET /individuals?graph_iris=... → 200 응답."""
    oid = created_ontology["id"]
    store = client._transport.app.state.ontology_store  # type: ignore[attr-defined]
    store.sparql_select.return_value = [{"total": {"value": "0"}}]

    graph1 = f"{ONT_IRI}/manual"

    with patch("api.individuals.resolve_ontology_iri", return_value=ONT_IRI):
        response = await client.get(
            f"/ontologies/{oid}/individuals",
            params={"graph_iris": [graph1]},
        )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_properties_with_graph_iris(
    client: AsyncClient, created_ontology: dict
) -> None:
    """GET /properties?graph_iris=... → 200 응답."""
    oid = created_ontology["id"]
    store = client._transport.app.state.ontology_store  # type: ignore[attr-defined]
    store.sparql_select.return_value = [{"total": {"value": "0"}}]

    graph1 = f"{ONT_IRI}/manual"

    with patch("api.properties.resolve_ontology_iri", return_value=ONT_IRI):
        response = await client.get(
            f"/ontologies/{oid}/properties",
            params={"graph_iris": [graph1]},
        )
    assert response.status_code == 200


# ─────────────────────────────────────────────────────────────────
# D2: create_concept → manual graph에 INSERT
# ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_concept_writes_to_manual_graph(
    client: AsyncClient, created_ontology: dict
) -> None:
    """POST /concepts → sparql_update가 /manual 그래프에 쓴다."""
    oid = created_ontology["id"]
    store = client._transport.app.state.ontology_store  # type: ignore[attr-defined]
    store.sparql_ask.return_value = False

    payload = {
        "iri": f"{ONT_IRI}#TestClass",
        "label": "Test Class",
        "super_classes": [],
        "restrictions": [],
    }

    with patch("api.concepts.resolve_ontology_iri", return_value=ONT_IRI):
        response = await client.post(f"/ontologies/{oid}/concepts", json=payload)
    assert response.status_code == 201

    # sparql_update 호출 → /manual 그래프에 INSERT
    assert store.sparql_update.called
    update_query = store.sparql_update.call_args.args[0]
    assert "/manual" in update_query, (
        f"Expected '/manual' graph in INSERT query, got:\n{update_query}"
    )
