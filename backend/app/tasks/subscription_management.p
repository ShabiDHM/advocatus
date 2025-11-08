# app/tasks/subscription_management.py
from app.celery_app import celery_app
from ..services import admin_service
from celery.schedules import crontab
import json

def log_structured(task_name: str, status: str, message: str = "", **extra):
    log_entry = {"task_name": task_name, "status": status, "message": message, **extra}
    print(json.dumps(log_entry))

@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Sets up the periodic task schedule (Celery Beat)."""
    sender.add_periodic_task(
        crontab(hour=0, minute=5), # Run daily at 00:05 UTC
        check_subscriptions.s(),
        name='Check for expired subscriptions daily',
    )

@celery_app.task(name="check_subscriptions")
def check_subscriptions():
    """
    Thin wrapper task that delegates the subscription check to the admin_service.
    """
    task_name = "nightly_subscription_check"
    log_structured(task_name, "initiated")
    try:
        num_expired = admin_service.expire_subscriptions()
        log_structured(task_name, "success", f"{num_expired} subscriptions expired.")
    except Exception as e:
        log_structured(task_name, "failed", str(e))