from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/billcheck"
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    UPLOAD_DIR: str = "/app/.uploads"

    class Config:
        env_file = ".env"


settings = Settings()
