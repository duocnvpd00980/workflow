from pydantic import BaseModel
from typing import List, Optional

class PipelineRequest(BaseModel):
    business_name: str = "Sontras Sea Hotel"
    address: str = "41 Hoàng Sa Road, Son Tra District, Da Nang, Vietnam"
    industry: str = "Hotel / Beachfront Resort / Hospitality"

class PipelineResponse(BaseModel):
    success: bool
    hotel_dir: str
    competitors_clean: List[str] = []
    competitor_analysis: str = ""
    final_report: str = ""
    errors: List[str] = []

class ProgressEvent(BaseModel):
    node: str
    status: str       
    message: str
    progress: int      
    data: dict = {}