from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    app_host: str = "127.0.0.1"
    app_port: int = 8765
    data_dir: Path = Path("./data")
    max_upload_mb: int = 500
    default_dpi: int = 240
    ocrmypdf_timeout_sec: int = Field(default=7200, validation_alias="OCRMY_PDF_TIMEOUT_SEC")
    mineru_timeout_sec: int = Field(default=14400, validation_alias="MINERU_TIMEOUT_SEC")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
