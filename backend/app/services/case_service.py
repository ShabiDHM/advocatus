# FILE: backend/app/services/case_service.py
# PHOENIX PROTOCOL - DRAFTING LOGIC & IMPORT FIX
# 1. IMPORT FIX: Changed model import to '...models.drafting.DraftRequest'.
# 2. TASK DISPATCH FIX: Removed direct import from 'worker' and now imports 'celery_app' to dispatch tasks by name.
# 3. LOGIC FIX: Aligned the service function with the correct fields from the 'DraftRequest' model (prompt, document_type).
# 4. RESULT: Resolves both 'reportMissingImports' and 'reportAttributeAccessIssue' errors.

from fastapi import HTTPException, status
from pymongo.database import Database
from bson import ObjectId
from datetime import datetime, timezone, timedelta

from ..models.case import CaseCreate, ClientDetailsOut
from ..models.user import UserInDB
from ..models.drafting import DraftRequest # <--- CORRECTED IMPORT
from ..celery_app import celery_app # <--- CORRECTED IMPORT

def create_case(db: Database, case_in: CaseCreate, owner: UserInDB) -> dict:
    case_dict = case_in.model_dump(by_alias=True)

    client_obj = ClientDetailsOut(
        name=case_in.clientName,
        email=case_in.clientEmail,
        phone=case_in.clientPhone
    )
    case_dict["client"] = client_obj.model_dump(exclude_none=True)

    case_dict.pop("clientName", None)
    case_dict.pop("clientEmail", None)
    case_dict.pop("clientPhone", None)

    case_dict["owner_id"] = owner.id
    case_dict["created_at"] = datetime.now(timezone.utc)

    result = db.cases.insert_one(case_dict)
    new_case = db.cases.find_one({"_id": result.inserted_id})

    if not new_case:
        raise HTTPException(status_code=500, detail="Failed to create case.")

    return {
        "id": str(new_case["_id"]),
        "case_name": new_case["case_name"],
        "client": new_case.get("client"),
        "status": new_case.get("status", "active"),
        "owner_id": str(new_case["owner_id"]),
        "created_at": new_case.get("created_at"),
        "document_count": 0, "alert_count": 0, "event_count": 0, "finding_count": 0
    }

def get_cases_for_user(db: Database, owner: UserInDB) -> list[dict]:
    results = []
    for case in db.cases.find({"owner_id": owner.id}).sort("created_at", -1):
        results.append(get_case_by_id(db=db, case_id=case["_id"], owner=owner) or {})
    return [r for r in results if r]


def get_case_by_id(db: Database, case_id: ObjectId, owner: UserInDB) -> dict | None:
    case = db.cases.find_one({"_id": case_id, "owner_id": owner.id})
    if case:
        case_id_str = str(case_id)

        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        next_week = today_start + timedelta(days=7)

        alert_query = {
            "case_id": case_id_str,
            "status": "PENDING",
            "start_date": {
                "$gte": today_start.isoformat(),
                "$lte": next_week.isoformat()
            }
        }

        doc_count = db.documents.count_documents({"case_id": case_id})
        event_count = db.calendar_events.count_documents({"case_id": case_id_str})
        finding_count = db.findings.count_documents({"case_id": case_id_str})

        calculated_alerts = db.calendar_events.count_documents(alert_query)

        counts = {
            "document_count": doc_count,
            "alert_count": calculated_alerts,
            "event_count": event_count,
            "finding_count": finding_count,
        }
        return {**case, **counts, "id": str(case["_id"])}
    return None

def delete_case_by_id(db: Database, case_id: ObjectId, owner: UserInDB):
    result = db.cases.delete_one({"_id": case_id, "owner_id": owner.id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Case not found.")

    case_id_str = str(case_id)
    db.documents.delete_many({"case_id": case_id})
    db.calendar_events.delete_many({"case_id": case_id_str})
    db.findings.delete_many({"case_id": case_id_str})
    db.alerts.delete_many({"case_id": case_id_str})

def create_draft_job_for_case(
    db: Database,
    case_id: ObjectId,
    job_in: DraftRequest, # <--- CORRECTED MODEL
    owner: UserInDB
) -> dict:
    """
    Validates that a case exists and belongs to the user, then dispatches a
    Celery task to process the drafting job with the correct arguments.
    """
    case = db.cases.find_one({"_id": case_id, "owner_id": owner.id})
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found or access denied."
        )

    # --- CORRECTED TASK DISPATCH ---
    task = celery_app.send_task(
        "process_drafting_job",
        args=[
            str(case_id),
            str(owner.id),
            job_in.document_type, # <--- CORRECTED FIELD
            job_in.prompt          # <--- CORRECTED FIELD
        ]
    )

    return {"job_id": task.id}