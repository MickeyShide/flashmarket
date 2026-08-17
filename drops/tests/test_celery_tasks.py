from drops.celery_app import app


def test_drops_maintenance_task_is_registered_and_routed() -> None:
    app.loader.import_default_modules()
    task_name = "flashmarket.drops.run_scheduler_tick"

    assert task_name in app.tasks
    assert app.conf.task_routes[task_name]["queue"] == "drops.maintenance"
