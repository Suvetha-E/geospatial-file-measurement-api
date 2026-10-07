from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Geospatial File Measurement API"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    
    # Database
    DATABASE_URL: str = "sqlite:///./geospatial.db"
    
    # File Storage
    UPLOAD_DIRECTORY: Path = Path("./uploads")
    TEMP_DIRECTORY: Path = Path("./temp")
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50 MB
    
    # Configuration model settings
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def setup_directories(self) -> None:
        """Ensure upload and temp directories exist."""
        self.UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)
        self.TEMP_DIRECTORY.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.setup_directories()
