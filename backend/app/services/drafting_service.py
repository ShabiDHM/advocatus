# FILE: backend/app/services/drafting_service.py
# PHOENIX PROTOCOL MODIFICATION: Groq Model Update to Currently Supported Version
# CORRECTION: Updated default Groq model to 'llama-3.3-70b-versatile' 
# which is currently supported in production

import os
import asyncio
import structlog
from typing import AsyncGenerator, Optional, List, Any, cast, Dict
from groq import AsyncGroq
from groq.types.chat import ChatCompletionMessageParam
from pymongo.database import Database

from ..models.user import UserInDB
from app.services.text_sterilization_service import sterilize_text_for_llm 

logger = structlog.get_logger(__name__)

def _get_template_augmentation(draft_type: str, jurisdiction: str, favorability: Optional[str], db: Database) -> Optional[str]:
    template_filter = {
        "document_type": draft_type,
        "jurisdiction": jurisdiction,
        "favorability": favorability
    }
    template = db.document_templates.find_one(template_filter)
    if not template:
        return None
    try:
        augmentation_text = f"The generated document MUST be a {draft_type} for the jurisdiction of {jurisdiction}."
        clauses_text = "\n".join([
            clause.get("clause_text", "") for clause in template.get("clauses", [])
            if clause.get("is_default", False)
        ])
        if clauses_text:
            augmentation_text += f"\n\nInclude the following mandatory clause text:\n{clauses_text}"
        return augmentation_text
    except Exception as e:
        logger.error("drafting_service.template_augmentation_error", error=str(e), exc_info=True)
        return None

async def generate_draft_stream(
    context: str,
    prompt_text: str,
    user: UserInDB,
    draft_type: Optional[str] = None,
    case_id: Optional[str] = None,
    jurisdiction: Optional[str] = None,
    favorability: Optional[str] = None,
    db: Optional[Database] = None
) -> AsyncGenerator[str, None]:
    log = logger.bind(case_id=case_id, user_id=str(user.id), draft_type=draft_type, jurisdiction=jurisdiction)
    if prompt_text is None:
        prompt_text = ""
    log.info("drafting_service.stream_start", prompt_length=len(prompt_text))

    sanitized_context = sterilize_text_for_llm(context)
    sanitized_prompt_text = sterilize_text_for_llm(prompt_text)
    log.info("drafting_service.inputs_sterilized")

    groq_api_key = os.environ.get("GROQ_API_KEY")
    if not groq_api_key:
        log.error("drafting_service.stream_failure", error="GROQ_API_KEY is missing.")
        raise Exception("Gabim: Shërbimi i AI nuk është konfiguruar saktë (Çelësi i API mungon).")

    # PHOENIX PROTOCOL CURE: Updated to currently supported production model
    groq_model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    log.info("drafting_service.model_selected", model=groq_model)
    
    GROQ_CLIENT = AsyncGroq(api_key=groq_api_key)
    system_prompt = (
        "You are an expert legal drafter for the legal markets of Kosovo and Albania named Phoenix. "
        "Your task is to generate a professional, well-structured document in response to the user's request. "
        "Maintain a formal, objective, and precise tone. "
        "Your response MUST be ONLY the generated legal text. Do not add any commentary. "
        "The generated text MUST be in the Albanian language."
    )
    full_prompt = f"Context:\n{sanitized_context}\n\n---\n\nPrompt:\n{sanitized_prompt_text}"

    # Use explicit None check for type safety
    if draft_type and jurisdiction and db is not None:
        template_augment = await asyncio.to_thread(_get_template_augmentation, draft_type, jurisdiction, favorability, db)
        if template_augment:
            system_prompt = system_prompt.replace("well-structured document", f"well-structured {draft_type} for {jurisdiction}")
            full_prompt = f"Template/Clause Guidance:\n{template_augment}\n\n---\n\n{full_prompt}"
            log.info("drafting_service.template_augmented", template=draft_type)

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": full_prompt}
    ]

    try:
        typed_messages = cast(List[ChatCompletionMessageParam], messages)
        stream = await GROQ_CLIENT.chat.completions.create(
            messages=typed_messages,
            model=groq_model,
            temperature=0.3,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content
        log.info("drafting_service.stream_success")
    except Exception as e:
        log.error("drafting_service.stream_failure", error=str(e), exc_info=True)
        error_message_str = str(e)
        
        if "model_decommissioned" in error_message_str or "invalid_request_error" in error_message_str:
            user_facing_error = "Gabim: Shërbimi i AI nuk po funksionon për momentin (Problemi me modelin e AI). Ju lutem kontaktoni mbështetjen."
        else:
            user_facing_error = "Gabim: Pata një problem gjatë gjenerimit të draftit. Ju lutem provoni përsëri më vonë."
        
        raise Exception(user_facing_error)


# --- Legacy Functions (No Changes) ---
def generate_draft_from_prompt(*args, **kwargs):
    raise NotImplementedError("Use generate_draft_stream instead.")
def generate_draft(*args, **kwargs):
    raise NotImplementedError("This legacy template function is not implemented.")