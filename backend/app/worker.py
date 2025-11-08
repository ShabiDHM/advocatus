# app/worker.py
# This file is the entry point for the Celery worker.
# It simply imports the centrally configured celery_app instance.
from app.celery_app import celery_app

# The command to run the worker will be:
# celery -A app.worker.celery_app worker --loglevel=info
# Docker Compose handles this command for us.