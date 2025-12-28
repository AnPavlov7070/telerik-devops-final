from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    IMAP_HOST: str = Field(..., description="IMAP server hostname")
    IMAP_PORT: int = Field(993, description="IMAP server port")
    IMAP_SSL: bool = Field(True, description="Use SSL for IMAP (true/false)")
    IMAP_USERNAME: str = Field(..., description="IMAP username")
    IMAP_PASSWORD: str = Field(..., description="IMAP password")
    IMAP_FOLDER: str = Field("INBOX", description="IMAP folder to read")
    STATE_PATH: str = Field("./state/state.json", description="Path to state JSON")

    model_config = SettingsConfigDict(
        env_file=".env",        # load variables from .env
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
