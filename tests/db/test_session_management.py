"""Test database session management."""

import pytest
from assistant.db.database import DatabaseManager


class TestDatabaseSessionManager:
    """Test database session context manager."""

    def test_context_manager(self):
        """Test that context manager works."""
        db = DatabaseManager()

        # Use context manager
        with db.get_session() as session:
            assert session is not None
            # Session should be usable
            from assistant.db.models import Conversation
            conv = session.query(Conversation).first()
            # This should not raise an error

        # Session should be closed after context exit
        # (we can't easily test this without checking internal state)

    def test_context_manager_commit(self):
        """Test that context manager commits successfully."""
        db = DatabaseManager()

        with db.get_session() as session:
            from assistant.db.models import Conversation
            # Create a test conversation
            conv = Conversation(title="Test Session Manager")
            session.add(conv)
            # Commit happens automatically on exit

        # Verify it was committed
        with db.get_session() as session:
            convs = session.query(Conversation).filter_by(title="Test Session Manager").all()
            assert len(convs) >= 1

            # Cleanup
            for conv in convs:
                session.delete(conv)

    def test_context_manager_rollback(self):
        """Test that context manager rolls back on error."""
        db = DatabaseManager()

        with db.get_session() as session:
            from assistant.db.models import Conversation
            initial_count = session.query(Conversation).count()

        try:
            with db.get_session() as session:
                from assistant.db.models import Conversation
                conv = Conversation(title="Test Rollback")
                session.add(conv)
                # Raise error to trigger rollback
                raise ValueError("Test error")
        except ValueError:
            pass

        # Count should be unchanged (rollback happened)
        with db.get_session() as session:
            final_count = session.query(Conversation).count()
            assert initial_count == final_count


class TestDatabaseManagerBackwardCompatibility:
    """Test that existing DatabaseManager methods still work."""

    def test_existing_methods_work(self):
        """Test that existing methods don't break."""
        db = DatabaseManager()

        # Test create_conversation (creates its own session)
        db.create_conversation("Test Backward Compat")

        # Verify it was created by querying in a new session
        with db.get_session() as session:
            from assistant.db.models import Conversation
            conv = session.query(Conversation).filter_by(title="Test Backward Compat").first()
            assert conv is not None
            assert conv.title == "Test Backward Compat"

            # Cleanup
            session.delete(conv)

    def test_session_still_accessible(self):
        """Test that get_session() provides a usable session."""
        db = DatabaseManager()

        # get_session() should provide a usable session
        with db.get_session() as session:
            assert session is not None

            # Can use it directly
            from assistant.db.models import Conversation
            conv = session.query(Conversation).first()

            # This is valid
            assert conv is None or isinstance(conv, Conversation)
