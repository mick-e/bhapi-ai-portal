"""AI Literacy Assessment database models."""

import uuid

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models import JSONType, TimestampMixin, UUIDMixin


class LiteracyModule(Base, UUIDMixin, TimestampMixin):
    """An AI literacy learning module."""

    __tablename__ = "literacy_modules"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(2000), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    difficulty_level: Mapped[str] = mapped_column(String(20), nullable=False)  # beginner, intermediate, advanced
    min_age: Mapped[int] = mapped_column(Integer, nullable=False, default=6)
    max_age: Mapped[int] = mapped_column(Integer, nullable=False, default=18)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    questions: Mapped[list["LiteracyQuestion"]] = relationship(
        back_populates="module", lazy="selectin"
    )


class LiteracyQuestion(Base, UUIDMixin, TimestampMixin):
    """A question within a literacy module."""

    __tablename__ = "literacy_questions"

    module_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("literacy_modules.id"), nullable=False, index=True
    )
    question_text: Mapped[str] = mapped_column(String(1000), nullable=False)
    question_type: Mapped[str] = mapped_column(String(20), nullable=False)  # multiple_choice, true_false
    options: Mapped[dict] = mapped_column(JSONType, nullable=False)
    correct_answer: Mapped[str] = mapped_column(String(255), nullable=False)
    explanation: Mapped[str] = mapped_column(String(2000), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    module: Mapped["LiteracyModule"] = relationship(back_populates="questions")


class LiteracyAssessment(Base, UUIDMixin, TimestampMixin):
    """A completed assessment for a group member."""

    __tablename__ = "literacy_assessments"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False, index=True
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_members.id"), nullable=False, index=True
    )
    module_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("literacy_modules.id"), nullable=False, index=True
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    answers: Mapped[dict] = mapped_column(JSONType, nullable=False)
    completed_at: Mapped[None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class LiteracyProgress(Base, UUIDMixin, TimestampMixin):
    """Aggregated progress for a group member across all modules."""

    __tablename__ = "literacy_progress"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False, index=True
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_members.id"), nullable=False, index=True
    )
    modules_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    current_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default="beginner"
    )  # beginner, intermediate, advanced
