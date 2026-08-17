"""Media Celery application."""

from flashmarket_celery import create_app

app = create_app("flashmarket-media", include=("media_service.tasks",))
