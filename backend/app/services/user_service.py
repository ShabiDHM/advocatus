# FILE: backend/app/services/user_service.py
# PHOENIX PROTOCOL - USER SERVICE
# 1. AUTHENTICATION: Now supports login via Username OR Email.
# 2. INTEGRITY: Preserves all previous Pydantic validations.

from pymongo.database import Database
from bson import ObjectId
from fastapi import HTTPException, status
from datetime import datetime, timezone
from typing import Optional

from app.core.security import verify_password, get_password_hash
from app.models.user import UserInDB, UserCreate

def get_user_by_username(db: Database, username: str) -> Optional[UserInDB]:
    user_dict = db.users.find_one({"username": username})
    if user_dict:
        return UserInDB.model_validate(user_dict)
    return None

def get_user_by_email(db: Database, email: str) -> Optional[UserInDB]:
    user_dict = db.users.find_one({"email": email})
    if user_dict:
        return UserInDB.model_validate(user_dict)
    return None

def get_user_by_id(db: Database, user_id: ObjectId) -> Optional[UserInDB]:
    user_dict = db.users.find_one({"_id": user_id})
    if user_dict:
        return UserInDB.model_validate(user_dict)
    return None

def authenticate(db: Database, username: str, password: str) -> Optional[UserInDB]:
    """
    Checks if user exists (by Username OR Email) and password matches hash.
    """
    # 1. Try finding by Username
    user = get_user_by_username(db, username)
    
    # 2. If not found, try finding by Email
    if not user:
        user = get_user_by_email(db, username)
        
    if not user:
        return None
        
    if not verify_password(password, user.hashed_password):
        return None
        
    return user

def create(db: Database, obj_in: UserCreate) -> UserInDB:
    """
    Creates a new user with hashed password.
    """
    user_data = obj_in.model_dump()
    password = user_data.pop("password")
    hashed_password = get_password_hash(password)
    
    user_data["hashed_password"] = hashed_password
    user_data["created_at"] = datetime.now(timezone.utc)
    
    # subscription_status is passed within obj_in (set to INACTIVE by auth endpoint)
    
    result = db.users.insert_one(user_data)
    new_user = db.users.find_one({"_id": result.inserted_id})
    
    if not new_user:
        raise HTTPException(status_code=500, detail="User creation failed")
        
    return UserInDB.model_validate(new_user)

def update_last_login(db: Database, user_id: str):
    """
    Updates the last_login timestamp for a user.
    """
    try:
        oid = ObjectId(user_id)
        db.users.update_one(
            {"_id": oid},
            {"$set": {"last_login": datetime.now(timezone.utc)}}
        )
    except Exception:
        pass

def change_password(db: Database, user_id: str, old_pass: str, new_pass: str):
    """
    Verifies old password and sets new hashed password.
    """
    try:
        oid = ObjectId(user_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    user_dict = db.users.find_one({"_id": oid})
    if not user_dict:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify old password
    if not verify_password(old_pass, user_dict["hashed_password"]):
        raise HTTPException(status_code=400, detail="Invalid old password")

    new_hash = get_password_hash(new_pass)
    db.users.update_one({"_id": oid}, {"$set": {"hashed_password": new_hash}})