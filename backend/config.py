"""
config.py — 환경변수 기반 앱 설정

pydantic BaseSettings를 사용하여 환경변수를 로드하고 타입 검증을 수행한다.
.env 파일을 자동으로 읽으며, 환경변수가 없을 경우 기본값을 사용한다.
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    앱 전역 설정.

    구현 세부사항:
    - 각 필드는 환경변수명과 매핑된다 (대소문자 무시)
    - docker-compose.yml의 environment 블록과 일치해야 한다
    - 운영 환경에서는 .env 파일 대신 실제 환경변수 주입 권장
    """

    # Neo4j 연결 설정
    neo4j_uri: str = Field(default="bolt://neo4j:7687", description="Neo4j Bolt URI")
    neo4j_user: str = Field(default="neo4j", description="Neo4j 사용자명")
    neo4j_password: str = Field(default="password", description="Neo4j 비밀번호")

    # Kafka 브로커
    kafka_brokers: str = Field(
        default="kafka:9092",
        description="Kafka 브로커 주소 (쉼표 구분 복수 브로커 가능)",
    )

    # Oxigraph 영구 저장소 경로
    oxigraph_path: str = Field(
        default="/data/oxigraph",
        description="Oxigraph 파일 시스템 경로. None이면 인메모리 사용 (테스트용)",
    )

    # SPARQL 타임아웃
    sparql_timeout_seconds: int = Field(
        default=30,
        description="SPARQL 쿼리 최대 실행 시간 (초)",
    )

    # Oxigraph → Neo4j 동기화 주기
    sync_interval_seconds: int = Field(
        default=300,
        description="ABox 동기화 주기 (초). 기본 5분",
    )

    # Neo4j 배치 INSERT 크기
    sync_batch_size: int = Field(
        default=1000,
        description="UNWIND + MERGE Cypher 배치 크기",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 싱글톤 설정 인스턴스 — 앱 전체에서 import하여 사용
settings = Settings()
