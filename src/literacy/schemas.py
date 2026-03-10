"""AI Literacy Assessment Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from src.schemas import BaseSchema


class QuestionResponse(BaseSchema):
    """Question response — correct_answer is intentionally omitted."""

    id: UUID
    module_id: UUID
    question_text: str
    question_type: str
    options: list[str]
    order_index: int


class ModuleResponse(BaseSchema):
    """Literacy module response."""

    id: UUID
    title: str
    description: str
    category: str
    difficulty_level: str
    min_age: int
    max_age: int
    order_index: int
    is_active: bool
    question_count: int = 0


class AnswerItem(BaseSchema):
    """A single answer within an assessment submission."""

    question_id: UUID
    selected_answer: str


class AssessmentSubmit(BaseSchema):
    """Submit answers for a module assessment."""

    group_id: UUID
    member_id: UUID
    module_id: UUID
    answers: list[AnswerItem] = Field(min_length=1)


class QuestionResult(BaseSchema):
    """Result for a single question in an assessment."""

    question_id: UUID
    selected_answer: str
    correct_answer: str
    is_correct: bool
    explanation: str


class AssessmentResponse(BaseSchema):
    """Assessment result after grading."""

    id: UUID
    group_id: UUID
    member_id: UUID
    module_id: UUID
    score: float
    total_questions: int
    correct_count: int
    results: list[QuestionResult]
    completed_at: datetime


class ProgressResponse(BaseSchema):
    """Member progress across all literacy modules."""

    member_id: UUID
    group_id: UUID
    modules_completed: int
    total_score: float
    current_level: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
