"""
RDF Transformer — 소스 이벤트 → RDF Triple 변환
"""
from __future__ import annotations

from typing import Any

# TODO: import internal models
# from backend.models.source import BackingSource, SourceEvent
# from backend.models.ontology import Triple
# from backend.services.ingestion.iri_generator import generate as generate_iri


class RDFTransformer:
    """소스 이벤트 레코드를 RDF Triple로 변환."""

    def transform(self, event: Any, source: Any) -> list:
        """
        소스 이벤트를 RDF Triple 목록으로 변환.

        변환 순서:
        1. iri_generator.generate(template, record)으로 IRI 생성
        2. rdf:type 트리플: {iri} rdf:type {conceptIri}
        3. propertyMappings 순회: DataProperty → Literal, ObjectProperty → NamedNode
        4. provenance 메타데이터 트리플: prov:generatedAtTime, prov:wasAttributedTo

        Args:
            event: SourceEvent — 변환할 소스 이벤트
            source: BackingSource — 소스 설정 (property mappings 포함)

        Returns:
            list[Triple]: 변환된 Triple 목록
        """
        # TODO: implement
        # triples = []
        # for record in event.records:
        #     iri = generate_iri(source.iri_template, record)
        #     triples.append(Triple(subject=iri, predicate=RDF_TYPE, object=source.concept_iri))
        #     for mapping in source.property_mappings:
        #         value = record.get(mapping.source_field)
        #         if value is None:
        #             continue
        #         if mapping.property_type == "data":
        #             triples.append(Triple(subject=iri, predicate=mapping.property_iri, object=Literal(value)))
        #         else:
        #             triples.append(Triple(subject=iri, predicate=mapping.property_iri, object=NamedNode(value)))
        #     graph_iri = self.build_named_graph_iri(event.source_id, event.timestamp)
        #     triples.append(Triple(subject=iri, predicate=PROV_GENERATED_AT_TIME, object=Literal(event.timestamp)))
        #     triples.append(Triple(subject=iri, predicate=PROV_WAS_ATTRIBUTED_TO, object=NamedNode(event.source_id)))
        # return triples
        raise NotImplementedError

    def build_named_graph_iri(self, source_id: str, timestamp: str) -> str:
        """
        "{source_id}/{timestamp}" 형식으로 Named Graph IRI 생성.

        Args:
            source_id: 소스 ID
            timestamp: ISO 8601 타임스탬프

        Returns:
            str: Named Graph IRI
        """
        # TODO: implement
        # return f"{source_id}/{timestamp}"
        raise NotImplementedError
