"""
IRI Generator — IRI 생성 전략
"""
from __future__ import annotations

import re
from urllib.parse import quote

# TODO: rfc3986 검증 라이브러리 선택 (rfc3986 패키지 또는 수동 구현)


def generate(template: str, record: dict) -> str:
    """
    "{template}".format(**record) 로 IRI 생성.
    예: "https://ex.org/emp/{emp_id}" + {"emp_id": 42} → "https://ex.org/emp/42"

    Args:
        template: IRI 템플릿 문자열 (Python format string)
        record: 템플릿 치환에 사용할 딕셔너리

    Returns:
        str: 생성된 IRI

    Raises:
        KeyError: 템플릿의 플레이스홀더가 record에 없을 때
        ValueError: 생성된 IRI가 유효하지 않을 때
    """
    # TODO: implement
    # iri = template.format(**record)
    # if not validate_iri(iri):
    #     raise ValueError(f"Generated IRI is invalid: {iri}")
    # return iri
    raise NotImplementedError


def validate_iri(iri: str) -> bool:
    """
    rfc3986 규격 검증, 공백/특수문자 포함 시 percent-encode.

    Args:
        iri: 검증할 IRI 문자열

    Returns:
        bool: 유효한 IRI이면 True
    """
    # TODO: implement
    # RFC 3986 기본 검증: scheme://authority/path 형식 확인
    # _IRI_PATTERN = re.compile(r'^[a-zA-Z][a-zA-Z0-9+\-.]*://')
    # if not _IRI_PATTERN.match(iri):
    #     return False
    # if ' ' in iri:
    #     return False
    # return True
    raise NotImplementedError


def percent_encode(value: str) -> str:
    """
    IRI 내 공백 및 특수문자를 percent-encode.

    Args:
        value: 인코딩할 문자열

    Returns:
        str: percent-encoded 문자열
    """
    # TODO: implement
    # return quote(value, safe=':/?#[]@!$&\'()*+,;=-._~')
    raise NotImplementedError
