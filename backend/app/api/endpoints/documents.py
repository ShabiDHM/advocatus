# FILE: backend/app/api/endpoints/documents.py
# DEFINITIVE VERSION 19.0 (ARCHITECTURAL DEPRECATION):
# This router has been deprecated and its functionality consolidated into the
# 'cases.py' router. This is the definitive and final state of this file,
# ensuring all document routes are correctly handled as sub-resources of a case
# to resolve all 404 Not Found errors.

from fastapi import APIRouter

# This router is now intentionally left empty as its routes have been moved
# to the '/cases' router to follow correct RESTful architecture.
router = APIRouter()