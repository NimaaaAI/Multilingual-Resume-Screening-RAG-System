from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    redis_url: str
    llm_api_key: str = ""
    llm_base_url: str = "https://api.gapgpt.app/v1"
    llm_model: str = "gpt-4o-mini"


settings = Settings()
