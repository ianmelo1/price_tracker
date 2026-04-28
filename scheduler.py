# price_tracker/scheduler.py

import logging
import time

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import config
from database.repository import get_active_products, record_price, get_latest_price
from scrapers.kabum import KabumScraper
from scrapers.mercadolivre import MercadoLivreScraper
from notifications.discord_notifier import send_price_alert, send_error_alert

logger = logging.getLogger(__name__)

SCRAPERS = {
    "kabum": KabumScraper(),
    "mercadolivre": MercadoLivreScraper(),
}


def check_prices() -> None:
    """Busca o preço de todos os produtos ativos e salva no histórico."""
    products = get_active_products()
    logger.info("Verificando %d produto(s)...", len(products))

    for product in products:
        scraper = SCRAPERS.get(product.store)

        if scraper is None:
            logger.warning("Scraper não encontrado para loja: %s", product.store)
            continue

        previous = get_latest_price(product.id)
        result = scraper.fetch_price(product.id, product.url)

        if result.price is None:
            send_error_alert(product.store, product.url, "Preço não encontrado na página")
            continue

        record_price(product.id, result.price, result.available)
        logger.info("[%s] %s → R$ %.2f", product.store, product.name, result.price)

        _check_target(product, result.price, previous_price=previous.price if previous else None)


def _check_target(product, current_price: float, previous_price: float | None) -> None:
    """Envia alerta apenas quando o preço cruza o alvo (evita spam a cada intervalo)."""
    if not product.target_price:
        return
    if current_price > product.target_price:
        return
    # só alerta se o preço anterior era desconhecido ou estava acima do alvo
    if previous_price is not None and previous_price <= product.target_price:
        return
    send_price_alert(
        product_name=product.name,
        store=product.store,
        current_price=current_price,
        target_price=product.target_price,
        url=product.url,
    )


def start_scheduler() -> None:
    """Inicia o BackgroundScheduler e retorna imediatamente.

    Adequado tanto para uso embutido no Streamlit quanto para execução
    standalone — neste caso, o bloco __main__ mantém o processo vivo.
    """
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=check_prices,
        trigger=IntervalTrigger(minutes=config.check_interval_minutes),
        id="check_prices",
        name="Verificar preços",
        replace_existing=True,
    )
    logger.info("Scheduler iniciado — intervalo: %d min", config.check_interval_minutes)
    check_prices()  # roda imediatamente na largada
    scheduler.start()


if __name__ == "__main__":
    start_scheduler()
    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler encerrado.")