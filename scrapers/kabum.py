# price_tracker/scrapers/kabum.py

import json
import logging
import subprocess
import sys
from pathlib import Path

from scrapers.base_scraper import BaseScraper, PriceResult

logger = logging.getLogger(__name__)

# Caminho absoluto do worker — funciona independente de onde o processo é iniciado
_WORKER = Path(__file__).parent / "_kabum_worker.py"


class KabumScraper(BaseScraper):
    store_name = "kabum"

    def fetch_price(self, product_id: int, url: str) -> PriceResult:
        try:
            self._wait()
            return self._scrape(product_id, url)
        except Exception as exc:
            return self._safe_error(product_id, url, exc)

    def _scrape(self, product_id: int, url: str) -> PriceResult:
        result = subprocess.run(
            [sys.executable, str(_WORKER), url, self.headers["User-Agent"]],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"Worker falhou (code {result.returncode}): {result.stderr.strip()}"
            )

        data = json.loads(result.stdout)

        if data["price"] is None:
            logger.warning("[kabum] Preço não encontrado para product_id=%s", product_id)

        return PriceResult(
            product_id=product_id,
            price=data["price"],
            available=data["available"],
            store=self.store_name,
        )