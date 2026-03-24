"""RDF Transformer — 소스 이벤트 → RDF Triple 변환"""
from __future__ import annotations

from typing import Any

from pyoxigraph import NamedNode, Literal as RDFLiteral

from services.ontology_store import Triple
from services.ingestion.iri_generator import generate

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
PROV_GENERATED_AT_TIME = "http://www.w3.org/ns/prov#generatedAtTime"
PROV_WAS_ATTRIBUTED_TO = "http://www.w3.org/ns/prov#wasAttributedTo"
XSD_STRING = "http://www.w3.org/2001/XMLSchema#string"


def build_named_graph_iri(source_id: str, timestamp: str) -> str:
    """urn:source:{source_id}/{timestamp} 형식으로 Named Graph IRI 생성."""
    return f"urn:source:{source_id}/{timestamp}"


class RDFTransformer:
    """소스 이벤트 레코드를 RDF Triple로 변환."""

    def transform(self, event: Any, source: Any) -> list[Triple]:
        """
        소스 이벤트를 RDF Triple 목록으로 변환.

        변환 순서:
        1. iri_generator.generate(template, record)으로 IRI 생성
        2. rdf:type 트리플: {iri} rdf:type {conceptIri}
        3. propertyMappings 순회: DataProperty → Literal, ObjectProperty → NamedNode
        4. provenance 메타데이터 트리플: prov:generatedAtTime, prov:wasAttributedTo
        """
        triples: list[Triple] = []

        for record in event.records:
            try:
                iri = generate(source.iri_template, record)
            except (KeyError, ValueError):
                continue

            subject = NamedNode(iri)

            # rdf:type triple
            triples.append(Triple(
                subject=subject,
                predicate=NamedNode(RDF_TYPE),
                object_=NamedNode(source.concept_iri),
            ))

            # Property mappings
            for mapping in source.property_mappings:
                value = record.get(mapping.source_field)
                if value is None:
                    continue

                value_str = str(value)

                # Determine if this is an object property (IRI value) or data property
                if value_str.startswith("http") or value_str.startswith("urn"):
                    obj: NamedNode | RDFLiteral = NamedNode(value_str)
                elif mapping.datatype:
                    obj = RDFLiteral(value_str, datatype=NamedNode(mapping.datatype))
                else:
                    obj = RDFLiteral(value_str, datatype=NamedNode(XSD_STRING))

                triples.append(Triple(
                    subject=subject,
                    predicate=NamedNode(mapping.property_iri),
                    object_=obj,
                ))

            # Provenance triples
            triples.append(Triple(
                subject=subject,
                predicate=NamedNode(PROV_GENERATED_AT_TIME),
                object_=RDFLiteral(event.timestamp, datatype=NamedNode(XSD_STRING)),
            ))
            triples.append(Triple(
                subject=subject,
                predicate=NamedNode(PROV_WAS_ATTRIBUTED_TO),
                object_=RDFLiteral(event.source_id, datatype=NamedNode(XSD_STRING)),
            ))

        return triples
