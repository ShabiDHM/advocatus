# FILE: backend/app/models/common.py
from bson import ObjectId
from typing import Any
from pydantic_core import core_schema
from pydantic.json_schema import JsonSchemaValue

class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: Any
    ) -> core_schema.CoreSchema:
        
        def validate(v: Any, _: core_schema.ValidationInfo) -> ObjectId:
            """Validate incoming data."""
            if isinstance(v, ObjectId):
                return v
            if ObjectId.is_valid(v):
                return ObjectId(v)
            raise ValueError("Invalid ObjectId")

        return core_schema.json_or_python_schema(
            json_schema=core_schema.with_info_plain_validator_function(validate),
            python_schema=core_schema.is_instance_schema(ObjectId),
            serialization=core_schema.to_string_ser_schema(),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: core_schema.CoreSchema, handler: Any
    ) -> JsonSchemaValue:
        """
        CRITICAL FIX FOR OPENAPI:
        Tells Pydantic/FastAPI that this field behaves like a 'string' 
        in the JSON documentation.
        """
        return {"type": "string", "example": "64b0f16d8e2d4d3a9c9e3b2a"}