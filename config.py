# price_tracker/config.py
"""Configurações centrais carregadas via variáveis de ambiente."""

import os
import logging
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


@dataclass(frozen=True)
class Config:
    database_url: str
    discord_webhook_url: str
    mercadolivre_app_id: str
    mercadolivre_secret: str
    check_interval_minutes: int
    request_delay_seconds: float = 2.0
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )


def load_config() -> Config:
    """Carrega e valida as variáveis de ambiente obrigatórias."""
    required = {
        "DATABASE_URL": os.getenv("DATABASE_URL"),
        "DISCORD_WEBHOOK_URL": os.getenv("DISCORD_WEBHOOK_URL"),
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        raise ValueError(f"Variáveis de ambiente ausentes: {missing}")

    return Config(
        database_url=required["DATABASE_URL"],
        discord_webhook_url=required["DISCORD_WEBHOOK_URL"],
        mercadolivre_app_id=os.getenv("MERCADOLIVRE_APP_ID", ""),
        mercadolivre_secret=os.getenv("MERCADOLIVRE_SECRET", ""),
        check_interval_minutes=int(os.getenv("CHECK_INTERVAL_MINUTES", "60")),
    )


config = load_config()