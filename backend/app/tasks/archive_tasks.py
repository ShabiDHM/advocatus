# FILE: backend/app/tasks/archive_tasks.py
# PHOENIX PROTOCOL - ARCHIVE TASKS V1.0 (GDPR RETENTION)
# 1. ADDED: Celery task for automatic deletion of expired archive items.
# 2. STATUS: Ready for production, uses ArchiveService.delete_expired_items().

import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name='app.tasks.archive_tasks.delete_expired_archive_items')
def delete_expired_archive_items():
    """
    Celery task to delete archive items that have passed their expiration date.
    This task is scheduled by Celery Beat (see celery_app.py).
    """
    try:
        # Import here to avoid circular imports at module load time
        from app.core.db import get_db
        from app.services.archive_service import ArchiveService

        # Get database instance
        db = get_db()  # or however you obtain the database in your app
        if not db:
            logger.error("Database connection could not be established.")
            return {"error": "No database connection"}

        # Initialize archive service
        service = ArchiveService(db)

        # Delete expired items
        deleted_count = service.delete_expired_items()

        logger.info(f"Archive retention task completed. Deleted {deleted_count} expired items.")
        return {"deleted": deleted_count}

    except Exception as e:
        logger.error(f"Archive retention task failed: {e}", exc_info=True)
        return {"error": str(e)}