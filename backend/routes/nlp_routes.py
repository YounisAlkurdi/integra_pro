from fastapi import APIRouter, Body
from ..services.forensic_service import perform_forensic_analysis

router = APIRouter(tags=["NLP Analysis Engine"])

@router.post("/api/analyze-forensics")
async def analyze_text(
    text: str = Body(..., embed=True),
    question: str = Body("", embed=True)
):
    """
    Consolidated forensic NLP analysis for candidate responses.
    Delegates logic to forensic_service.py
    """
    return await perform_forensic_analysis(text, question)
