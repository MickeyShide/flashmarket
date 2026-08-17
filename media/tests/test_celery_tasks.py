from media_service.celery_app import app


def test_media_maintenance_task_is_registered_and_routed() -> None:
    app.loader.import_default_modules()
    task_name = "flashmarket.media.cleanup_expired_assets"

    assert task_name in app.tasks
    assert app.conf.task_routes[task_name]["queue"] == "media.maintenance"
