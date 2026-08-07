from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_api_key: str = ""
    database_path: str = "data/receipts.db"
    auth_username: str = ""
    auth_password_hash: str = ""
    session_secret_key: str = ""
    api_token: str = ""


settings = Settings()

