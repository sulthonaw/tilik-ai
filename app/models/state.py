"""LangGraph AgentState TypedDict for Tilik AI fact-checking workflow."""

from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict

from app.models.schemas import VerificationResponse


class AgentState(TypedDict, total=False):
    """Workflow state passed through LangGraph nodes."""

    # Input parameters
    raw_text: str
    source_platform: Optional[str]

    # Node 1: NER & Slang Resolution
    slang_candidates: List[Dict[str, Any]]
    detected_ticker: Optional[str]
    company_name: Optional[str]
    detected_slangs: List[str]

    # Node 2: Intent & Claim Classification
    claims: List[Dict[str, Any]]  # List of identified claims with intent/sentiment

    # Node 3: Sectors API Data Fetcher
    sectors_data: Dict[str, Any]
    fetch_errors: List[str]

    # Node 4: Evaluator & Anomaly Detection
    evaluation: Dict[str, Any]

    # Node 5: Synthesizer
    response: Optional[VerificationResponse]

    # Error handling
    error: Optional[str]
