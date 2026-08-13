"""Low-cardinality RabbitMQ reliability metrics shared by workers."""

from prometheus_client import Counter

PUBLISH_OUTCOMES = Counter(
    "flashmarket_rabbitmq_publish_total",
    "RabbitMQ confirmed publish attempts by outcome",
    ("outcome",),
)
CONSUMER_MOVES = Counter(
    "flashmarket_rabbitmq_consumer_move_total",
    "Failed consumer deliveries moved to retry or DLQ",
    ("destination",),
)
