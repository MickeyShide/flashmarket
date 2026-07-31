"""Full-text search primitives shared by schema DDL and query building.

Products are matched against a weighted ``tsvector`` built from ``name``
(weight ``A``) and ``description`` (weight ``B``) with the ``russian`` text
search configuration, which gives stemming for Russian while leaving Latin
words untouched. The same expression backs the GIN index declared on the
products table, so ``@@`` lookups are index-assisted.

PostgreSQL only considers an expression index applicable when the query
expression is structurally identical to the indexed one. Bind parameters are
not interchangeable with constants there, hence every constant below is a
``literal_column`` and never a bound value.

A trigram similarity condition is provided as a second stage: when the parsed
query matches nothing, ``word_similarity`` still finds products whose name
contains a near-miss of the phrase, which is what makes typos survivable.
"""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import ColumnElement, Float, literal, literal_column
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.sql import func

#: Accepts either a bare column (DDL-time, e.g. from a migration) or a mapped
#: ORM attribute (query-time, e.g. ``ProductModel.name``) — callers pass both.
StrColumn = ColumnElement[str] | InstrumentedAttribute[str]

#: Text search configuration used for both indexing and querying.
SEARCH_CONFIG: ColumnElement[Any] = literal_column("'russian'")

_WEIGHT_NAME: ColumnElement[Any] = literal_column("'A'")
_WEIGHT_DESCRIPTION: ColumnElement[Any] = literal_column("'B'")

#: Matches runs of letters and digits in any alphabet, excluding underscores.
_TOKEN_PATTERN = re.compile(r"[^\W_]+")

#: Upper bound on tokens taken from one phrase, to keep query cost predictable.
MAX_SEARCH_TOKENS = 10

#: pg_trgm "word similarity" operator: ``phrase <% haystack``. Unlike ``%`` it
#: compares the phrase against the closest extent of the haystack instead of
#: the whole string, so a short query still matches a long product name.
WORD_SIMILARITY_OP = "<%"


def product_search_vector(
    name: StrColumn,
    description: StrColumn,
) -> ColumnElement[Any]:
    """Build the weighted ``tsvector`` expression for a product."""
    return func.setweight(
        func.to_tsvector(SEARCH_CONFIG, name),
        _WEIGHT_NAME,
    ).op("||", return_type=TSVECTOR)(
        func.setweight(
            func.to_tsvector(SEARCH_CONFIG, description),
            _WEIGHT_DESCRIPTION,
        )
    )


def tokenize_search_phrase(phrase: str) -> list[str]:
    """Split a user phrase into lowercase alphanumeric search tokens.

    Punctuation and operator characters are dropped, so the result is always
    safe to embed into a ``tsquery`` or a ``LIKE`` pattern.
    """
    return _TOKEN_PATTERN.findall(phrase.lower())[:MAX_SEARCH_TOKENS]


def to_prefix_tsquery(tokens: list[str]) -> str:
    """Render tokens as a conjunctive ``tsquery`` with prefix matching.

    Prefix matching keeps incremental (type-as-you-search) queries useful:
    ``iphon`` still matches ``iPhone``.
    """
    return " & ".join(f"{token}:*" for token in tokens)


def _tsquery(tokens: list[str]) -> ColumnElement[Any]:
    """Build the ``tsquery`` side of a match, with the phrase safely bound."""
    return func.to_tsquery(SEARCH_CONFIG, to_prefix_tsquery(tokens))


def product_search_condition(
    name: StrColumn,
    description: StrColumn,
    tokens: list[str],
) -> ColumnElement[bool]:
    """Build the ``tsvector @@ tsquery`` predicate for *tokens*."""
    return product_search_vector(name, description).bool_op("@@")(_tsquery(tokens))


def product_search_rank(
    name: StrColumn,
    description: StrColumn,
    tokens: list[str],
) -> ColumnElement[float]:
    """Score how well a product matches *tokens*; higher is better.

    Weights favour a hit in the name over one in the description.
    """
    return func.ts_rank(
        product_search_vector(name, description),
        _tsquery(tokens),
        type_=Float(),
    )


def product_similarity_condition(
    name: StrColumn,
    phrase: str,
) -> ColumnElement[bool]:
    """Build the trigram near-match predicate used as a typo fallback.

    The phrase is on the left so the indexed column stays on the right, which
    is the form the ``gin_trgm_ops`` index can accelerate.
    """
    return literal(phrase).bool_op(WORD_SIMILARITY_OP)(name)


def product_similarity_rank(
    name: StrColumn,
    phrase: str,
) -> ColumnElement[float]:
    """Score a trigram near-match between *phrase* and a product name."""
    return func.word_similarity(literal(phrase), name, type_=Float())


def product_search_vector_sql() -> str:
    """Render the search vector expression as raw PostgreSQL SQL.

    Used by the migration so the indexed expression is generated from the same
    source as the query expression instead of being duplicated by hand.
    """
    from sqlalchemy import column
    from sqlalchemy.dialects import postgresql

    expression = product_search_vector(column("name"), column("description"))
    compiled = expression.compile(
        dialect=postgresql.dialect(),  # type: ignore[no-untyped-call]
        compile_kwargs={"literal_binds": True},
    )
    return str(compiled)
