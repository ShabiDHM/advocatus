# File: app/celery_config.py
# DEFINITIVE CELERY FIX: Centralized worker configuration.

# This is the list of all modules that the Celery WORKER should discover tasks from.
# The backend/producer code will NOT import this file.
include = [
    "app.tasks.document_processing",
    "app.tasks.deadline_extraction"
]

task_track_started = True