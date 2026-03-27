# price_tracker/notifications/discord_notifier.py

import logging
import requests

from config import config

logger = logging.getLogger(__name__)


def send_price_alert(
    product_name: str,
    store: str,
    current_price: float,
    target_price: float,
    url: str,
) -> None:
    """Envia alerta no Discord quando o preço atingir o alvo."""
    payload = {
        "embeds": [{
            "title": f"🔔 Alerta de preço — {product_name}",
            "url": url,
            "color": 0x00b894,
            "fields": [
                {"name": "Loja",        "value": store,                    "inline": True},
                {"name": "Preço atual", "value": f"R$ {current_price:.2f}", "inline": True},
                {"name": "Seu alvo",    "value": f"R$ {target_price:.2f}",  "inline": True},
            ],
            "footer": {"text": "price_tracker"},
        }]
    }
    try:
        response = requests.post(config.discord_webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("Alerta Discord enviado: %s R$ %.2f", product_name, current_price)
    except requests.RequestException as exc:
        logger.error("Falha ao enviar alerta Discord: %s", exc)


def send_error_alert(store: str, url: str, reason: str) -> None:
    """Avisa no Discord quando um scraper falhar repetidamente."""
    payload = {
        "embeds": [{
            "title": f"⚠️ Falha no scraper — {store}",
            "color": 0xd63031,
            "fields": [
                {"name": "URL",    "value": url,    "inline": False},
                {"name": "Motivo", "value": reason, "inline": False},
            ],
            "footer": {"text": "price_tracker"},
        }]
    }
    try:
        response = requests.post(config.discord_webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("Alerta de erro Discord enviado: %s", store)
    except requests.RequestException as exc:
        logger.error("Falha ao enviar alerta de erro Discord: %s", exc)