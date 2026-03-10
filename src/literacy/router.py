"""AI Literacy Assessment API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.database import get_db
from src.dependencies import require_active_trial_or_subscription, resolve_group_id as _gid
from src.literacy.schemas import (
    AssessmentResponse,
    AssessmentSubmit,
    ModuleResponse,
    ProgressResponse,
    QuestionResponse,
)
from src.literacy.service import (
    get_member_progress,
    get_module_questions,
    get_modules,
    seed_content,
    submit_assessment,
)
from src.schemas import GroupContext

router = APIRouter(dependencies=[Depends(require_active_trial_or_subscription)])


@router.get("/modules", response_model=list[ModuleResponse])
async def list_modules(
    min_age: int | None = Query(None, ge=0, description="Filter modules suitable for this minimum age"),
    max_age: int | None = Query(None, ge=0, description="Filter modules suitable for this maximum age"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List available literacy modules, optionally filtered by age range."""
    return await get_modules(db, min_age=min_age, max_age=max_age)


@router.get("/modules/{module_id}/questions", response_model=list[QuestionResponse])
async def list_questions(
    module_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get questions for a specific module. Correct answers are hidden."""
    questions = await get_module_questions(db, module_id)
    return [
        QuestionResponse(
            id=q.id,
            module_id=q.module_id,
            question_text=q.question_text,
            question_type=q.question_type,
            options=q.options,
            order_index=q.order_index,
        )
        for q in questions
    ]


@router.post("/assessments", response_model=AssessmentResponse)
async def submit(
    data: AssessmentSubmit,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit assessment answers and receive graded results."""
    return await submit_assessment(db, data)


@router.get("/progress/{member_id}", response_model=ProgressResponse)
async def get_progress(
    member_id: UUID,
    group_id: UUID | None = Query(None, description="Group ID"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get literacy progress for a specific member."""
    gid = _gid(group_id, auth)
    return await get_member_progress(db, gid, member_id)


@router.post("/seed")
async def seed(
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Seed literacy modules and questions. Idempotent — skips if content exists."""
    count = await seed_content(db)
    return {"modules_created": count}
