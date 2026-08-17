from auth_service.celery_app import app


def test_auth_maintenance_task_is_registered_and_routed() -> None:
    app.loader.import_default_modules()
    task_name = "flashmarket.auth.cleanup_expired_data"

    assert task_name in app.tasks
    assert app.conf.task_routes[task_name]["queue"] == "auth.maintenance"
