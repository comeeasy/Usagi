"""
api/import_.py — 온톨로지 파일/URL Import 라우터

엔드포인트:
  POST /ontologies/{id}/import/file       OWL/TTL/RDF/JSON-LD 파일 업로드
  POST /ontologies/{id}/import/url        URL에서 온톨로지 가져오기
  POST /ontologies/{id}/import/standard   사전 등록 온톨로지 임포트
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Literal

from models.reasoner import JobResponse

router = APIRouter(
    prefix="/ontologies/{ontology_id}/import",
    tags=["import"],
)

# 사전 등록 온톨로지 URL 매핑
STANDARD_ONTOLOGIES: dict[str, str] = {
    "schema.org": "https://schema.org/version/latest/schemaorg-current-https.ttl",
    "foaf": "http://xmlns.com/foaf/spec/index.rdf",
    "dc": "https://www.dublincore.org/specifications/dublin-core/dcmi-terms/dublin_core_terms.ttl",
    "skos": "https://www.w3.org/2009/08/skos-reference/skos.rdf",
    "owl": "https://www.w3.org/2002/07/owl",
    "rdfs": "https://www.w3.org/2000/01/rdf-schema",
}


class ImportURLRequest(BaseModel):
    url: str


class ImportStandardRequest(BaseModel):
    name: Literal["schema.org", "foaf", "dc", "skos", "owl", "rdfs"]


@router.post("/file", response_model=JobResponse, status_code=202)
async def import_file(
    ontology_id: str,
    file: UploadFile = File(...),
) -> JobResponse:
    """
    OWL/TTL/RDF/JSON-LD 파일 업로드 임포트.

    구현 세부사항:
    - file.content_type으로 MIME 타입 확인
    - 지원 형식: text/turtle, application/rdf+xml, application/ld+json, application/n-triples
    - file.read()로 바이트 읽기 (최대 100MB — Nginx client_max_body_size와 일치)
    - asyncio.create_task(ImportService.import_from_bytes(ontology_id, data, mime_type))
      백그라운드 태스크로 실행 (대용량 파일 타임아웃 방지)
    - job_id 생성 후 즉시 JobResponse(status="pending") 반환
    """
    pass


@router.post("/url", response_model=JobResponse, status_code=202)
async def import_url(ontology_id: str, body: ImportURLRequest) -> JobResponse:
    """
    URL에서 온톨로지 다운로드 + 임포트.

    구현 세부사항:
    - httpx.AsyncClient(follow_redirects=True) 로 URL 다운로드
    - response.headers["content-type"]으로 MIME 타입 감지
    - ImportService.import_from_bytes(ontology_id, content, mime_type) 호출
    - 다운로드 타임아웃: 60초
    - HTTP 오류(4xx/5xx): HTTPException(400, code="IMPORT_URL_FETCH_FAILED")
    - 비동기 Job으로 실행, JobResponse 반환
    """
    pass


@router.post("/standard", response_model=JobResponse, status_code=202)
async def import_standard(ontology_id: str, body: ImportStandardRequest) -> JobResponse:
    """
    사전 등록 온톨로지 임포트.

    구현 세부사항:
    - STANDARD_ONTOLOGIES[body.name]으로 URL 조회
    - import_url 로직 재사용 (내부 함수 호출)
    - 결과: JobResponse 반환
    """
    pass
