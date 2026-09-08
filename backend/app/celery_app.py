# FILE: backend/app/celery_app.py
# PHOENIX PROTOCOL - CELERY ROBUSTNESS V3.0 (GDPR SCHEDULER READY)
# 1. ENHANCED: Added beat schedule for GDPR archive deletion task.
# 2. ENHANCED: Autodiscovers archive_tasks module.
# 3. STATUS: Type-safe, decoupled configuration, production-ready.

from celery import Celery
from celery.schedules import crontab
import logging
import os

# Use os.getenv directly for the initial definition to prevent startup race conditions.
redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery("tasks", broker=redis_url, backend=redis_url)

def configure_celery_app():
    """
    This function applies the full configuration to the Celery app.
    It is called EXPLICITLY by the worker entrypoint (worker.py).
    """
    from .core.config import settings
    
    # PHOENIX FIX: Use .update() for type safety instead of direct assignment.
    celery_app.conf.update(
        broker_url=settings.REDIS_URL,
        result_backend=settings.REDIS_URL,
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        worker_prefetch_multiplier=1,
        task_acks_late=True,
    )

    # Load any additional task-related configuration from celery_config.py
    celery_app.config_from_object('app.celery_config')

    # --- GDPR: Schedule for automatic deletion of expired archive items ---
    celery_app.conf.beat_schedule = {
        'delete-expired-archive-every-day': {
            'task': 'app.tasks.archive_tasks.delete_expired_archive_items',
            'schedule': crontab(hour=0, minute=0),  # Every day at 00:00 UTC
        },
    }

    # Define the modules where tasks are located.
    celery_app.autodiscover_tasks([
        'app.tasks.document_processing',
        'app.tasks.deadline_extraction',
        'app.tasks.findings_extraction',
        'app.tasks.chat_tasks',
        'app.tasks.archive_tasks',   # Added for GDPR retention policy
    ])
    
    logging.getLogger(__name__).info("--- [Celery App] Celery application fully configured for worker (GDPR compliant). ---")

