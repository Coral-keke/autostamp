"""
Auto-Stamp System Configuration
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings, loaded from environment variables."""

    # Project paths
    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
    BACKEND_DIR: Path = Path(__file__).resolve().parent
    SEAL_STORAGE: Path = BACKEND_DIR / "storage" / "seals"
    UPLOAD_DIR: Path = BACKEND_DIR / "uploads"
    OUTPUT_DIR: Path = BACKEND_DIR / "output"
    TEMP_DIR: Path = BACKEND_DIR / "temp"  # Downloaded files

    # Seal constraints
    MAX_SEAL_SIZE_MB: int = 5
    ALLOWED_SEAL_FORMATS: list[str] = ["png", "jpg", "jpeg", "svg"]

    # File constraints
    MAX_FILE_SIZE_MB: int = 100
    ALLOWED_INPUT_FORMATS: list[str] = ["pdf", "dwg", "png", "jpg", "jpeg", "bmp", "tiff", "tif", "docx", "xlsx"]
    ALLOWED_OUTPUT_FORMATS: list[str] = ["pdf", "dwf", "dwg", "png", "jpg", "docx", "xlsx"]

    # File download
    DOWNLOAD_TIMEOUT: int = 60  # seconds
    DOWNLOAD_MAX_SIZE_MB: int = 100

    # Callback
    CALLBACK_TIMEOUT: int = 30
    CALLBACK_RETRY_COUNT: int = 3
    CALLBACK_RETRY_DELAY: int = 5  # seconds between retries

    # HMAC signing for callbacks
    HMAC_SECRET: str = ""  # Set via env STAMP_HMAC_SECRET

    # ODA File Converter
    ODA_CONVERTER_PATH: str = str(Path(__file__).resolve().parent.parent.parent / ".local" / "oda" / "ODAFileConverter")

    # Coordinate system
    DEFAULT_DPI: int = 72
    MM_TO_PT: float = 72.0 / 25.4  # 1 mm = 2.8346 points

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Base URL for generating download links in callbacks
    BASE_URL: str = "http://localhost:8000"

    # API Key authentication
    API_KEY: str = ""  # Set via env STAMP_API_KEY. Empty = no auth required.
    API_KEY_HEADER: str = "X-API-Key"

    # Concurrency
    MAX_CONCURRENT_JOBS: int = 10  # Max simultaneous background stamp tasks

    # Web UI authentication
    WEB_PASSWORD: str = "autostamp"  # Set via env STAMP_WEB_PASSWORD
    WEB_TOKEN_SECRET: str = "change-me-in-production"  # Set via env STAMP_WEB_TOKEN_SECRET

    class Config:
        env_prefix = "STAMP_"
        env_file = ".env"
        extra = "allow"


settings = Settings()

# Ensure directories exist
for d in [settings.SEAL_STORAGE, settings.UPLOAD_DIR, settings.OUTPUT_DIR, settings.TEMP_DIR]:
    d.mkdir(parents=True, exist_ok=True)
