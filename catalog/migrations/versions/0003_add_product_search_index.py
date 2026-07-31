"""add_product_search_index

Adds a GIN expression index backing PostgreSQL full-text search over product
name and description, replacing unindexable ``ILIKE '%...%'`` scans.

The indexed expression is generated from
``catalog.infrastructure.search.product_search_vector`` so the DDL and the
runtime query expression can never drift apart — PostgreSQL only uses an
expression index when the query expression matches it exactly.

``pg_trgm`` is enabled as well: it makes the trigram similarity fallback used
for typo-tolerant matching index-assisted.

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-31
"""

from collections.abc import Sequence

from alembic import op

from catalog.infrastructure.search import product_search_vector_sql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEX_NAME = "ix_products_search_vector"
TRGM_INDEX_NAME = "ix_products_name_trgm"


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(f"CREATE INDEX {INDEX_NAME} ON products USING gin (({product_search_vector_sql()}))")
    op.create_index(
        TRGM_INDEX_NAME,
        "products",
        ["name"],
        postgresql_using="gin",
        postgresql_ops={"name": "gin_trgm_ops"},
    )


def downgrade() -> None:
    op.drop_index(TRGM_INDEX_NAME, table_name="products")
    op.drop_index(INDEX_NAME, table_name="products")
