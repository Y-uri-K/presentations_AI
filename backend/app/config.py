from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_database: str = "presentations_ai"

    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 7

    verification_code_expire_minutes: int = 15
    pending_registration_expire_minutes: int = 30
    email_send_cooldown_seconds: int = 60

    cors_origins: str = "http://localhost:3000"

    email_dev_mode: bool = True
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@example.com"
    smtp_use_tls: bool = True

    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "llama3.2"
    ollama_timeout_seconds: int = 120

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    gemini_timeout_seconds: int = 120

    polza_api_key: str = ""
    polza_base_url: str = "https://polza.ai/api/v1"
    polza_image_model: str = "google/gemini-2.5-flash-image"
    polza_chat_model: str = "google/gemini-3.5-flash"
    polza_chat_timeout_seconds: int = 120
    polza_image_timeout_seconds: int = 180
    polza_image_poll_interval_seconds: float = 4.0

    mimi_api_key: str = ""
    mimi_base_url: str = "https://api.xiaomimimo.com/v1"
    mimi_model: str = "mimo-v2.5-pro"
    mimi_timeout_seconds: int = 300

    template_max_size_mb: int = 25
    template_max_count_per_user: int = 50

    presentation_source_max_size_mb: int = 10
    presentation_source_max_files: int = 5
    presentation_default_agent: str = "gemini"
    presentation_max_slides: int = 10
    presentation_max_generated_images: int = 4
    presentation_source_enrichment: bool = True
    presentation_template_ai_analysis: bool = True
    presentation_pptx_max_size_mb: int = 50
    presentation_use_gamma_pipeline: bool = True
    presentation_use_template_driven: bool = True
    presentation_blueprint_llm_phase2: bool = False
    presentation_blueprint_use_llm: bool = False
    presentation_blueprint_use_polza: bool = True
    presentation_language: str = "Русский"
    presentation_tone: str = "деловой"
    presentation_text_content: str = "concise"
    presentation_audience: str = "широкая аудитория"
    presentation_scenario: str = "бизнес-презентация"

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
