"""SQLAlchemy ORM models for the catalog database."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    column,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from catalog.domain.entities import Currency, ProductStatus
from catalog.infrastructure.database import Base, utc_now
from catalog.infrastructure.search import product_search_vector


class CategoryModel(Base):
    """Hierarchical product category."""

    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid7,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )

    children: Mapped[list[CategoryModel]] = relationship(
        "CategoryModel",
        back_populates="parent",
        order_by="CategoryModel.name",
        lazy="selectin",
    )
    parent: Mapped[CategoryModel | None] = relationship(
        "CategoryModel",
        back_populates="children",
        remote_side=[id],
        lazy="joined",
    )


class BrandModel(Base):
    """Product brand / manufacturer entity."""

    __tablename__ = "brands"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid7,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    logo_url: Mapped[str | None] = mapped_column(String(2048))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )


class ProductModel(Base):
    """Catalog product with pricing and lifecycle status."""

    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("price > 0", name="ck_products_price_positive"),
        Index("ix_products_status", "status"),
        Index("ix_products_price", "price"),
        Index("ix_products_category_status", "category_id", "status"),
        Index("ix_products_brand_status", "brand_id", "status"),
        Index(
            "ix_products_search_vector",
            product_search_vector(column("name"), column("description")),
            postgresql_using="gin",
        ).ddl_if(dialect="postgresql"),
        Index(
            "ix_products_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ).ddl_if(dialect="postgresql"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid7,
        server_default=text("gen_random_uuid()"),
    )
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    price: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=2),
        nullable=False,
    )
    currency: Mapped[Currency] = mapped_column(
        Enum(Currency, name="currency"),
        nullable=False,
        default=Currency.RUB,
        server_default="RUB",
    )
    status: Mapped[ProductStatus] = mapped_column(
        Enum(ProductStatus, name="product_status"),
        nullable=False,
        default=ProductStatus.HIDDEN,
        server_default="HIDDEN",
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    brand_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("brands.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    cover_image: Mapped[str | None] = mapped_column(String(2048))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    category: Mapped[CategoryModel] = relationship(lazy="joined")
    brand: Mapped[BrandModel | None] = relationship(lazy="joined")
    images: Mapped[list[ProductImageModel]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ProductImageModel.sort_order",
        lazy="selectin",
    )
    variants: Mapped[list[ProductVariantModel]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ProductVariantModel.sort_order",
        lazy="selectin",
    )


class ProductImageModel(Base):
    """Supplementary image attached to a product."""

    __tablename__ = "product_images"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid7)
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    product: Mapped[ProductModel] = relationship(back_populates="images")


class ProductVariantModel(Base):
    """Product variant with specific SKU, size, color, and optional price override."""

    __tablename__ = "product_variants"
    __table_args__ = (
        UniqueConstraint(
            "product_id",
            "size",
            "color",
            name="uq_variant_product_size_color",
            postgresql_nulls_not_distinct=True,
        ),
        CheckConstraint(
            "price_override IS NULL OR price_override > 0",
            name="ck_product_variants_price_override_positive",
        ),
        Index("ix_variants_product_active", "product_id", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid7,
        server_default=text("gen_random_uuid()"),
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sku: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    size: Mapped[str | None] = mapped_column(String(20), nullable=True)
    color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    color_hex: Mapped[str | None] = mapped_column(String(7), nullable=True)
    material: Mapped[str | None] = mapped_column(String(100), nullable=True)
    weight_grams: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price_override: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=12, scale=2), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        nullable=False, default=True, server_default=text("true")
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )

    product: Mapped[ProductModel] = relationship(back_populates="variants")
