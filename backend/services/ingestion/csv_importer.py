"""
services/ingestion/csv_importer.py — CSV 파일 → Oxigraph + Neo4j 일괄 import

흐름:
  1. csv.DictReader 로 파일 파싱
  2. [Phase 1] iri_generator + RDF 트리플 생성 → Oxigraph Named Graph bulk insert
     (기존 Named Graph는 DROP 후 원자적 교체)
  3. [Phase 2] 파싱된 행을 UNWIND $rows Cypher로 Neo4j 배치 upsert
     (500행 단위 chunking)
"""
from __future__ import annotations

import asyncio
import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pyoxigraph import Literal as RDFLiteral, NamedNode, Quad

from services.ingestion.iri_generator import generate
from services.ontology_store import OntologyStore

logger = logging.getLogger(__name__)

# RDF 상수
_RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
_PROV_GENERATED_AT = "http://www.w3.org/ns/prov#generatedAtTime"
_PROV_ATTRIBUTED_TO = "http://www.w3.org/ns/prov#wasAttributedTo"
_XSD_STRING = "http://www.w3.org/2001/XMLSchema#string"

_NEO4J_BATCH = 500  # Neo4j UNWIND 배치 크기


def _build_named_graph_iri(source_id: str, timestamp: str) -> str:
    return f"urn:source:{source_id}/{timestamp}"


def _read_csv(file_path: Path, cfg: Any) -> list[dict]:
    """CSV 파일을 list[dict]로 읽는다. 모든 값은 str."""
    delimiter = cfg.delimiter if hasattr(cfg, "delimiter") else ","
    has_header = cfg.has_header if hasattr(cfg, "has_header") else True
    encoding = cfg.encoding if hasattr(cfg, "encoding") else "utf-8"
    skip_rows = cfg.skip_rows if hasattr(cfg, "skip_rows") else 0

    records: list[dict] = []
    with file_path.open(encoding=encoding, newline="") as f:
        for _ in range(skip_rows):
            f.readline()
        reader = csv.DictReader(f, delimiter=delimiter) if has_header else csv.reader(f, delimiter=delimiter)  # type: ignore[assignment]
        for row in reader:
            if has_header:
                records.append(dict(row))  # type: ignore[arg-type]
            else:
                records.append({str(i): v for i, v in enumerate(row)})  # type: ignore[union-attr]
    return records


class CSVImporter:
    """CSV 파일을 Oxigraph + Neo4j에 import하는 서비스."""

    def __init__(self, store: OntologyStore, graph_store: Any) -> None:
        self._store = store
        self._graph_store = graph_store

    async def preview(self, file_path: Path, cfg: Any) -> dict:
        """파일 파싱 없이 헤더와 행 수만 반환 (빠른 미리보기)."""
        delimiter = cfg.delimiter if hasattr(cfg, "delimiter") else ","
        encoding = cfg.encoding if hasattr(cfg, "encoding") else "utf-8"
        skip_rows = cfg.skip_rows if hasattr(cfg, "skip_rows") else 0
        has_header = cfg.has_header if hasattr(cfg, "has_header") else True

        headers: list[str] = []
        row_count = 0
        with file_path.open(encoding=encoding, newline="") as f:
            for _ in range(skip_rows):
                f.readline()
            reader = csv.reader(f, delimiter=delimiter)
            for i, row in enumerate(reader):
                if i == 0 and has_header:
                    headers = list(row)
                else:
                    row_count += 1
        return {"headers": headers, "row_count": row_count}

    async def import_file(
        self,
        file_path: Path,
        source: Any,  # BackingSource (source_type == 'csv-file')
        ontology_id: str,
    ) -> dict:
        """CSV를 Oxigraph + Neo4j에 모두 import하고 결과를 반환."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        named_graph = _build_named_graph_iri(source.id, timestamp)

        cfg = source.config
        records = _read_csv(file_path, cfg)
        if not records:
            return {
                "rows_read": 0,
                "triples_inserted": 0,
                "neo4j_nodes_upserted": 0,
                "named_graph": named_graph,
            }

        logger.info(
            "CSV import start: source=%s, rows=%d, ontology=%s",
            source.id, len(records), ontology_id,
        )

        triples = await self._phase_oxigraph(records, source, named_graph, timestamp)
        nodes = await self._phase_neo4j(records, source, ontology_id)

        logger.info(
            "CSV import done: triples=%d, neo4j_nodes=%d, graph=%s",
            triples, nodes, named_graph,
        )
        return {
            "rows_read": len(records),
            "triples_inserted": triples,
            "neo4j_nodes_upserted": nodes,
            "named_graph": named_graph,
        }

    # ── Phase 1: Oxigraph ─────────────────────────────────────────────────

    async def _phase_oxigraph(
        self,
        records: list[dict],
        source: Any,
        named_graph: str,
        timestamp: str,
    ) -> int:
        # 기존 Named Graph DROP (재적재 원자적 교체)
        await self._store.delete_graph(named_graph)

        graph_node = NamedNode(named_graph)
        rdf_type_node = NamedNode(_RDF_TYPE)
        prov_at_node = NamedNode(_PROV_GENERATED_AT)
        prov_attr_node = NamedNode(_PROV_ATTRIBUTED_TO)
        xsd_str_node = NamedNode(_XSD_STRING)
        concept_node = NamedNode(source.concept_iri)
        ts_literal = RDFLiteral(timestamp, datatype=xsd_str_node)
        src_literal = RDFLiteral(source.id, datatype=xsd_str_node)

        quads: list[Quad] = []
        for record in records:
            try:
                iri = generate(source.iri_template, record)
            except (KeyError, ValueError) as exc:
                logger.warning("IRI generation failed: %s — skipping row", exc)
                continue

            subject = NamedNode(iri)
            quads.append(Quad(subject, rdf_type_node, concept_node, graph_node))

            for mapping in source.property_mappings:
                raw = record.get(mapping.source_field)
                if raw is None:
                    continue
                value_str = str(raw)
                if value_str.startswith("http") or value_str.startswith("urn"):
                    obj: NamedNode | RDFLiteral = NamedNode(value_str)
                elif mapping.datatype:
                    obj = RDFLiteral(value_str, datatype=NamedNode(mapping.datatype))
                else:
                    obj = RDFLiteral(value_str, datatype=xsd_str_node)
                quads.append(Quad(subject, NamedNode(mapping.property_iri), obj, graph_node))

            quads.append(Quad(subject, prov_at_node, ts_literal, graph_node))
            quads.append(Quad(subject, prov_attr_node, src_literal, graph_node))

        # Bulk insert (executor로 블로킹 해제)
        ox_store = self._store._store
        async with self._store._write_lock:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, ox_store.extend, quads)

        return len(quads)

    # ── Phase 2: Neo4j ────────────────────────────────────────────────────

    async def _phase_neo4j(
        self,
        records: list[dict],
        source: Any,
        ontology_id: str,
    ) -> int:
        cfg = source.config
        pk_field = cfg.primary_key_field if hasattr(cfg, "primary_key_field") else ""

        rows: list[dict] = []
        for record in records:
            try:
                iri = generate(source.iri_template, record)
            except (KeyError, ValueError):
                continue
            # label: PK 필드 값 → 없으면 IRI 마지막 세그먼트
            raw_label = record.get(pk_field, "") if pk_field else ""
            label = str(raw_label) if raw_label else iri.split("/")[-1].split("#")[-1]
            rows.append({"iri": iri, "label": label})

        if not rows:
            return 0

        total = 0
        for i in range(0, len(rows), _NEO4J_BATCH):
            batch = rows[i : i + _NEO4J_BATCH]
            async with self._graph_store._session() as session:
                result = await session.run(
                    """
                    UNWIND $rows AS row
                    MERGE (n:Individual {iri: row.iri})
                    SET n.label = row.label, n.ontologyId = $ontologyId
                    WITH n
                    MERGE (c:Concept {iri: $conceptIri})
                    MERGE (n)-[:TYPE]->(c)
                    RETURN count(n) AS cnt
                    """,
                    rows=batch,
                    ontologyId=ontology_id,
                    conceptIri=source.concept_iri,
                )
                record = await result.single()
                total += record["cnt"] if record else 0

        return total
