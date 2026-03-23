"""
pytest fixtures for ontology platform tests.
"""
from __future__ import annotations

import pytest
import pytest_asyncio

# TODO: import FastAPI app, httpx AsyncClient, OntologyStore
# from httpx import AsyncClient
# from fastapi import FastAPI
# from backend.main import create_app
# from backend.services.ontology_store import OntologyStore


@pytest_asyncio.fixture
async def app():
    """테스트용 FastAPI 앱 인스턴스."""
    # TODO: implement
    # application = create_app()
    # async with lifespan(application):
    #     yield application
    raise NotImplementedError


@pytest_asyncio.fixture
async def client(app):
    """테스트용 httpx AsyncClient."""
    # TODO: implement
    # async with AsyncClient(app=app, base_url="http://test") as ac:
    #     yield ac
    raise NotImplementedError


@pytest_asyncio.fixture
async def ontology_store():
    """인메모리 Oxigraph OntologyStore 인스턴스."""
    # TODO: implement
    # store = OntologyStore(endpoint="memory://")
    # yield store
    # await store.clear()
    raise NotImplementedError


@pytest.fixture
def sample_ontology() -> dict:
    """테스트용 온톨로지 생성 페이로드."""
    return {
        "name": "Test Ontology",
        "description": "A test ontology for unit tests",
        "base_iri": "https://test.example.org/ontology#",
        "version": "1.0.0",
    }
