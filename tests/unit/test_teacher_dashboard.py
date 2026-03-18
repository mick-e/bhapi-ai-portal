"""Unit tests for teacher dashboard."""

import pytest
from uuid import uuid4
from tests.conftest import make_test_group
from src.groups.teacher_dashboard import (
    create_note, list_notes_for_member, mark_note_read,
)
from src.exceptions import NotFoundError


@pytest.mark.asyncio
class TestTeacherDashboard:
    async def test_create_note(self, test_session):
        group, owner_id = await make_test_group(test_session, group_type="school")
        member_id = uuid4()
        note = await create_note(
            test_session, group_id=group.id, member_id=member_id,
            author_id=owner_id, author_role="teacher",
            subject="AI Usage Report", body="Student showed good progress.",
        )
        assert note.subject == "AI Usage Report"

    async def test_list_notes(self, test_session):
        group, owner_id = await make_test_group(test_session, group_type="school")
        member_id = uuid4()
        await create_note(test_session, group.id, member_id, owner_id, "teacher", "Note 1", "Body 1")
        await create_note(test_session, group.id, member_id, owner_id, "parent", "Note 2", "Body 2")
        notes = await list_notes_for_member(test_session, group.id, member_id)
        assert len(notes) == 2

    async def test_mark_read(self, test_session):
        group, owner_id = await make_test_group(test_session, group_type="school")
        note = await create_note(test_session, group.id, uuid4(), owner_id, "teacher", "Test", "Body")
        updated = await mark_note_read(test_session, note.id)
        assert updated.read_at is not None

    async def test_mark_nonexistent_read(self, test_session):
        with pytest.raises(NotFoundError):
            await mark_note_read(test_session, uuid4())
