"""
config.py — 환경변수 기반 앱 설정
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Neo4j
    neo4j_uri: str = Field(default="bolt://neo4j:7687")
    neo4j_user: str = Field(default="neo4j")
    neo4j_password: str = Field(default="password")

    # Kafka
    kafka_brokers: str = Field(default="kafka:9092")

    # Oxigraph
    oxigraph_path: str = Field(default="/data/oxigraph")

    # SPARQL 타임아웃
    sparql_timeout_seconds: int = Field(default=30)

    # Oxigraph → Neo4j 동기화
    sync_interval_seconds: int = Field(default=300)
    sync_batch_size: int = Field(default=1000)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def kafka_broker_list(self) -> list[str]:
        return [b.strip() for b in self.kafka_brokers.split(",")]


settings = Settings()
