"""AI Literacy Assessment service — business logic."""

from uuid import UUID, uuid4

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import NotFoundError, ValidationError
from src.literacy.content import SEED_MODULES
from src.literacy.models import (
    LiteracyAssessment,
    LiteracyModule,
    LiteracyProgress,
    LiteracyQuestion,
)
from src.literacy.schemas import (
    AssessmentResponse,
    AssessmentSubmit,
    ModuleResponse,
    ProgressResponse,
    QuestionResult,
)

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Module queries
# ---------------------------------------------------------------------------


async def get_modules(
    db: AsyncSession,
    min_age: int | None = None,
    max_age: int | None = None,
) -> list[ModuleResponse]:
    """List active literacy modules, optionally filtered by age range."""
    query = select(LiteracyModule).where(LiteracyModule.is_active.is_(True))

    if min_age is not None:
        query = query.where(LiteracyModule.max_age >= min_age)
    if max_age is not None:
        query = query.where(LiteracyModule.min_age <= max_age)

    query = query.order_by(LiteracyModule.order_index)
    result = await db.execute(query)
    modules = list(result.scalars().all())

    return [_module_to_response(m) for m in modules]


async def get_module_questions(
    db: AsyncSession,
    module_id: UUID,
) -> list[LiteracyQuestion]:
    """Get questions for a module. Raises NotFoundError if module missing."""
    # Verify module exists
    mod_result = await db.execute(
        select(LiteracyModule).where(LiteracyModule.id == module_id)
    )
    module = mod_result.scalar_one_or_none()
    if not module:
        raise NotFoundError("LiteracyModule", str(module_id))

    result = await db.execute(
        select(LiteracyQuestion)
        .where(LiteracyQuestion.module_id == module_id)
        .order_by(LiteracyQuestion.order_index)
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Assessment grading
# ---------------------------------------------------------------------------


async def submit_assessment(
    db: AsyncSession,
    data: AssessmentSubmit,
) -> AssessmentResponse:
    """Grade an assessment, create a record, and update progress."""
    # Verify module exists
    mod_result = await db.execute(
        select(LiteracyModule).where(LiteracyModule.id == data.module_id)
    )
    module = mod_result.scalar_one_or_none()
    if not module:
        raise NotFoundError("LiteracyModule", str(data.module_id))

    # Fetch questions for grading
    q_result = await db.execute(
        select(LiteracyQuestion).where(LiteracyQuestion.module_id == data.module_id)
    )
    questions = {q.id: q for q in q_result.scalars().all()}

    if not questions:
        raise ValidationError("This module has no questions to assess.")

    # Grade each answer
    results: list[QuestionResult] = []
    correct_count = 0

    for answer in data.answers:
        question = questions.get(answer.question_id)
        if not question:
            raise ValidationError(
                f"Question {answer.question_id} does not belong to this module."
            )

        is_correct = answer.selected_answer == question.correct_answer
        if is_correct:
            correct_count += 1

        results.append(
            QuestionResult(
                question_id=answer.question_id,
                selected_answer=answer.selected_answer,
                correct_answer=question.correct_answer,
                is_correct=is_correct,
                explanation=question.explanation,
            )
        )

    total_questions = len(data.answers)
    score = (correct_count / total_questions) * 100.0 if total_questions > 0 else 0.0

    # Persist assessment record
    assessment = LiteracyAssessment(
        id=uuid4(),
        group_id=data.group_id,
        member_id=data.member_id,
        module_id=data.module_id,
        score=score,
        answers={
            str(a.question_id): a.selected_answer for a in data.answers
        },
    )
    db.add(assessment)
    await db.flush()
    await db.refresh(assessment)

    # Update progress
    await _update_progress(db, data.group_id, data.member_id)

    logger.info(
        "literacy_assessment_submitted",
        assessment_id=str(assessment.id),
        module_id=str(data.module_id),
        member_id=str(data.member_id),
        score=score,
        correct=correct_count,
        total=total_questions,
    )

    return AssessmentResponse(
        id=assessment.id,
        group_id=assessment.group_id,
        member_id=assessment.member_id,
        module_id=assessment.module_id,
        score=score,
        total_questions=total_questions,
        correct_count=correct_count,
        results=results,
        completed_at=assessment.completed_at,
    )


# ---------------------------------------------------------------------------
# Progress
# ---------------------------------------------------------------------------


async def get_member_progress(
    db: AsyncSession,
    group_id: UUID,
    member_id: UUID,
) -> ProgressResponse:
    """Get aggregated progress for a member."""
    result = await db.execute(
        select(LiteracyProgress).where(
            LiteracyProgress.group_id == group_id,
            LiteracyProgress.member_id == member_id,
        )
    )
    progress = result.scalar_one_or_none()

    if not progress:
        # Return default progress
        return ProgressResponse(
            member_id=member_id,
            group_id=group_id,
            modules_completed=0,
            total_score=0.0,
            current_level="beginner",
        )

    return ProgressResponse(
        member_id=progress.member_id,
        group_id=progress.group_id,
        modules_completed=progress.modules_completed,
        total_score=progress.total_score,
        current_level=progress.current_level,
        created_at=progress.created_at,
        updated_at=progress.updated_at,
    )


async def _update_progress(
    db: AsyncSession,
    group_id: UUID,
    member_id: UUID,
) -> None:
    """Recalculate and upsert progress for a member."""
    # Count distinct modules completed
    count_result = await db.execute(
        select(func.count(func.distinct(LiteracyAssessment.module_id))).where(
            LiteracyAssessment.group_id == group_id,
            LiteracyAssessment.member_id == member_id,
        )
    )
    modules_completed = count_result.scalar() or 0

    # Average score across best attempt per module
    avg_result = await db.execute(
        select(func.avg(LiteracyAssessment.score)).where(
            LiteracyAssessment.group_id == group_id,
            LiteracyAssessment.member_id == member_id,
        )
    )
    total_score = avg_result.scalar() or 0.0

    # Determine level
    if modules_completed >= 5 and total_score >= 70:
        level = "advanced"
    elif modules_completed >= 3 and total_score >= 50:
        level = "intermediate"
    else:
        level = "beginner"

    # Upsert progress
    result = await db.execute(
        select(LiteracyProgress).where(
            LiteracyProgress.group_id == group_id,
            LiteracyProgress.member_id == member_id,
        )
    )
    progress = result.scalar_one_or_none()

    if progress:
        progress.modules_completed = modules_completed
        progress.total_score = total_score
        progress.current_level = level
    else:
        progress = LiteracyProgress(
            id=uuid4(),
            group_id=group_id,
            member_id=member_id,
            modules_completed=modules_completed,
            total_score=total_score,
            current_level=level,
        )
        db.add(progress)

    await db.flush()


# ---------------------------------------------------------------------------
# Seed content
# ---------------------------------------------------------------------------


async def seed_content(db: AsyncSession) -> int:
    """Seed literacy modules and questions. Returns count of modules created."""
    # Check if modules already exist
    existing = await db.execute(select(func.count(LiteracyModule.id)))
    if (existing.scalar() or 0) > 0:
        return 0

    created = 0
    for module_data in SEED_MODULES:
        questions_data = module_data.pop("questions")
        module = LiteracyModule(id=uuid4(), **module_data)
        db.add(module)
        await db.flush()

        for q_data in questions_data:
            question = LiteracyQuestion(id=uuid4(), module_id=module.id, **q_data)
            db.add(question)

        # Restore questions for idempotency
        module_data["questions"] = questions_data
        created += 1

    await db.flush()

    logger.info("literacy_content_seeded", modules_created=created)
    return created


# ---------------------------------------------------------------------------
# Response builders
# ---------------------------------------------------------------------------


def _module_to_response(module: LiteracyModule) -> ModuleResponse:
    """Convert LiteracyModule model to ModuleResponse schema."""
    return ModuleResponse(
        id=module.id,
        title=module.title,
        description=module.description,
        category=module.category,
        difficulty_level=module.difficulty_level,
        min_age=module.min_age,
        max_age=module.max_age,
        order_index=module.order_index,
        is_active=module.is_active,
        question_count=len(module.questions) if module.questions else 0,
    )
