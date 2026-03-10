"""End-to-end tests for the AI Literacy Assessment module."""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.groups.models import Group, GroupMember
from src.literacy.models import (
    LiteracyAssessment,
    LiteracyModule,
    LiteracyProgress,
    LiteracyQuestion,
)
from src.literacy.service import (
    get_member_progress,
    get_module_questions,
    get_modules,
    seed_content,
    submit_assessment,
)
from src.literacy.schemas import AssessmentSubmit, AnswerItem


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def group_with_member(test_session: AsyncSession):
    """Create a test group with one member."""
    user = User(
        id=uuid.uuid4(),
        email=f"test-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Test Parent",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    test_session.add(user)
    await test_session.flush()

    group = Group(
        id=uuid.uuid4(),
        name="Test Family",
        type="family",
        owner_id=user.id,
    )
    test_session.add(group)
    await test_session.flush()

    member = GroupMember(
        id=uuid.uuid4(),
        group_id=group.id,
        user_id=user.id,
        role="parent",
        display_name="Test Child",
        date_of_birth=datetime(2014, 5, 15, tzinfo=timezone.utc),
    )
    test_session.add(member)
    await test_session.flush()

    return group, member


@pytest_asyncio.fixture
async def seeded_modules(test_session: AsyncSession):
    """Seed literacy content and return session."""
    count = await seed_content(test_session)
    await test_session.flush()
    return count


@pytest_asyncio.fixture
async def sample_module(test_session: AsyncSession):
    """Create a single test module with 2 questions."""
    module = LiteracyModule(
        id=uuid.uuid4(),
        title="Test Module",
        description="A test module for assessments.",
        category="fundamentals",
        difficulty_level="beginner",
        min_age=6,
        max_age=18,
        order_index=1,
        is_active=True,
    )
    test_session.add(module)
    await test_session.flush()

    q1 = LiteracyQuestion(
        id=uuid.uuid4(),
        module_id=module.id,
        question_text="What is 1+1?",
        question_type="multiple_choice",
        options=["1", "2", "3", "4"],
        correct_answer="2",
        explanation="1+1 equals 2.",
        order_index=1,
    )
    q2 = LiteracyQuestion(
        id=uuid.uuid4(),
        module_id=module.id,
        question_text="The sky is blue.",
        question_type="true_false",
        options=["True", "False"],
        correct_answer="True",
        explanation="The sky appears blue due to Rayleigh scattering.",
        order_index=2,
    )
    test_session.add_all([q1, q2])
    await test_session.flush()

    return module, [q1, q2]


# ---------------------------------------------------------------------------
# Seed Content Tests
# ---------------------------------------------------------------------------


class TestSeedContent:
    """Test seed_content creates modules and questions."""

    @pytest.mark.asyncio
    async def test_seed_creates_modules(self, test_session, seeded_modules):
        assert seeded_modules == 6

        result = await test_session.execute(select(LiteracyModule))
        modules = list(result.scalars().all())
        assert len(modules) == 6

    @pytest.mark.asyncio
    async def test_seed_creates_questions(self, test_session, seeded_modules):
        result = await test_session.execute(select(LiteracyQuestion))
        questions = list(result.scalars().all())
        # 6 modules: 3+2+3+2+3+2 = 15 questions
        assert len(questions) == 15

    @pytest.mark.asyncio
    async def test_seed_idempotent(self, test_session, seeded_modules):
        """Second seed should create 0 modules."""
        count = await seed_content(test_session)
        assert count == 0


# ---------------------------------------------------------------------------
# Module Listing Tests
# ---------------------------------------------------------------------------


class TestGetModules:
    """Test listing literacy modules."""

    @pytest.mark.asyncio
    async def test_list_all_modules(self, test_session, seeded_modules):
        modules = await get_modules(test_session)
        assert len(modules) == 6

    @pytest.mark.asyncio
    async def test_list_modules_ordered(self, test_session, seeded_modules):
        modules = await get_modules(test_session)
        indices = [m.order_index for m in modules]
        assert indices == sorted(indices)

    @pytest.mark.asyncio
    async def test_list_modules_filtered_by_min_age(self, test_session, seeded_modules):
        modules = await get_modules(test_session, min_age=12)
        # Modules with max_age >= 12: all 6 modules (all have max_age=18)
        assert len(modules) == 6

    @pytest.mark.asyncio
    async def test_list_modules_filtered_by_max_age(self, test_session, seeded_modules):
        modules = await get_modules(test_session, max_age=7)
        # Only modules with min_age <= 7: "What is AI?" (min_age=6)
        assert len(modules) == 1
        assert modules[0].title == "What is AI?"

    @pytest.mark.asyncio
    async def test_module_has_question_count(self, test_session, seeded_modules):
        modules = await get_modules(test_session)
        first = modules[0]
        assert first.question_count > 0

    @pytest.mark.asyncio
    async def test_empty_when_no_modules(self, test_session):
        modules = await get_modules(test_session)
        assert modules == []


# ---------------------------------------------------------------------------
# Questions Tests
# ---------------------------------------------------------------------------


class TestGetQuestions:
    """Test getting questions for a module."""

    @pytest.mark.asyncio
    async def test_get_questions(self, test_session, sample_module):
        module, expected_questions = sample_module
        questions = await get_module_questions(test_session, module.id)
        assert len(questions) == 2

    @pytest.mark.asyncio
    async def test_questions_ordered(self, test_session, sample_module):
        module, _ = sample_module
        questions = await get_module_questions(test_session, module.id)
        indices = [q.order_index for q in questions]
        assert indices == sorted(indices)

    @pytest.mark.asyncio
    async def test_questions_not_found(self, test_session):
        """Requesting questions for a non-existent module raises NotFoundError."""
        from src.exceptions import NotFoundError

        with pytest.raises(NotFoundError):
            await get_module_questions(test_session, uuid.uuid4())


# ---------------------------------------------------------------------------
# Assessment Submission Tests
# ---------------------------------------------------------------------------


class TestSubmitAssessment:
    """Test submitting and grading assessments."""

    @pytest.mark.asyncio
    async def test_submit_perfect_score(self, test_session, sample_module, group_with_member):
        module, questions = sample_module
        group, member = group_with_member

        data = AssessmentSubmit(
            group_id=group.id,
            member_id=member.id,
            module_id=module.id,
            answers=[
                AnswerItem(question_id=questions[0].id, selected_answer="2"),
                AnswerItem(question_id=questions[1].id, selected_answer="True"),
            ],
        )

        result = await submit_assessment(test_session, data)
        assert result.score == 100.0
        assert result.correct_count == 2
        assert result.total_questions == 2

    @pytest.mark.asyncio
    async def test_submit_partial_score(self, test_session, sample_module, group_with_member):
        module, questions = sample_module
        group, member = group_with_member

        data = AssessmentSubmit(
            group_id=group.id,
            member_id=member.id,
            module_id=module.id,
            answers=[
                AnswerItem(question_id=questions[0].id, selected_answer="2"),
                AnswerItem(question_id=questions[1].id, selected_answer="False"),
            ],
        )

        result = await submit_assessment(test_session, data)
        assert result.score == 50.0
        assert result.correct_count == 1

    @pytest.mark.asyncio
    async def test_submit_zero_score(self, test_session, sample_module, group_with_member):
        module, questions = sample_module
        group, member = group_with_member

        data = AssessmentSubmit(
            group_id=group.id,
            member_id=member.id,
            module_id=module.id,
            answers=[
                AnswerItem(question_id=questions[0].id, selected_answer="3"),
                AnswerItem(question_id=questions[1].id, selected_answer="False"),
            ],
        )

        result = await submit_assessment(test_session, data)
        assert result.score == 0.0
        assert result.correct_count == 0

    @pytest.mark.asyncio
    async def test_submit_creates_assessment_record(self, test_session, sample_module, group_with_member):
        module, questions = sample_module
        group, member = group_with_member

        data = AssessmentSubmit(
            group_id=group.id,
            member_id=member.id,
            module_id=module.id,
            answers=[
                AnswerItem(question_id=questions[0].id, selected_answer="2"),
                AnswerItem(question_id=questions[1].id, selected_answer="True"),
            ],
        )

        result = await submit_assessment(test_session, data)

        # Verify DB record
        db_result = await test_session.execute(
            select(LiteracyAssessment).where(
                LiteracyAssessment.id == result.id,
            )
        )
        assessment = db_result.scalar_one_or_none()
        assert assessment is not None
        assert assessment.score == 100.0

    @pytest.mark.asyncio
    async def test_submit_results_include_explanations(self, test_session, sample_module, group_with_member):
        module, questions = sample_module
        group, member = group_with_member

        data = AssessmentSubmit(
            group_id=group.id,
            member_id=member.id,
            module_id=module.id,
            answers=[
                AnswerItem(question_id=questions[0].id, selected_answer="3"),
                AnswerItem(question_id=questions[1].id, selected_answer="True"),
            ],
        )

        result = await submit_assessment(test_session, data)
        # Wrong answer should show correct answer and explanation
        wrong = [r for r in result.results if not r.is_correct]
        assert len(wrong) == 1
        assert wrong[0].correct_answer == "2"
        assert wrong[0].explanation == "1+1 equals 2."

    @pytest.mark.asyncio
    async def test_submit_invalid_module(self, test_session, group_with_member):
        from src.exceptions import NotFoundError

        group, member = group_with_member
        data = AssessmentSubmit(
            group_id=group.id,
            member_id=member.id,
            module_id=uuid.uuid4(),
            answers=[
                AnswerItem(question_id=uuid.uuid4(), selected_answer="x"),
            ],
        )
        with pytest.raises(NotFoundError):
            await submit_assessment(test_session, data)

    @pytest.mark.asyncio
    async def test_submit_invalid_question_id(self, test_session, sample_module, group_with_member):
        from src.exceptions import ValidationError

        module, questions = sample_module
        group, member = group_with_member
        data = AssessmentSubmit(
            group_id=group.id,
            member_id=member.id,
            module_id=module.id,
            answers=[
                AnswerItem(question_id=uuid.uuid4(), selected_answer="x"),
            ],
        )
        with pytest.raises(ValidationError, match="does not belong"):
            await submit_assessment(test_session, data)


# ---------------------------------------------------------------------------
# Progress Tests
# ---------------------------------------------------------------------------


class TestProgress:
    """Test member progress tracking."""

    @pytest.mark.asyncio
    async def test_default_progress(self, test_session, group_with_member):
        group, member = group_with_member
        progress = await get_member_progress(test_session, group.id, member.id)
        assert progress.modules_completed == 0
        assert progress.total_score == 0.0
        assert progress.current_level == "beginner"

    @pytest.mark.asyncio
    async def test_progress_after_assessment(self, test_session, sample_module, group_with_member):
        module, questions = sample_module
        group, member = group_with_member

        data = AssessmentSubmit(
            group_id=group.id,
            member_id=member.id,
            module_id=module.id,
            answers=[
                AnswerItem(question_id=questions[0].id, selected_answer="2"),
                AnswerItem(question_id=questions[1].id, selected_answer="True"),
            ],
        )
        await submit_assessment(test_session, data)

        progress = await get_member_progress(test_session, group.id, member.id)
        assert progress.modules_completed == 1
        assert progress.total_score == 100.0
        assert progress.current_level == "beginner"  # Only 1 module, stays beginner

    @pytest.mark.asyncio
    async def test_progress_persisted(self, test_session, sample_module, group_with_member):
        module, questions = sample_module
        group, member = group_with_member

        data = AssessmentSubmit(
            group_id=group.id,
            member_id=member.id,
            module_id=module.id,
            answers=[
                AnswerItem(question_id=questions[0].id, selected_answer="2"),
                AnswerItem(question_id=questions[1].id, selected_answer="True"),
            ],
        )
        await submit_assessment(test_session, data)

        # Verify DB row
        result = await test_session.execute(
            select(LiteracyProgress).where(
                LiteracyProgress.group_id == group.id,
                LiteracyProgress.member_id == member.id,
            )
        )
        row = result.scalar_one_or_none()
        assert row is not None
        assert row.modules_completed == 1

    @pytest.mark.asyncio
    async def test_progress_updates_on_second_module(self, test_session, group_with_member):
        """Completing a second module updates the progress count."""
        group, member = group_with_member

        # Create two modules with questions
        modules_data = []
        for i in range(2):
            mod = LiteracyModule(
                id=uuid.uuid4(),
                title=f"Module {i + 1}",
                description=f"Test module {i + 1}",
                category="fundamentals",
                difficulty_level="beginner",
                min_age=6,
                max_age=18,
                order_index=i + 1,
                is_active=True,
            )
            test_session.add(mod)
            await test_session.flush()

            q = LiteracyQuestion(
                id=uuid.uuid4(),
                module_id=mod.id,
                question_text=f"Question for module {i + 1}?",
                question_type="true_false",
                options=["True", "False"],
                correct_answer="True",
                explanation=f"Explanation {i + 1}.",
                order_index=1,
            )
            test_session.add(q)
            await test_session.flush()
            modules_data.append((mod, q))

        # Submit first module
        await submit_assessment(
            test_session,
            AssessmentSubmit(
                group_id=group.id,
                member_id=member.id,
                module_id=modules_data[0][0].id,
                answers=[
                    AnswerItem(
                        question_id=modules_data[0][1].id,
                        selected_answer="True",
                    )
                ],
            ),
        )

        # Submit second module
        await submit_assessment(
            test_session,
            AssessmentSubmit(
                group_id=group.id,
                member_id=member.id,
                module_id=modules_data[1][0].id,
                answers=[
                    AnswerItem(
                        question_id=modules_data[1][1].id,
                        selected_answer="True",
                    )
                ],
            ),
        )

        progress = await get_member_progress(test_session, group.id, member.id)
        assert progress.modules_completed == 2
        assert progress.total_score == 100.0
