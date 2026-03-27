# price_tracker/scrapers/kabum.py

import logging
import requests
from bs4 import BeautifulSoup

from scrapers.base_scraper import BaseScraper, PriceResult

logger = logging.getLogger(__name__)


class KabumScraper(BaseScraper):
    """Scraper da KaBuM usando requests + BeautifulSoup."""

    store_name = "kabum"

    def fetch_price(self, product_id: int, url: str) -> PriceResult:
        """Busca o preço atual de um produto na KaBuM."""
        try:
            self._wait()
            response = self._get(url)
            return self._parse(product_id, response.text)
        except Exception as exc:
            return self._safe_error(url, exc)

    def _get(self, url: str) -> requests.Response:
        """Faz o request e valida o status HTTP."""
        response = requests.get(url, headers=self.headers, timeout=15)
        response.raise_for_status()
        return response

    def _parse(self, product_id: int, html: str) -> PriceResult:
        """Extrai preço e disponibilidade do HTML."""
        soup = BeautifulSoup(html, "html.parser")
        price = self._extract_price(soup)
        available = self._extract_availability(soup)
        if price is None:
            logger.warning("[kabum] Preço não encontrado para product_id=%s", product_id)
        return PriceResult(
            product_id=product_id,
            price=price,
            available=available,
            store=self.store_name,
        )

    def _extract_price(self, soup: BeautifulSoup) -> float | None:
        """Localiza e converte o preço para float."""
        tag = soup.select_one("h4.text-4xl")
        if not tag:
            return None
        raw = tag.get_text(strip=True)
        clean = (
            raw.replace("R$", "")
            .replace("\xa0", "")
            .replace(".", "")
            .replace(",", ".")
            .strip()
        )
        try:
            return float(clean)
        except ValueError:
            return None

    def _extract_availability(self, soup: BeautifulSoup) -> bool:
        """Verifica se o produto está disponível."""
        esgotado = soup.find("span", string=lambda t: t and "esgotado" in t.lower())
        return esgotado is None