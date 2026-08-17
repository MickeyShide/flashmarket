"""Auth Celery application."""

from flashmarket_celery import create_app

app = create_app("flashmarket-auth", include=("auth_service.tasks",))
