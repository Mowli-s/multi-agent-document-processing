from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    azure_document_intelligence_endpoint: str
    azure_document_intelligence_key: str

    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_deployment: str

    azure_storage_connection_string: str

    azure_storage_input_container: str = "input"
    azure_storage_output_container: str = "processed"
    azure_storage_report_container: str = "reports"

    confidence_threshold: float = 0.80

    max_retries: int = 3
    retry_min_seconds: int = 1
    retry_max_seconds: int = 8

    log_level: str = "INFO"
    error_notification_webhook_url: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
