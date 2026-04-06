"""
Tests for RDFTransformer service.
"""
import pytest
from rdflib import URIRef, Literal

from services.ingestion.rdf_transformer import (
    RDFTransformer,
    build_named_graph_iri,
    PROV_GENERATED_AT_TIME,
    PROV_WAS_ATTRIBUTED_TO,
    RDF_TYPE,
)
from services.ontology_store import Triple
from models.source import BackingSource, SourceEvent, PropertyMapping


CONCEPT_IRI = "https://example.org/onto#Employee"
NAME_PROP = "https://example.org/onto#name"
DEPT_PROP = "https://example.org/onto#department"


def make_source(mappings=None):
    return BackingSource(
        id="src-001",
        ontology_id="ont-001",
        label="Test Source",
        source_type="jdbc",
        concept_iri=CONCEPT_IRI,
        iri_template="https://example.org/emp/{emp_id}",
        property_mappings=mappings or [],
    )


def make_event(records=None):
    return SourceEvent(
        source_id="src-001",
        ontology_id="ont-001",
        event_type="upsert",
        timestamp="2026-03-25T00:00:00Z",
        records=records or [{"emp_id": "1", "name": "Alice"}],
    )


def test_transform_produces_rdf_type_triple():
    """rdf:type 트리플이 생성되고 object가 concept_iri여야 함."""
    transformer = RDFTransformer()
    triples = transformer.transform(make_event(), make_source())
    type_triple = next(
        (t for t in triples if str(t.predicate) == RDF_TYPE),
        None,
    )
    assert type_triple is not None
    assert str(type_triple.object_) == CONCEPT_IRI


def test_transform_subject_iri_from_template():
    """subject IRI가 템플릿대로 생성됨."""
    transformer = RDFTransformer()
    triples = transformer.transform(make_event([{"emp_id": "42"}]), make_source())
    subjects = {str(t.subject) for t in triples}
    assert "https://example.org/emp/42" in subjects


def test_transform_property_mapping_literal():
    """DataProperty 매핑 → Literal 생성."""
    mapping = PropertyMapping(
        source_field="name",
        property_iri=NAME_PROP,
        datatype="http://www.w3.org/2001/XMLSchema#string",
    )
    transformer = RDFTransformer()
    triples = transformer.transform(make_event(), make_source(mappings=[mapping]))
    name_triple = next(
        (t for t in triples if str(t.predicate) == NAME_PROP),
        None,
    )
    assert name_triple is not None
    assert isinstance(name_triple.object_, Literal)
    assert str(name_triple.object_) == "Alice"


def test_transform_property_mapping_iri_value():
    """값이 IRI(http/urn 시작)이면 URIRef로 변환."""
    mapping = PropertyMapping(
        source_field="dept",
        property_iri=DEPT_PROP,
    )
    transformer = RDFTransformer()
    records = [{"emp_id": "1", "dept": "https://example.org/dept/Engineering"}]
    triples = transformer.transform(make_event(records), make_source(mappings=[mapping]))
    dept_triple = next(
        (t for t in triples if str(t.predicate) == DEPT_PROP),
        None,
    )
    assert dept_triple is not None
    assert isinstance(dept_triple.object_, URIRef)


def test_transform_provenance_generated_at_time():
    """prov:generatedAtTime 트리플이 event.timestamp를 포함."""
    transformer = RDFTransformer()
    triples = transformer.transform(make_event(), make_source())
    prov_triple = next(
        (t for t in triples if str(t.predicate) == PROV_GENERATED_AT_TIME),
        None,
    )
    assert prov_triple is not None
    assert "2026-03-25" in str(prov_triple.object_)


def test_transform_provenance_was_attributed_to():
    """prov:wasAttributedTo 트리플이 event.source_id를 포함."""
    transformer = RDFTransformer()
    triples = transformer.transform(make_event(), make_source())
    attr_triple = next(
        (t for t in triples if str(t.predicate) == PROV_WAS_ATTRIBUTED_TO),
        None,
    )
    assert attr_triple is not None
    assert str(attr_triple.object_) == "src-001"


def test_transform_skips_missing_template_key():
    """템플릿 키가 없는 레코드는 건너뜀 → 빈 결과."""
    transformer = RDFTransformer()
    event = SourceEvent(
        source_id="src-001",
        ontology_id="ont-001",
        event_type="upsert",
        timestamp="2026-03-25T00:00:00Z",
        records=[{"wrong_key": "val"}],
    )
    triples = transformer.transform(event, make_source())
    assert triples == []


def test_transform_multiple_records():
    """여러 레코드 → 각 레코드별 triple 생성."""
    transformer = RDFTransformer()
    event = SourceEvent(
        source_id="src-001",
        ontology_id="ont-001",
        event_type="upsert",
        timestamp="2026-03-25T00:00:00Z",
        records=[{"emp_id": "1"}, {"emp_id": "2"}],
    )
    triples = transformer.transform(event, make_source())
    subjects = {str(t.subject) for t in triples}
    assert "https://example.org/emp/1" in subjects
    assert "https://example.org/emp/2" in subjects


def test_transform_skips_none_property_value():
    """매핑된 필드가 None이면 해당 Property 트리플 미생성."""
    mapping = PropertyMapping(source_field="name", property_iri=NAME_PROP)
    transformer = RDFTransformer()
    records = [{"emp_id": "1"}]  # name 필드 없음
    triples = transformer.transform(make_event(records), make_source(mappings=[mapping]))
    name_triples = [t for t in triples if str(t.predicate) == NAME_PROP]
    assert name_triples == []


def test_build_named_graph_iri():
    """urn:source:{source_id}/{timestamp} 형식."""
    iri = build_named_graph_iri("src-001", "2026-03-25T00:00:00Z")
    assert iri == "urn:source:src-001/2026-03-25T00:00:00Z"
