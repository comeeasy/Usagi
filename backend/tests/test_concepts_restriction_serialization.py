"""
tests/test_concepts_restriction_serialization.py

EBUG-1: hasValue restriction 직렬화가 literal/IRI를 올바르게 구분하는지 검증.
"""
from __future__ import annotations

from api.concepts import _restriction_triples
from models.concept import PropertyRestriction


def test_has_value_literal_serialized_as_literal() -> None:
    triples = _restriction_triples(
        "https://test.example.org/onto#Person",
        [
            PropertyRestriction(
                property_iri="https://test.example.org/onto#status",
                type="hasValue",
                value="active",
            )
        ],
    )
    assert 'owl:hasValue "active" .' in triples


def test_has_value_iri_serialized_as_iri() -> None:
    triples = _restriction_triples(
        "https://test.example.org/onto#Person",
        [
            PropertyRestriction(
                property_iri="https://test.example.org/onto#hasRole",
                type="hasValue",
                value="https://test.example.org/onto#Admin",
            )
        ],
    )
    assert "owl:hasValue <https://test.example.org/onto#Admin> ." in triples
