"""Inventory Celery application."""

from flashmarket_celery import create_app

app = create_app("flashmarket-inventory", include=("inventory.tasks",))
