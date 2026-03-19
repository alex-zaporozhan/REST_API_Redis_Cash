from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str
    REDIS_URL: str

    POST_CACHE_TTL_SECONDS: int = 60
    POST_CACHE_PREFIX: str = "posts:dev"


settings = Settings()

