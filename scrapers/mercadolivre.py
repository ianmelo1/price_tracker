# price_tracker/scrapers/mercadolivre.py

import logging
import requests

from scrapers.base_scraper import BaseScraper, PriceResult
from config import config

logger = logging.getLogger(__name__)

ML_API = "https://api.mercadolivre.com/items"


class MercadoLivreScraper(BaseScraper):
    """Busca preços via API oficial do Mercado Livre."""

    store_name = "mercadolivre"

    def fetch_price(self, product_id: int, url: str) -> PriceResult:
        """Busca o preço atual de um produto no Mercado Livre."""
        try:
            self._wait()
            item_id = self._extract_item_id(url)
            data = self._get(item_id)
            return self._parse(product_id, data)
        except Exception as exc:
            return self._safe_error(url, exc)

    # -- extrai o ID do item da URL (ex: MLB3123456789)
    def _extract_item_id(self, url: str) -> str:
        for part in url.split("/"):
            if part.upper().startswith("MLB"):
                return part.split("-")[0].upper()
        raise ValueError(f"ID do item não encontrado na URL: {url}")

    # -- consulta a API e retorna o JSON
    def _get(self, item_id: str) -> dict:
        response = requests.get(
            f"{ML_API}/{item_id}",
            headers=self.headers,
            timeout=15,
        )
        response.raise_for_status()
        return response.json()

    # -- extrai preço e disponibilidade do JSON
    def _parse(self, product_id: int, data: dict) -> PriceResult:
        price = data.get("price") or data.get("original_price")
        status = data.get("status", "")
        available = status == "active"

        if price is None:
            logger.warning("[mercadolivre] Preço não encontrado para product_id=%s", product_id)

        return PriceResult(
            product_id=product_id,
            price=float(price) if price else None,
            available=available,
            store=self.store_name,
        )