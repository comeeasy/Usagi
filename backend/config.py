"""
config.py — 환경변수 기반 앱 설정
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Jena Fuseki
    fuseki_url: str = Field(default="http://fuseki:3030")
    fuseki_dataset: str = Field(default="ontology")

    # Kafka
    kafka_brokers: str = Field(default="kafka:9092")

    # SPARQL 타임아웃
    sparql_timeout_seconds: int = Field(default=30)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def kafka_broker_list(self) -> list[str]:
        return [b.strip() for b in self.kafka_brokers.split(",")]


settings = Settings()
