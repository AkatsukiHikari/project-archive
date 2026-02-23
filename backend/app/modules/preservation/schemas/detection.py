from typing import Dict, Any
from pydantic import BaseModel

class DetectionResult(BaseModel):
    is_valid: bool
    details: Dict[str, Any]
    score: float
