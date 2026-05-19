from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    public_data_service_key: str | None = None
    public_data_base_url: str = "https://api.odcloud.kr/api"
    checkup_dataset_path: str = "/15007122/v1/uddi:4be8523e-2fd4-457d-a594-ac1fbba444b5"
    checkup_group_dataset_path: str = "/15144521/v1/uddi:281e8b27-402b-48db-85d9-d5410a73ce07"
    use_demo_data: bool = True
    request_timeout_seconds: float = 8.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8-sig",
        extra="ignore",
    )

    @property
    def has_public_data_key(self) -> bool:
        return bool(self.public_data_service_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
