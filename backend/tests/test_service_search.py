"""
Tests for SearchService.

SearchService는 현재 stub 상태(NotImplementedError).
실제 구현 후 통과 예정. docs/debug.md 참조.
"""
import pytest


@pytest.mark.xfail(raises=NotImplementedError, strict=True, reason="SearchService not implemented")
async def test_search_entities_raises_not_implemented():
    from services.search_service import search_entities
    await search_entities("ont-001", "Person")


@pytest.mark.xfail(raises=NotImplementedError, strict=True, reason="SearchService not implemented")
async def test_search_relations_raises_not_implemented():
    from services.search_service import search_relations
    await search_relations("ont-001", "has")


@pytest.mark.xfail(raises=NotImplementedError, strict=True, reason="SearchService not implemented")
async def test_vector_search_raises_not_implemented():
    from services.search_service import vector_search
    await vector_search("ont-001", "employee")
