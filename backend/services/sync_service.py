"""
Sync Service — Oxigraph → Neo4j 동기화
"""
from __future__ import annotations

import time

# TODO: import OntologyStore, Neo4j driver
# from backend.services.ontology_store import OntologyStore
# from neo4j import AsyncGraphDatabase

BATCH_SIZE = 1000


class SyncService:
    """Oxigraph triple store의 TBox/ABox를 Neo4j 그래프 DB로 동기화."""

    async def sync_tbox(self, ontology_id: str) -> int:
        """
        CONSTRUCT로 owl:Class, owl:ObjectProperty, owl:DatatypeProperty 추출.
        Neo4j MERGE (:Concept {iri}) 및 (:Property {iri}) 노드 생성/갱신.

        Args:
            ontology_id: 동기화할 온톨로지 ID

        Returns:
            int: 처리된 노드 수
        """
        # TODO: implement
        # store = OntologyStore.get_instance()
        # tbox = await store.sparql_construct(ontology_id, TBOX_CONSTRUCT_QUERY)
        # async with neo4j_session() as session:
        #     result = await session.run(TBOX_MERGE_CYPHER, triples=tbox)
        #     return result.consume().counters.nodes_created
        raise NotImplementedError

    async def sync_abox_batch(self, ontology_id: str) -> int:
        """
        owl:NamedIndividual 및 Property 값 추출 → Neo4j 벌크 UNWIND+MERGE.
        배치 크기: 1000 triple.

        Args:
            ontology_id: 동기화할 온톨로지 ID

        Returns:
            int: 처리된 triple 수
        """
        # TODO: implement
        # store = OntologyStore.get_instance()
        # offset = 0
        # total = 0
        # while True:
        #     batch = await store.sparql_select(ontology_id, ABOX_SELECT, limit=BATCH_SIZE, offset=offset)
        #     if not batch:
        #         break
        #     async with neo4j_session() as session:
        #         await session.run(ABOX_MERGE_CYPHER, rows=batch)
        #     total += len(batch)
        #     offset += BATCH_SIZE
        # return total
        raise NotImplementedError

    async def full_sync(self, ontology_id: str) -> dict:
        """
        sync_tbox + sync_abox_batch 순서로 실행, 소요시간/건수 반환.

        Args:
            ontology_id: 동기화할 온톨로지 ID

        Returns:
            dict: {tbox_count, abox_count, elapsed_seconds}
        """
        # TODO: implement
        # start = time.monotonic()
        # tbox_count = await self.sync_tbox(ontology_id)
        # abox_count = await self.sync_abox_batch(ontology_id)
        # elapsed = time.monotonic() - start
        # return {"tbox_count": tbox_count, "abox_count": abox_count, "elapsed_seconds": elapsed}
        raise NotImplementedError
