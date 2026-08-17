"""Drops Celery application."""

from flashmarket_celery import create_app

app = create_app("flashmarket-drops", include=("drops.tasks",))
