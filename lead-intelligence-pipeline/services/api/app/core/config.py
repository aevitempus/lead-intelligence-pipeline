from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: str = "local"
    database_url: str
    redis_url: str
    openai_api_key: str | None = None
    ai_model: str = "gpt-4.1-mini"
    crawler_api_token: str = "change-me"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
