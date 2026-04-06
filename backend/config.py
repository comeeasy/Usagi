"""
config.py — 환경변수 기반 앱 설정
"""

import httpx
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Jena Fuseki
    fuseki_url: str = Field(default="http://fuseki:3030")
    fuseki_dataset: str = Field(default="ontology")
    # stain/jena-fuseki shiro: UPDATE/GSP/Admin API need Basic auth (user admin, password = ADMIN_PASSWORD in compose)
    fuseki_user: str = Field(default="admin")
    fuseki_password: str = Field(default="")

    def fuseki_basic_auth(self) -> httpx.Auth | None:
        if not self.fuseki_password:
            return None
        return httpx.BasicAuth(self.fuseki_user, self.fuseki_password)

    # Kafka
    kafka_brokers: str = Field(default="kafka:9092")

    # SPARQL 타임아웃
    sparql_timeout_seconds: int = Field(default=30)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def kafka_broker_list(self) -> list[str]:
        return [b.strip() for b in self.kafka_brokers.split(",")]


settings = Settings()
