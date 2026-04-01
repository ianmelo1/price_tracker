# price_tracker/scrapers/base_scraper.py

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from config import config

logger = logging.getLogger(__name__)


@dataclass
class PriceResult:
    """Resultado padronizado de qualquer scraper."""
    product_id: int
    price: Optional[float]
    available: bool
    store: str


class BaseScraper(ABC):
    """Contrato base para todos os scrapers."""

    store_name: str = ""

    def __init__(self) -> None:
        self.headers = {"User-Agent": config.user_agent}

    # -- obrigatório implementar nas subclasses
    @abstractmethod
    def fetch_price(self, product_id: int, url: str) -> PriceResult:
        ...

    # -- pausa entre requests para respeitar rate limit
    def _wait(self) -> None:
        time.sleep(config.request_delay_seconds)

    # -- loga erro sem deixar a aplicação cair
    def _safe_error(self, url: str, exc: Exception) -> PriceResult:
        logger.error("[%s] Falha ao buscar %s:", self.store_name, url, exc_info=True)
        return PriceResult(product_id=0, price=None, available=False, store=self.store_name)