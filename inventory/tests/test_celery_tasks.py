from inventory.celery_app import app


def test_inventory_maintenance_task_is_registered_and_routed() -> None:
    app.loader.import_default_modules()
    task_name = "flashmarket.inventory.expire_reservations"

    assert task_name in app.tasks
    assert app.conf.task_routes[task_name]["queue"] == "inventory.maintenance"
