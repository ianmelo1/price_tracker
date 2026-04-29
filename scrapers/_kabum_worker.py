# scrapers/_kabum_worker.py
# Script standalone — chamado como subprocesso pelo KabumScraper.
# Recebe a URL como argumento e imprime JSON no stdout.

import sys
import json
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


def _parse_price(raw: str) -> float:
    clean = (
        raw.replace("R$", "")
           .replace("\xa0", "")
           .replace("\u00a0", "")
           .replace(".", "")
           .replace(",", ".")
           .strip()
    )
    return float(clean)


def extract_price(page) -> float | None:
    # Seletor em estoque
    try:
        tag = page.locator("h4.text-4xl").first
        tag.wait_for(timeout=5000)
        return _parse_price(tag.inner_text())
    except (PlaywrightTimeout, ValueError):
        pass

    # Seletor esgotado \u2014 pre\u00e7o exibido em cinza
    try:
        tag = page.locator("span.text-secondary-500.font-semibold").first
        tag.wait_for(timeout=4000)
        return _parse_price(tag.inner_text())
    except (PlaywrightTimeout, ValueError):
        return None


def extract_availability(page) -> bool:
    return not page.locator("span:has-text('esgotado')").is_visible()


def run(url: str, user_agent: str) -> dict:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=user_agent,
            viewport={"width": 1280, "height": 800},
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
        )
        page = context.new_page()
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page.goto(url, wait_until="domcontentloaded", timeout=30000)

        try:
            accept_btn = page.locator(
                "button#accept-all-cookies, "
                "button:has-text('Aceitar'), "
                "button:has-text('Aceitar todos')"
            )
            accept_btn.first.click(timeout=5000)
            page.wait_for_timeout(1000)  # aguarda banner sumir antes de extrair preço
        except Exception:
            pass  # sem banner — segue normalmente

        result = {
            "price": extract_price(page),
            "available": extract_availability(page),
        }
        browser.close()
    return result


if __name__ == "__main__":
    url = sys.argv[1]
    user_agent = sys.argv[2]
    output = run(url, user_agent)
    print(json.dumps(output))