# FILE: backend/app/worker.py
# PHOENIX PROTOCOL - WORKER ENTRYPOINT FIX
# 1. Calls the new configuration function to prevent race conditions.
# 2. Ensures worker connects to the correct Redis broker.

import os
from app.celery_app import celery_app, configure_celery_app

# Set an environment variable to signal this is a worker process.
# This prevents the configuration from running twice if imported by the web server.
os.environ["CELERY_WORKER_PROCESS"] = "true"

# Explicitly configure the Celery app instance before the worker starts.
configure_celery_app()

# The celery_app object is now fully configured and ready.
# The 'celery -A app.worker.celery_app worker' command will use this instance.