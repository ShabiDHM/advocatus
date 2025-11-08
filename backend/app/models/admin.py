# app/models/admin.py
# DEFINITIVE VERSION 4.0 (PYDANTIC V2 ALIASING CORRECTION):
# 1. Corrected the UserAdminView model to explicitly alias the 'id' field to MongoDB's '_id'
#    using Field(validation_alias='_id'). This resolves the Pydantic ValidationError
#    and the subsequent 500 Internal Server Error on the Admin Dashboard.
# 2. Previous model definitions remain correct.

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal
from datetime import datetime

# Import the common PyObjectId helper
from .common import PyObjectId

class SubscriptionUpdate(BaseModel):
    """
    Pydantic model for updating a user's subscription details.
    This is the data an admin would provide.
    """
    subscription_status: Literal['active', 'expired', 'none']
    subscription_expiry_date: Optional[datetime] = None
    last_payment_date: Optional[datetime] = None
    last_payment_amount: Optional[float] = None
    admin_notes: Optional[str] = None

class UserAdminView(BaseModel):
    """
    Detailed view of a user's data for the admin panel.
    """
    # PHOENIX PROTOCOL FIX: Explicitly alias 'id' to '_id' for database validation/loading
    id: PyObjectId = Field(validation_alias='_id')
    username: str
    email: str
    role: str
    subscription_status: str
    subscription_expiry_date: Optional[datetime] = None
    last_payment_date: Optional[datetime] = None
    last_payment_amount: Optional[float] = None
    admin_notes: Optional[str] = None
    
    # from_attributes is necessary for the FastAPI response to work correctly.
    model_config = ConfigDict(from_attributes=True)