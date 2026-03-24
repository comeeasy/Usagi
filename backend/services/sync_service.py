"""Sync Service — Oxigraph → Neo4j 동기화"""
from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

PREFIX = (
    "PREFIX owl: <http://www.w3.org/2002/07/owl#> "
    "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>"
)


def _v(term: Any, default: str = "") -> str:
    """pyoxigraph SPARQL 결과 term → str 변환."""
    if isinstance(term, dict):
        return term.get("value", default)
    if term:
        return str(term)
    return default


class SyncService:
    """Oxigraph triple store의 TBox/ABox를 Neo4j 그래프 DB로 동기화."""

    def __init__(self, ontology_store: Any, graph_store: Any) -> None:
        self._store = ontology_store
        self._graph_store = graph_store

    async def sync_tbox(self, ontology_id: str) -> int:
        """
        SPARQL SELECT로 owl:Class 추출 → Neo4j batch_upsert_concepts 호출.

        Returns:
            int: 처리된 Concept 노드 수
        """
        tbox_iri = f"{ontology_id}/tbox"
        query = f"""
            {PREFIX}
            SELECT ?iri ?label WHERE {{
                GRAPH <{tbox_iri}> {{
                    ?iri a owl:Class .
                    OPTIONAL {{ ?iri rdfs:label ?label }}
                }}
            }}
        """

        rows = await self._store.sparql_select(query)

        concept_list = [
            {"iri": _v(row.get("iri")), "label": _v(row.get("label"))}
            for row in rows
            if row.get("iri")
        ]

        if not concept_list:
            return 0

        count = await self._graph_store.batch_upsert_concepts(ontology_id, concept_list)
        logger.info("sync_tbox: upserted %d concepts for ontology=%s", count, ontology_id)
        return count

    async def sync_abox(self, ontology_id: str) -> int:
        """
        SPARQL SELECT로 owl:NamedIndividual 추출 → Neo4j batch_upsert_individuals 호출.

        Returns:
            int: 처리된 Individual 노드 수
        """
        query = f"""
            {PREFIX}
            SELECT ?iri ?type WHERE {{
                ?iri a owl:NamedIndividual .
                ?iri a ?type .
                FILTER(?type != owl:NamedIndividual)
            }}
        """

        rows = await self._store.sparql_select(query)

        # Group by iri, collect types
        individuals: dict[str, dict] = {}
        for row in rows:
            iri = _v(row.get("iri"))
            type_iri = _v(row.get("type"))
            if not iri:
                continue
            if iri not in individuals:
                individuals[iri] = {"iri": iri, "label": None, "typeIris": []}
            if type_iri:
                individuals[iri]["typeIris"].append(type_iri)

        individual_list = list(individuals.values())

        if not individual_list:
            return 0

        count = await self._graph_store.batch_upsert_individuals(ontology_id, individual_list)
        logger.info("sync_abox: upserted %d individuals for ontology=%s", count, ontology_id)
        return count

    async def full_sync(self, ontology_id: str) -> dict:
        """
        sync_tbox + sync_abox 순서로 실행, 소요시간/건수 반환.

        Returns:
            dict: {tbox_count, abox_count, elapsed_seconds}
        """
        start = time.monotonic()
        tbox_count = await self.sync_tbox(ontology_id)
        abox_count = await self.sync_abox(ontology_id)
        elapsed = time.monotonic() - start

        result = {
            "tbox_count": tbox_count,
            "abox_count": abox_count,
            "elapsed_seconds": round(elapsed, 3),
        }
        logger.info("full_sync for ontology=%s: %s", ontology_id, result)
        return result
