# Price Tracker

> Automated price monitoring for Brazilian e-commerce stores — with a live dashboard and Discord alerts.

![Python](https://img.shields.io/badge/Python-3.13%2B-blue?logo=python)
![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B?logo=streamlit)
![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite)
![License](https://img.shields.io/badge/License-MIT-green)
![Built with Claude](https://img.shields.io/badge/Built%20with-Claude%20(Anthropic)-blueviolet?logo=anthropic)

---

## What it does

Price Tracker watches product URLs across multiple Brazilian online retailers, records prices over time, and sends you a Discord notification the moment a product hits your target price.

- Add any product URL → it starts being monitored
- Prices are checked automatically on a configurable interval
- Interactive dashboard shows price history charts in real time
- Discord alert fires when the current price ≤ your target

---

## Stores supported

| Store | Method | Status |
|---|---|---|
| KaBuM | Playwright (headless Chrome) | ✅ Working |
| Mercado Livre | Official API | ✅ Working |
| Amazon BR | — | 🚧 Coming soon |
| Magazine Luiza | — | 🚧 Coming soon |

---

## Architecture

```
price_tracker/
├── app.py                    # Streamlit dashboard (UI entry point)
├── scheduler.py              # APScheduler — runs price checks on interval
├── config.py                 # Config loaded from .env
│
├── scrapers/
│   ├── base_scraper.py       # Abstract base class + PriceResult dataclass
│   ├── kabum.py              # KaBuM — spawns headless browser via subprocess
│   ├── _kabum_worker.py      # Playwright worker (called by kabum.py)
│   ├── mercadolivre.py       # Mercado Livre — calls official REST API
│   ├── amazon_br.py          # Stub (not yet implemented)
│   └── magazineluiza.py      # Stub (not yet implemented)
│
├── database/
│   ├── models.py             # SQLAlchemy models: Product, PriceHistory
│   └── repository.py         # CRUD layer — all DB interactions go here
│
├── notifications/
│   └── discord_notifier.py   # Sends embeds to a Discord webhook
│
├── requirements.txt
├── pyproject.toml
├── .env.example
└── .gitignore
```

**Data flow:**

```
User adds product (Streamlit UI)
        ↓
   products table (SQLite)
        ↓
   Scheduler fires (every N minutes)
        ↓
   Scraper fetches price
        ↓
   price_history table updated
        ↓
   price ≤ target? → Discord alert
```

---

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- A Discord webhook URL for notifications
- Mercado Livre API credentials (only if tracking ML products)

---

## Installation

```bash
# 1. Clone
git clone https://github.com/ianmelo1/price_tracker.git
cd price_tracker

# 2. Create virtual environment and install dependencies
uv sync
# or with pip:
python -m venv .venv && .venv/Scripts/activate   # Windows
pip install -r requirements.txt

# 3. Install Playwright browsers (needed for KaBuM scraping)
playwright install chromium

# 4. Copy and fill in the config
cp .env.example .env
# Edit .env with your Discord webhook and other settings
```

---

## Configuration

All settings live in `.env`. Copy `.env.example` to get started:

```env
# Database (SQLite, auto-created on first run)
DATABASE_URL=sqlite:///price_tracker.db

# Discord Webhook — required for price alerts
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN

# Mercado Livre API — optional, only for ML product URLs
MERCADOLIVRE_APP_ID=your_app_id
MERCADOLIVRE_SECRET=your_secret

# How often to check prices (default: 60 minutes)
CHECK_INTERVAL_MINUTES=60
```

> **Never commit `.env`** — it is already listed in `.gitignore`.

---

## Usage

### Run the dashboard

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`. The background scheduler starts automatically inside the Streamlit process.

### Run the scheduler standalone (headless)

```bash
python scheduler.py
```

Useful if you want to run just the price-checking loop without the UI (e.g., on a server).

### Test a scraper manually

```python
from scrapers.kabum import KaBumScraper

scraper = KaBumScraper()
result = scraper.fetch_price(product_id=1, url="https://www.kabum.com.br/produto/...")
print(result.price, result.available)
```

---

## How price alerts work

When the scheduler runs, for each active product it:

1. Calls the appropriate scraper
2. Records the price in `price_history`
3. Compares `current_price` with `target_price`
4. If `current_price <= target_price` → sends a Discord embed with the product name, store, both prices, and a direct link

Error alerts (scraper failure) are also sent to Discord so you know when something stops working.

---

## Database schema

Two SQLAlchemy models backed by SQLite:

**`Product`**
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | Auto |
| name | String | Product display name |
| url | String | Unique product URL |
| store | String | `kabum`, `mercadolivre`, etc. |
| target_price | Float | Nullable — alert threshold |
| active | Boolean | Soft delete flag |
| created_at | DateTime | Auto |

**`PriceHistory`**
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | Auto |
| product_id | FK → Product | Cascade delete |
| price | Float | Scraped price |
| available | Boolean | In stock? |
| captured_at | DateTime | Indexed with product_id |

---

## Contributing

Pull requests are welcome. To add a new store:

1. Create `scrapers/your_store.py` inheriting from `BaseScraper`
2. Implement `fetch_price(product_id, url) -> PriceResult`
3. Register the store key in `scheduler.py` and the Streamlit selectbox in `app.py`

```bash
git checkout -b feature/add-americanas-scraper
# ... implement ...
git commit -m "feat: add Americanas scraper"
git push origin feature/add-americanas-scraper
```

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

> **Built with [Claude](https://www.anthropic.com/claude) by Anthropic.**
> This project was designed and implemented with the assistance of Claude, Anthropic's AI assistant.
