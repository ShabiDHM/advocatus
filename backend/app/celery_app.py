# FILE: backend/app/celery_app.py

from celery import Celery
import logging

from .core.config import settings
# PHOENIX PROTOCOL CURE: The db module is implicitly imported by the tasks.
# No direct connection management is needed here anymore.

# Define the Celery application instance.
celery_app = Celery("tasks", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

# Load configuration from a separate config file.
celery_app.config_from_object('app.celery_config')

# Set core Celery configuration settings.
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True
)

logger = logging.getLogger(__name__)

# Automatically discover tasks from the specified modules.
celery_app.autodiscover_tasks([
    'app.tasks.document_processing',
    'app.tasks.deadline_extraction',
    'app.tasks.findings_extraction',
    'app.tasks.chat_tasks',
    'app.tasks.drafting_tasks',
    # PHOENIX PROTOCOL CURE: Add any other task modules here as they are created.
    'app.tasks.document_reprocessing',
])

# PHOENIX PROTOCOL CURE: All manual connection logic (worker_process_init,
# worker_process_shutdown) has been removed. The global instances in `db.py`
# are initialized once when the worker process starts and are shared by all tasks.
# This simplifies the architecture and resolves all Pylance errors.

logger.info("--- [Celery App] Celery application configured. ---")