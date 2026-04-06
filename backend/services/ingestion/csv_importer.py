"""
services/ingestion/csv_importer.py — CSV 파일 → Fuseki 일괄 import

흐름:
  1. csv.DictReader 로 파일 파싱
  2. iri_generator + rdflib Graph → GSP POST(Turtle) 한 번으로 kg 그래프에 삽입
  3. 동일 소스 재import 시 prov:wasAttributedTo 가 해당 source.id 인 트리플만 먼저 삭제
"""
from __future__ import annotations

import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rdflib import Graph, URIRef, Literal, BNode
from rdflib.namespace import XSD

from services.ingestion.iri_generator import generate
from services.ontology_graph import resolve_kg_graph_iri
from services.ontology_store import OntologyStore, Triple

logger = logging.getLogger(__name__)

_RDF_TYPE = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
_PROV_GENERATED_AT = URIRef("http://www.w3.org/ns/prov#generatedAtTime")
_PROV_ATTRIBUTED_TO = URIRef("http://www.w3.org/ns/prov#wasAttributedTo")

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
        kg_iri = await resolve_kg_graph_iri(self._store, ontology_id, dataset=dataset)
        if kg_iri is None:
            raise ValueError(f"Ontology not found: {ontology_id}")

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        cfg = source.config
        records = _read_csv(file_path, cfg)
        if not records:
            return {
                "rows_read": 0,
                "triples_inserted": 0,
                "named_graph": kg_iri,
            }

        logger.info(
            "CSV import start: source=%s, rows=%d, ontology=%s",
            source.id, len(records), ontology_id,
        )

        triples_inserted = await self._import_to_fuseki(
            records, source, kg_iri, timestamp, dataset=dataset,
        )

        logger.info(
            "CSV import done: triples=%d, graph=%s",
            triples_inserted, kg_iri,
        )
        return {
            "rows_read": len(records),
            "triples_inserted": triples_inserted,
            "named_graph": kg_iri,
        }

    async def _delete_triples_for_source(self, kg_iri: str, source_id: str, dataset: str | None) -> None:
        """이전 CSV import에서 해당 소스가 남긴 트리플 제거 (prov:wasAttributedTo 일치)."""
        esc = source_id.replace("\\", "\\\\").replace('"', '\\"')
        await self._store.sparql_update(
            f"""
            PREFIX prov: <http://www.w3.org/ns/prov#>
            DELETE {{ GRAPH <{kg_iri}> {{ ?s ?p ?o }} }}
            WHERE {{
              GRAPH <{kg_iri}> {{
                ?s prov:wasAttributedTo ?attr .
                FILTER(STR(?attr) = "{esc}")
                ?s ?p ?o .
              }}
            }}
            """,
            dataset=dataset,
        )

    async def _import_to_fuseki(
        self,
        records: list[dict],
        source: Any,
        kg_iri: str,
        timestamp: str,
        dataset: str | None = None,
    ) -> int:
        """CSV 레코드를 Triple로 변환하여 kg 그래프에 삽입."""
        await self._delete_triples_for_source(kg_iri, source.id, dataset=dataset)

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

        if not triples:
            return 0
        g = Graph()
        for t in triples:
            g.add((t.subject, t.predicate, t.object_))
        turtle = g.serialize(format="turtle")
        await self._store.post_graph_turtle(kg_iri, turtle, dataset=dataset)
        return len(triples)
