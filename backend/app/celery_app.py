# FILE: backend/app/celery_app.py
# DEFINITIVE VERSION 8.4 (FINAL CORRECTION):
# Corrected the import and function call from 'close_mongo_connection' to
# 'close_mongo_connections' to align with the V8.0 architectural refactor,
# resolving the 'ImportError' startup crash.

from celery import Celery
from celery.signals import worker_process_init, worker_process_shutdown
import logging

from .core.config import settings
# PHOENIX PROTOCOL FIX 1: Import the correctly named function
from .core.db import connect_to_mongo, close_mongo_connections

celery_app = Celery("tasks", broker=settings.REDIS_URL, backend=settings.REDIS_URL)
celery_app.config_from_object('app.celery_config')

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

celery_app.autodiscover_tasks([
    'app.tasks.document_processing',
    'app.tasks.deadline_extraction',
    'app.tasks.findings_extraction',
    'app.tasks.chat_tasks',
    'app.tasks.drafting_tasks'
])

# --- PHOENIX PROTOCOL FIX 2: Create a state dictionary for the worker ---
# This avoids using global variables and provides a clean state for each process.
worker_state = {}

@worker_process_init.connect
def init_worker(**kwargs):
    logging.info("--- [Celery Worker] Initializing worker process... ---")
    # Store the client connections in the worker's state
    mongo_client, db = connect_to_mongo()
    worker_state['mongo_client'] = mongo_client
    worker_state['db'] = db
    # NOTE: motor_client and redis clients are not needed for worker shutdown logic.

@worker_process_shutdown.connect
def shutdown_worker(**kwargs):
    logging.info("--- [Celery Worker] Shutting down worker process... ---")
    mongo_client = worker_state.get('mongo_client')
    if mongo_client:
        # PHOENIX PROTOCOL FIX 3: Call the correctly named function
        # Pass the client from the state, and None for the async client which this worker doesn't use.
        close_mongo_connections(sync_client=mongo_client, async_client=None)