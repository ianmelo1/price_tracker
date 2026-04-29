# price_tracker/database/repository.py
"""CRUD e queries para Product e PriceHistory."""

import logging
from typing import Optional
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from database.models import Base, PriceHistory, Product
from config import config

logger = logging.getLogger(__name__)

engine = create_engine(
    config.database_url,
    connect_args={"check_same_thread": False},  # obrigatório para SQLite + threads
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db() -> None:
    """Cria as tabelas no banco se ainda não existirem."""
    Base.metadata.create_all(bind=engine)
    logger.info("Banco de dados inicializado.")


# ── Products ──────────────────────────────────────────────

def add_product(
    name: str,
    url: str,
    store: str,
    target_price: Optional[float] = None,
) -> tuple[Product, bool]:
    """Cadastra novo produto. Retorna (produto, criado) — criado=False se já existia."""
    with SessionLocal() as session:
        existing = session.execute(select(Product).where(Product.url == url)).scalars().first()
        if existing:
            logger.warning("Produto já cadastrado: %s", url)
            return existing, False

        product = Product(name=name, url=url, store=store, target_price=target_price)
        session.add(product)
        session.commit()
        logger.info("Produto cadastrado: %s (%s)", name, store)
        return product, True


def get_active_products() -> list[Product]:
    """Retorna todos os produtos com active=True."""
    with SessionLocal() as session:
        return session.execute(
            select(Product).where(Product.active == True)
        ).scalars().all()


def update_target_price(product_id: int, target_price: float) -> None:
    """Atualiza o preço-alvo de um produto."""
    with SessionLocal() as session:
        product = session.get(Product, product_id)
        if product:
            product.target_price = target_price
            session.commit()
            logger.info("Preço-alvo atualizado: product_id=%s → R$ %.2f", product_id, target_price)


def deactivate_product(product_id: int) -> None:
    """Desativa um produto (não apaga do histórico)."""
    with SessionLocal() as session:
        product = session.get(Product, product_id)
        if product:
            product.active = False
            session.commit()


# ── Price History ─────────────────────────────────────────

def record_price(product_id: int, price: float, available: bool = True) -> PriceHistory:
    """Salva um novo registro de preço no histórico."""
    with SessionLocal() as session:
        entry = PriceHistory(product_id=product_id, price=price, available=available)
        session.add(entry)
        session.commit()
        logger.debug("Preço salvo: product_id=%s R$ %.2f", product_id, price)
        return entry


def get_price_history(product_id: int, limit: int = 100) -> list[PriceHistory]:
    """Retorna os registros mais recentes de preço de um produto."""
    with SessionLocal() as session:
        stmt = (
            select(PriceHistory)
            .where(PriceHistory.product_id == product_id)
            .order_by(PriceHistory.captured_at.desc())
            .limit(limit)
        )
        return session.execute(stmt).scalars().all()


def get_latest_price(product_id: int) -> Optional[PriceHistory]:
    """Retorna o registro de preço mais recente de um produto."""
    with SessionLocal() as session:
        stmt = (
            select(PriceHistory)
            .where(PriceHistory.product_id == product_id)
            .order_by(PriceHistory.captured_at.desc())
            .limit(1)
        )
        return session.execute(stmt).scalars().first()


def get_price_stats(product_id: int) -> dict:
    """Retorna min, max, média e primeiro preço registrado de um produto."""
    with SessionLocal() as session:
        row = session.execute(
            select(
                func.min(PriceHistory.price),
                func.max(PriceHistory.price),
                func.avg(PriceHistory.price),
                func.count(PriceHistory.id),
            ).where(PriceHistory.product_id == product_id)
        ).first()
        if not row or row[3] == 0:
            return {"min": None, "max": None, "avg": None, "count": 0}
        first_entry = session.execute(
            select(PriceHistory)
            .where(PriceHistory.product_id == product_id)
            .order_by(PriceHistory.captured_at.asc())
            .limit(1)
        ).scalars().first()
        return {
            "min": row[0],
            "max": row[1],
            "avg": row[2],
            "count": row[3],
            "first_price": first_entry.price if first_entry else None,
        }