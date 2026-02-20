from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "Library Management Service"
    API_V1_STR: str = "/api/v1"

    POSTGRES_SERVER: Optional[str] = "localhost"
    POSTGRES_USER: Optional[str] = "user"
    POSTGRES_PASSWORD: Optional[str] = "password"
    POSTGRES_DB: Optional[str] = "library"
    POSTGRES_PORT: int = 5432

    # Business Logic Config
    MAX_ACTIVE_BORROWS: int = 5
    DEFAULT_BORROW_DURATION_DAYS: int = 14

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        if not self.POSTGRES_SERVER:
            return "sqlite:///./test.db"
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )


settings = Settings()
