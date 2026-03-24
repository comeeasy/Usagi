"""IRI Generator — IRI 생성 전략"""
from urllib.parse import quote
import re

_IRI_SCHEME = re.compile(r'^[a-zA-Z][a-zA-Z0-9+\-.]*://')


def generate(template: str, record: dict) -> str:
    """{template}.format(**record) 로 IRI 생성."""
    # percent-encode each value before substituting
    encoded = {k: percent_encode(str(v)) for k, v in record.items()}
    iri = template.format(**encoded)
    if not validate_iri(iri):
        raise ValueError(f"Generated IRI is invalid: {iri}")
    return iri


def validate_iri(iri: str) -> bool:
    return bool(_IRI_SCHEME.match(iri)) and ' ' not in iri


def percent_encode(value: str) -> str:
    return quote(value, safe=':/?#[]@!$&\'()*+,;=-._~')
