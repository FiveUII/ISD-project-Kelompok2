"""
Application configuration using pydantic-settings.
Reads from environment variables or .env file.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/library"
    ALLOWED_ORIGINS: str = "http://localhost,http://localhost:5173"
    JWT_SECRET: str = "changeme-never-commit-real-secret"
    ADMIN_EMAIL: str = "admin@library.local"
    ADMIN_PASSWORD: str = "changeme-set-in-env"

    model_config = {"env_file": ".env", "case_sensitive": True}

    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse the comma-separated ALLOWED_ORIGINS string into a list."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]


settings = Settings()
