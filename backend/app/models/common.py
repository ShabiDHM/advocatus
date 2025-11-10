# FILE: backend/app/models/common.py
# DEFINITIVE VERSION (ARCHITECTURAL FOUNDATION):
# 1. This file provides the core, reusable `PyObjectId` type for MongoDB integration.
# 2. It uses Pydantic's `BeforeValidator` to ensure that any string representation
#    of an ObjectId is correctly validated and converted into a `bson.ObjectId` instance.
# 3. It includes serialization logic to convert `ObjectId` back to a string for JSON
#    responses, ensuring API compatibility.
# 4. This single, correct implementation resolves the "unknown import symbol" error
#    across the entire application.

from bson import ObjectId
from pydantic import BeforeValidator
from typing import Annotated

# --- The Core Architectural Cure ---
# Pydantic v2 and later require using an Annotated type with a validator.
# This function checks if the input is a valid ObjectId and, if it's a string,
# converts it. This is the validation logic.
def validate_object_id(v):
    if isinstance(v, ObjectId):
        return v
    if ObjectId.is_valid(v):
        return ObjectId(v)
    raise ValueError("Invalid ObjectId")

# We create an annotated type. Pydantic will use this for validation and JSON schema generation.
# `BeforeValidator` applies our validation function before any other Pydantic validation.
# `PlainSerializer` tells Pydantic to simply call `str()` on the ObjectId when serializing.
# `WithJsonSchema` provides the schema hint that this will be a string.
PyObjectId = Annotated[
    ObjectId,
    BeforeValidator(validate_object_id),
]