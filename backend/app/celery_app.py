# FILE: backend/app/celery_app.py

from celery import Celery
import logging

from .core.config import settings

# --- PHOENIX PROTOCOL CURE: Simplified, Stateless Celery App Definition ---
# This file's sole responsibility is to define the Celery application and
# discover the tasks. It holds no state and manages no connections. This
# eliminates the root cause of the ImportError crash loop.

celery_app = Celery("tasks", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

# Load task-related configuration.
celery_app.config_from_object('app.celery_config')

# Set core Celery protocol settings.
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

# Define the modules where tasks are located.
celery_app.autodiscover_tasks([
    'app.tasks.document_processing',
    'app.tasks.deadline_extraction',
    'app.tasks.findings_extraction',
    'app.tasks.chat_tasks',
    'app.tasks.drafting_tasks',
    'app.tasks.document_reprocessing',
])

logging.getLogger(__name__).info("--- [Celery App] Celery application configured successfully. ---")