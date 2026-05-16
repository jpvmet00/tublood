from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./tublood.db"
    data_dir: Path = Path("./data")
    openai_api_key: str = ""

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    n8n_webhook_url: str = "http://localhost:5678/webhook/tublood"

    cooldown_dias: int = 7
    mora_minima: int = 1
    tolerance_pct: float = 0.10


settings = Settings()
