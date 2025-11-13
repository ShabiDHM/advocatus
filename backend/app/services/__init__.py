# FILE: backend/app/services/__init__.py

# This file marks the 'services' directory as a Python package.
# PHOENIX PROTOCOL CURE: The explicit re-export of the deprecated 
# 'get_user_from_token' function has been removed to resolve the ImportError.
# Individual services and their functions should be imported directly 
# from their respective modules (e.g., `from app.services import user_service`).