"""
services/ingestion/csv_importer.py — CSV 파일 → Fuseki 일괄 import

흐름:
  1. csv.DictReader 로 파일 파싱
  2. iri_generator + rdflib Triple 생성 → OntologyStore.insert_triples() 로 Named Graph 삽입
     (기존 Named Graph는 DROP 후 원자적 교체)
"""
from __future__ import annotations

import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rdflib import URIRef, Literal, BNode
from rdflib.namespace import XSD

from services.ingestion.iri_generator import generate
from services.ontology_store import OntologyStore, Triple

logger = logging.getLogger(__name__)

_RDF_TYPE = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
_PROV_GENERATED_AT = URIRef("http://www.w3.org/ns/prov#generatedAtTime")
_PROV_ATTRIBUTED_TO = URIRef("http://www.w3.org/ns/prov#wasAttributedTo")

_BATCH_SIZE = 500


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
    """CSV 파일을 Fuseki에 import하는 서비스."""

    def __init__(self, store: OntologyStore) -> None:
        self._store = store

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
        dataset: str | None = None,
    ) -> dict:
        """CSV를 Fuseki에 import하고 결과를 반환."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        named_graph = _build_named_graph_iri(source.id, timestamp)

        cfg = source.config
        records = _read_csv(file_path, cfg)
        if not records:
            return {
                "rows_read": 0,
                "triples_inserted": 0,
                "named_graph": named_graph,
            }

        logger.info(
            "CSV import start: source=%s, rows=%d, ontology=%s",
            source.id, len(records), ontology_id,
        )

        triples_inserted = await self._import_to_fuseki(records, source, named_graph, timestamp, dataset=dataset)

        logger.info(
            "CSV import done: triples=%d, graph=%s",
            triples_inserted, named_graph,
        )
        return {
            "rows_read": len(records),
            "triples_inserted": triples_inserted,
            "named_graph": named_graph,
        }

    async def _import_to_fuseki(
        self,
        records: list[dict],
        source: Any,
        named_graph: str,
        timestamp: str,
        dataset: str | None = None,
    ) -> int:
        """CSV 레코드를 Triple로 변환하여 Fuseki Named Graph에 삽입."""
        # 기존 Named Graph DROP (재적재 원자적 교체)
        await self._store.delete_graph(named_graph, dataset=dataset)

        rdf_type_node = _RDF_TYPE
        concept_node = URIRef(source.concept_iri)
        ts_literal = Literal(timestamp, datatype=XSD.string)
        src_literal = Literal(source.id, datatype=XSD.string)

        triples: list[Triple] = []
        for record in records:
            try:
                iri = generate(source.iri_template, record)
            except (KeyError, ValueError) as exc:
                logger.warning("IRI generation failed: %s — skipping row", exc)
                continue

            subject = URIRef(iri)
            triples.append(Triple(subject, rdf_type_node, concept_node))

            for mapping in source.property_mappings:
                raw = record.get(mapping.source_field)
                if raw is None:
                    continue
                value_str = str(raw)
                if value_str.startswith("http") or value_str.startswith("urn"):
                    obj: URIRef | Literal = URIRef(value_str)
                elif mapping.datatype:
                    obj = Literal(value_str, datatype=URIRef(mapping.datatype))
                else:
                    obj = Literal(value_str, datatype=XSD.string)
                triples.append(Triple(subject, URIRef(mapping.property_iri), obj))

            triples.append(Triple(subject, _PROV_GENERATED_AT, ts_literal))
            triples.append(Triple(subject, _PROV_ATTRIBUTED_TO, src_literal))

        # 배치 삽입
        total = 0
        for i in range(0, len(triples), _BATCH_SIZE):
            batch = triples[i:i + _BATCH_SIZE]
            await self._store.insert_triples(named_graph, batch, dataset=dataset)
            total += len(batch)

        return total
