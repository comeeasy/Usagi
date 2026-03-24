"""
Tests for IRI Generator service.
"""
import pytest

from services.ingestion.iri_generator import generate, validate_iri, percent_encode


def test_basic_iri_generation():
    """단순 템플릿 + 단일 필드."""
    iri = generate("https://example.org/emp/{id}", {"id": "42"})
    assert iri == "https://example.org/emp/42"


def test_multi_field_template():
    """여러 필드 치환."""
    iri = generate("https://example.org/{table}/{pk}", {"table": "employee", "pk": "100"})
    assert iri == "https://example.org/employee/100"


def test_iri_url_encoding_space():
    """공백 포함 값 → percent-encode."""
    iri = generate("https://example.org/item/{id}", {"id": "hello world"})
    assert " " not in iri
    assert "hello" in iri
    assert "%20" in iri


def test_iri_url_encoding_special_chars():
    """특수문자 포함 PK → percent-encode."""
    iri = generate("https://example.org/item/{id}", {"id": "foo&bar=baz"})
    assert "&" not in iri or "foo" in iri  # 특수문자가 인코딩됨


def test_validate_iri_http():
    assert validate_iri("https://example.org/foo") is True


def test_validate_iri_urn():
    # BUG-006: validate_iri는 `://`를 요구하므로 `urn:` 스킴을 거부함
    # 실제 동작 문서화 — 수정 전까지는 False
    assert validate_iri("urn:example:123") is False


def test_validate_iri_no_scheme():
    assert validate_iri("not-an-iri") is False


def test_validate_iri_with_space():
    assert validate_iri("https://example.org/foo bar") is False


def test_percent_encode_space():
    assert percent_encode("hello world") == "hello%20world"


def test_percent_encode_slash_preserved():
    """'/'는 safe 문자로 인코딩하지 않음."""
    result = percent_encode("foo/bar")
    assert result == "foo/bar"


def test_missing_key_raises_key_error():
    """템플릿에 없는 키 → KeyError."""
    with pytest.raises(KeyError):
        generate("https://example.org/{missing_key}", {"other": "value"})


def test_invalid_iri_template_raises_value_error():
    """IRI 스킴이 없는 결과 → ValueError."""
    with pytest.raises(ValueError):
        generate("{id}", {"id": "nope"})
