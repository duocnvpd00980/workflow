from fastapi import APIRouter, HTTPException, Query
from app.research.research_service import run_research
from fastapi import APIRouter, Depends
from .schemas import TestPipelineRequest

router = APIRouter(
    prefix="/research",
    tags=["Research"],
)


@router.post("/test")
async def test_pipeline(
    payload: TestPipelineRequest = Depends(),
):

    await payload.validate_fb_exists()

    result = await run_research(
        query=payload.query,
        fb_url=payload.fb_url,
        business_id=payload.business_id,
        business_name=payload.business_name,
    )

    return result

