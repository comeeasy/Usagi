"""
services/merge_service.py — 온톨로지 Merge 로직 + 충돌 감지

병합 전략:
  - TBox(스키마) 병합만 지원 (ABox는 Provenance로 관리)
  - 충돌 감지: 동일 IRI의 rdfs:label, rdfs:domain, rdfs:range, rdfs:subClassOf 비교
  - 충돌 해결: keep-target / keep-source / merge-both 선택 적용
"""

from typing import Any

# from services.ontology_store import OntologyStore
# from services.sync_service import SyncService
# from api.merge import ConflictItem, ConflictResolution


class MergeService:
    """온톨로지 병합 서비스."""

    def __init__(self, ontology_store: Any, sync_service: Any):
        """
        구현 세부사항:
        - self._store = ontology_store
        - self._sync = sync_service
        """
        pass

    async def detect_conflicts(
        self,
        target_id: str,
        source_id: str,
    ) -> dict:
        """
        병합 충돌 감지.

        구현 세부사항:
        1. target TBox에서 모든 owl:Class, owl:ObjectProperty, owl:DatatypeProperty IRI 조회
        2. source TBox에서 동일 타입의 IRI 목록 조회
        3. 공통 IRI 집합: set(target_iris) & set(source_iris)
        4. 공통 IRI 각각에 대해:
           a. rdfs:label 비교 → 다르면 ConflictItem(type="label")
           b. rdfs:domain 목록 비교 → 다르면 ConflictItem(type="domain")
           c. rdfs:range 목록 비교 → 다르면 ConflictItem(type="range")
           d. rdfs:subClassOf 목록 비교 → 다르면 ConflictItem(type="superClass")
        5. 자동 병합 가능: source에만 있는 새 IRI 수 계산
        6. 반환:
           {
             conflicts: [ConflictItem, ...],
             auto_mergeable_count: int,
             total_source_entities: int
           }
        """
        pass

    async def merge(
        self,
        target_id: str,
        source_id: str,
        resolutions: list[Any],
    ) -> None:
        """
        온톨로지 병합 실행.

        구현 세부사항:
        1. resolutions를 { (iri, conflictType): choice } 딕셔너리로 인덱싱
        2. source TBox의 모든 트리플 순회:
           a. 충돌 없는 새 엔티티: target TBox에 직접 삽입 (자동 병합)
           b. 충돌 있는 트리플:
              - keep-target: 스킵 (target 값 유지)
              - keep-source: target에서 기존 값 삭제 후 source 값 삽입
              - merge-both: 기존 값 유지 + source 값 추가 삽입 (복수 허용)
        3. owl:imports 트리플 처리: source ontology의 imports를 target에 추가
        4. SPARQL UPDATE 배치로 일괄 처리 (성능)
        5. await self._sync.trigger_tbox_sync(target_id) 호출
        """
        pass

    def _compare_literal_lists(self, a: list[str], b: list[str]) -> bool:
        """
        두 리터럴/IRI 목록이 다른지 비교.

        구현 세부사항:
        - 집합 비교: set(a) != set(b)
        - 빈 리스트와 None은 동일 처리
        """
        pass
