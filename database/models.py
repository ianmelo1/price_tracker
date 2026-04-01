# price_tracker/database/models.py
"""Modelos ORM: Product e PriceHistory."""

from datetime import datetime
from sqlalchemy import (
    Boolean, Column, DateTime, Float,
    ForeignKey, Index, Integer, String,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    name          = Column(String(300), nullable=False)
    url           = Column(String(2000), nullable=False, unique=True)
    store         = Column(String(50), nullable=False)  # kabum | mercadolivre | amazon | magazineluiza
    target_price  = Column(Float, nullable=True)
    active        = Column(Boolean, default=True, nullable=False)
    created_at    = Column(DateTime, default=datetime.utcnow, nullable=False)

    price_history = relationship(
        "PriceHistory", back_populates="product", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Product id={self.id} store={self.store} name={self.name[:40]!r}>"


class PriceHistory(Base):
    __tablename__ = "price_history"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    price      = Column(Float, nullable=False)
    available  = Column(Boolean, default=True, nullable=False)
    captured_at = Column(DateTime, default=datetime.now, nullable=False)

    product = relationship("Product", back_populates="price_history")

    __table_args__ = (
        Index("ix_price_history_product_captured", "product_id", "captured_at"),
    )

    def __repr__(self) -> str:
        return f"<PriceHistory product_id={self.product_id} price={self.price:.2f}>"