"""
services/graph_store.py — Neo4j LPG 저장소 Cypher 래퍼

Neo4j는 그래프 탐색(서브그래프 쿼리, 시각화 데이터 제공) 전용으로 사용한다.
Oxigraph(SPARQL)이 소스 오브 트루스이며, Neo4j는 읽기 최적화 복제본이다.

노드 레이블:
  - :Concept (owl:Class)
  - :Individual (owl:NamedIndividual)

관계 유형:
  - [:SUBCLASS_OF]
  - [:TYPE] (Individual → Concept)
  - [:RELATION {propertyIri: "..."}] (ObjectProperty 값)
"""

import logging
from typing import Any

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession

logger = logging.getLogger(__name__)

_NODE_LIMIT = 500  # 서브그래프 노드 최대 수


class GraphStore:
    """Neo4j AsyncDriver 래퍼."""

    def __init__(self, uri: str, user: str, password: str):
        self._driver: AsyncDriver = AsyncGraphDatabase.driver(
            uri,
            auth=(user, password),
            max_connection_pool_size=50,
        )
        logger.info("GraphStore initialized (uri=%s)", uri)

    # ── 내부 헬퍼 ─────────────────────────────────────────────────────────

    def _session(self) -> AsyncSession:
        return self._driver.session()

    # ── TBox (Concept / Property) ──────────────────────────────────────────

    async def upsert_concept(
        self,
        ontology_id: str,
        iri: str,
        label: str,
        super_class_iris: list[str],
    ) -> None:
        """Concept 노드 upsert + SUBCLASS_OF 관계 동기화."""
        async with self._session() as session:
            async with session.begin_transaction() as tx:
                # 노드 생성/갱신
                await tx.run(
                    """
                    MERGE (c:Concept {iri: $iri})
                    SET c.label = $label, c.ontologyId = $ontologyId
                    """,
                    iri=iri, label=label, ontologyId=ontology_id,
                )
                # 기존 SUBCLASS_OF 관계 삭제 후 재생성 (변경 감지 단순화)
                await tx.run(
                    "MATCH (c:Concept {iri: $iri})-[r:SUBCLASS_OF]->() DELETE r",
                    iri=iri,
                )
                for parent_iri in super_class_iris:
                    await tx.run(
                        """
                        MERGE (parent:Concept {iri: $parentIri})
                        WITH parent
                        MATCH (c:Concept {iri: $iri})
                        MERGE (c)-[:SUBCLASS_OF]->(parent)
                        """,
                        iri=iri, parentIri=parent_iri,
                    )

    async def upsert_individual(
        self,
        ontology_id: str,
        iri: str,
        label: str | None,
        type_iris: list[str],
        data_properties: dict[str, str],
    ) -> None:
        """Individual 노드 upsert + TYPE 관계 설정."""
        async with self._session() as session:
            async with session.begin_transaction() as tx:
                await tx.run(
                    """
                    MERGE (i:Individual {iri: $iri})
                    SET i += $dataProps, i.label = $label, i.ontologyId = $ontologyId
                    """,
                    iri=iri,
                    label=label,
                    ontologyId=ontology_id,
                    dataProps=data_properties,
                )
                # 기존 TYPE 관계 삭제 후 재생성
                await tx.run(
                    "MATCH (i:Individual {iri: $iri})-[r:TYPE]->() DELETE r",
                    iri=iri,
                )
                for type_iri in type_iris:
                    await tx.run(
                        """
                        MERGE (c:Concept {iri: $typeIri})
                        WITH c
                        MATCH (i:Individual {iri: $iri})
                        MERGE (i)-[:TYPE]->(c)
                        """,
                        iri=iri, typeIri=type_iri,
                    )

    async def upsert_object_property_value(
        self,
        subject_iri: str,
        property_iri: str,
        object_iri: str,
        property_label: str | None = None,
    ) -> None:
        """ObjectProperty 값을 Neo4j 관계(RELATION)로 upsert."""
        async with self._session() as session:
            await session.run(
                """
                MATCH (s {iri: $sIri}), (o {iri: $oIri})
                MERGE (s)-[r:RELATION {propertyIri: $propIri}]->(o)
                SET r.propertyLabel = $propLabel
                """,
                sIri=subject_iri,
                oIri=object_iri,
                propIri=property_iri,
                propLabel=property_label,
            )

    # ── 배치 upsert (sync_service 용) ─────────────────────────────────────

    async def batch_upsert_concepts(self, ontology_id: str, concepts: list[dict]) -> int:
        """
        Concept 노드 배치 upsert.
        concepts: [{ iri, label, superClasses: [iri] }]
        """
        async with self._session() as session:
            result = await session.run(
                """
                UNWIND $concepts AS c
                MERGE (n:Concept {iri: c.iri})
                SET n.label = c.label, n.ontologyId = $ontologyId
                RETURN count(n) AS cnt
                """,
                concepts=concepts,
                ontologyId=ontology_id,
            )
            record = await result.single()
            return record["cnt"] if record else 0

    async def batch_upsert_individuals(self, ontology_id: str, individuals: list[dict]) -> int:
        """
        Individual 노드 배치 upsert.
        individuals: [{ iri, label, typeIris: [iri], dataProps: {key: val} }]
        """
        async with self._session() as session:
            result = await session.run(
                """
                UNWIND $individuals AS i
                MERGE (n:Individual {iri: i.iri})
                SET n.label = i.label, n.ontologyId = $ontologyId
                RETURN count(n) AS cnt
                """,
                individuals=individuals,
                ontologyId=ontology_id,
            )
            record = await result.single()
            return record["cnt"] if record else 0

    # ── 서브그래프 ────────────────────────────────────────────────────────

    async def get_subgraph(
        self,
        ontology_id: str,
        entity_iris: list[str],
        depth: int,
    ) -> dict:
        """
        BFS로 서브그래프 탐색. 노드 최대 _NODE_LIMIT개.
        반환: { nodes: [...], edges: [...] }
        """
        depth = max(1, min(depth, 5))

        async with self._session() as session:
            result = await session.run(
                f"""
                MATCH path = (n)-[*1..{depth}]-(m)
                WHERE n.iri IN $iris AND n.ontologyId = $ontologyId
                WITH nodes(path) AS ns, relationships(path) AS rs
                UNWIND ns AS node
                WITH DISTINCT node, rs
                WITH collect(DISTINCT node)[0..{_NODE_LIMIT}] AS nodes, rs
                RETURN nodes, rs AS rels
                """,
                iris=entity_iris,
                ontologyId=ontology_id,
            )

            seen_nodes: dict[str, dict] = {}
            seen_edges: dict[str, dict] = {}

            async for record in result:
                for node in record["nodes"]:
                    iri = node.get("iri", "")
                    if iri and iri not in seen_nodes:
                        labels = list(node.labels)
                        kind = "concept" if "Concept" in labels else "individual"
                        seen_nodes[iri] = {
                            "iri": iri,
                            "label": node.get("label", iri),
                            "kind": kind,
                            "ontologyId": node.get("ontologyId", ontology_id),
                        }
                for rel in record["rels"]:
                    edge_key = f"{rel.start_node['iri']}-{rel['propertyIri']}-{rel.end_node['iri']}"
                    if edge_key not in seen_edges:
                        seen_edges[edge_key] = {
                            "source": rel.start_node.get("iri", ""),
                            "target": rel.end_node.get("iri", ""),
                            "propertyIri": rel.get("propertyIri", rel.type),
                            "propertyLabel": rel.get("propertyLabel", rel.type),
                            "kind": "relation",
                        }

        return {
            "nodes": list(seen_nodes.values()),
            "edges": list(seen_edges.values()),
        }

    # ── 삭제 ──────────────────────────────────────────────────────────────

    async def delete_ontology_data(self, ontology_id: str) -> None:
        """온톨로지 관련 Neo4j 데이터 전체 삭제 (배치)."""
        async with self._session() as session:
            await session.run(
                """
                CALL {
                    MATCH (n {ontologyId: $ontologyId})
                    WITH n LIMIT 10000
                    DETACH DELETE n
                } IN TRANSACTIONS
                """,
                ontologyId=ontology_id,
            )

    async def close(self) -> None:
        """Neo4j 드라이버 연결 종료."""
        await self._driver.close()
        logger.info("GraphStore closed.")
