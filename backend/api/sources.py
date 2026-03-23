"""
api/sources.py — Backing Source 관리 + 수동 Sync 라우터

엔드포인트:
  GET    /ontologies/{id}/sources                      Backing Source 목록
  POST   /ontologies/{id}/sources                      새 Backing Source 등록
  GET    /ontologies/{id}/sources/{source_id}          Source 상세
  PUT    /ontologies/{id}/sources/{source_id}          Source 설정 수정
  DELETE /ontologies/{id}/sources/{source_id}          Source 삭제
  POST   /ontologies/{id}/sources/{source_id}/sync     수동 즉시 동기화 트리거
"""

from fastapi import APIRouter, HTTPException

from models.source import BackingSource, BackingSourceCreate
from models.reasoner import JobResponse

router = APIRouter(
    prefix="/ontologies/{ontology_id}/sources",
    tags=["sources"],
)


@router.get("", response_model=list[BackingSource])
async def list_sources(ontology_id: str) -> list[BackingSource]:
    """
    Backing Source 목록 조회.

    구현 세부사항:
    - 인메모리 source_store 또는 Oxigraph prov Named Graph에서 조회
    - 각 소스의 status, lastSyncAt 포함
    - ontology_id 필터링
    """
    pass


@router.post("", response_model=BackingSource, status_code=201)
async def create_source(ontology_id: str, body: BackingSourceCreate) -> BackingSource:
    """
    새 Backing Source 등록.

    구현 세부사항:
    - source_id = str(uuid4())
    - body.sourceType에 따라 config 유효성 검증:
      - "jdbc": JDBCConfig 필드 검증 (jdbcUrl 형식 등)
      - "api-rest": APIConfig.url 유효성 검증
      - "api-stream": StreamConfig.kafkaBrokers 형식 검증
    - BackingSource 저장 (인메모리 또는 Oxigraph 메타데이터 Named Graph)
    - status="active"로 초기화
    - 생성된 BackingSource 반환
    """
    pass


@router.get("/{source_id}", response_model=BackingSource)
async def get_source(ontology_id: str, source_id: str) -> BackingSource:
    """
    Source 상세 + 마지막 동기화 상태 조회.

    구현 세부사항:
    - source_store에서 source_id로 조회
    - 없거나 ontology_id 불일치 시 HTTPException(404)
    - lastSyncAt, status 최신 값 포함
    """
    pass


@router.put("/{source_id}", response_model=BackingSource)
async def update_source(ontology_id: str, source_id: str, body: BackingSourceCreate) -> BackingSource:
    """
    Source 설정 수정.

    구현 세부사항:
    - 기존 source 조회 후 body의 변경된 필드 업데이트
    - config 타입이 변경되면 기존 config 전체 교체
    - 수정된 BackingSource 반환
    """
    pass


@router.delete("/{source_id}", status_code=204)
async def delete_source(ontology_id: str, source_id: str) -> None:
    """
    Source 삭제.

    구현 세부사항:
    - source_store에서 삭제
    - 주의: 해당 소스가 수집한 Triple은 보존 (Named Graph는 유지)
      → Provenance 이력 보존을 위해 데이터 자체는 삭제하지 않음
    - 단, 이후 이 소스의 새 수집은 중단됨
    - 204 반환
    """
    pass


@router.post("/{source_id}/sync", response_model=JobResponse, status_code=202)
async def trigger_sync(ontology_id: str, source_id: str) -> JobResponse:
    """
    수동 즉시 동기화 트리거.

    구현 세부사항:
    - source 존재 여부 확인
    - SyncService.trigger_source_sync(source_id) 호출
      → Kafka Producer로 sync-commands 토픽에 { source_id, triggered_at, trigger_type: "manual" } 발행
    - job_id 생성 후 JobResponse(status="pending") 반환
    """
    pass
