from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Library Management Service"
    API_V1_STR: str = "/api/v1"

    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "user"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "library"
    POSTGRES_PORT: int = 5432
    POSTGRES_URL: str | None = None

    # Business Logic Config
    MAX_ACTIVE_BORROWS: int = 5
    DEFAULT_BORROW_DURATION_DAYS: int = 14
    SEEDING_SECRET: str = "change-me-in-production"

    @property
    def DATABASE_URL(self) -> str:
        if self.POSTGRES_URL:
            # Handles Vercel/Supabase style URLs, replacing legacy postgres:// if present
            return self.POSTGRES_URL.replace("postgres://", "postgresql://", 1)
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )


settings = Settings()
