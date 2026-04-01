# 🛒 Price Tracker

Monitor preços de eletrônicos em tempo real nas principais lojas do Brasil e receba alertas via Telegram quando o preço atingir sua meta.

## Funcionalidades

- **Scraping automático** de KaBuM, Mercado Livre (API oficial), Amazon BR e Magazine Luiza
- **Dashboard interativo** com histórico de preços e gráficos (Streamlit + Plotly)
- **Alertas via Telegram** quando o preço cair abaixo do valor alvo
- **Agendamento automático** de buscas com APScheduler
- **Banco de dados local** SQLite com histórico completo via SQLAlchemy

---

## Pré-requisitos

- Python 3.10+
- [Telegram Bot Token](https://core.telegram.org/bots/tutorial) (opcional, para notificações)
- Credenciais da [API do Mercado Livre](https://developers.mercadolivre.com.br/) (opcional)

---

## Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/price_tracker.git
cd price_tracker

# 2. Crie e ative o ambiente virtual
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
.venv\Scripts\activate           # Windows

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Instale os navegadores do Playwright (necessário para Magazine Luiza)
playwright install chromium
```

---

## Configuração

Crie um arquivo `.env` na raiz do projeto com base no exemplo abaixo:

```env
# Banco de dados
DATABASE_URL=sqlite:///price_tracker.db

# Telegram
TELEGRAM_BOT_TOKEN=seu_token_aqui
TELEGRAM_CHAT_ID=seu_chat_id_aqui

# Mercado Livre API
ML_CLIENT_ID=seu_client_id
ML_CLIENT_SECRET=seu_client_secret

# Agendamento (em minutos)
SCRAPE_INTERVAL_MINUTES=60
```

> ⚠️ **Nunca** commite o arquivo `.env`. Ele já está incluído no `.gitignore`.

---

## Uso

### Iniciando o dashboard

```bash
streamlit run app.py
```

Acesse em `http://localhost:8501`.

### Executando o agendador em background

```bash
python scheduler.py
```

### Executando um scraper manualmente

```python
from scrapers.kabum import KaBumScraper

scraper = KaBumScraper()
resultado = scraper.get_price("https://www.kabum.com.br/produto/...")
print(resultado)
```

---

## Estrutura do Projeto

```
price_tracker/
├── scrapers/
│   ├── base_scraper.py       # Classe base abstrata
│   ├── kabum.py              # Scraper KaBuM (requests + BS4)
│   ├── mercadolivre.py       # Integração API oficial
│   ├── amazon_br.py          # Scraper Amazon BR
│   └── magazineluiza.py      # Scraper Magalu (Playwright)
├── database/
│   ├── models.py             # Modelos Product e PriceHistory
│   └── repository.py         # Camada de acesso a dados
├── notifications/
│   └── telegram_bot.py       # Envio de alertas via Telegram
├── app.py                    # Dashboard Streamlit
├── scheduler.py              # Agendamento com APScheduler
├── config.py                 # Carregamento de variáveis de ambiente
├── requirements.txt
├── .env.example
└── README.md
```

---

## Lojas Suportadas

| Loja            | Método          | Rate Limit |
|-----------------|-----------------|------------|
| KaBuM           | requests + BS4  | 2s         |
| Mercado Livre   | API oficial     | 2s         |
| Amazon BR       | requests + BS4  | 2s         |
| Magazine Luiza  | Playwright      | 2s         |

---

## Banco de Dados

O projeto usa SQLite com dois modelos principais:

- **`Product`** — URL, nome, loja, preço-alvo, data de cadastro
- **`PriceHistory`** — preço coletado, timestamp, FK para Product

O banco é criado automaticamente na primeira execução.

---

## Contribuindo

1. Fork o repositório
2. Crie uma branch: `git checkout -b feature/nova-loja`
3. Commit suas mudanças: `git commit -m 'feat: adiciona scraper Americanas'`
4. Push: `git push origin feature/nova-loja`
5. Abra um Pull Request

---

## Licença

Distribuído sob a licença MIT. Veja [`LICENSE`](LICENSE) para mais informações.