# app/models/drafting.py
# DEFINITIVE VERSION 1.1: FIX - Modified DraftRequest to include prompt, context, and case_id 
# to resolve the AttributeError crash in the /drafting endpoint.

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from .document import PyObjectId # Re-using our ObjectId helper

class TemplateClause(BaseModel):
    """Represents a single, reusable clause within a document template."""
    clause_id: str = Field(..., description="A unique identifier for the clause, e.g., 'confidentiality_period'.")
    clause_text: str = Field(..., description="The full legal text of the clause, with Jinja2 placeholders.")
    is_default: bool = Field(default=True, description="Whether this clause is included by default.")

class DocumentTemplate(BaseModel):
    """Represents a full document template stored in the database."""
    id: PyObjectId = Field(alias="_id")
    document_type: str = Field(..., description="e.g., 'NDA', 'EMPLOYMENT_CONTRACT'.")
    jurisdiction: str = Field(..., description="e.g., 'XK', 'AL', 'US-NY'.")
    favorability: str = Field(..., description="e.g., 'DISCLOSING_PARTY', 'RECEIVING_PARTY', 'NEUTRAL'.")
    template_name: str = Field(..., description="A human-readable name for the template.")
    template_content: str = Field(..., description="The main body of the document, with Jinja2 placeholders.")
    clauses: List[TemplateClause] = Field(..., description="A list of optional or conditional clauses.")

class DraftRequest(BaseModel):
    """Defines the request body for both Template and LLM-Augmented drafting."""
    
    # --- LLM-Augmented Fields (Primary Input) ---
    prompt: Optional[str] = Field(None, description="The custom prompt for LLM-Augmented Drafting.") # FIX: Added the missing 'prompt' field
    context: Optional[str] = Field(None, description="The document/case context provided to the LLM.")
    case_id: Optional[str] = Field(None, description="The ID of the current case for context.")

    # --- Template Fields (Optional for Custom Prompt) ---
    document_type: Optional[str] = Field(None, description="The type of document template to use (e.g., 'NDA').")
    jurisdiction: Optional[str] = Field(None, description="The jurisdiction for the template (e.g., 'XK').")
    favorability: Optional[str] = Field(None, description="The favorability setting for the template.")
    parameters: Optional[Dict[str, Any]] = Field(None, description="A dictionary of key-value pairs for template placeholders.")