import unittest
from unittest.mock import MagicMock
from uuid import uuid4
from sqlalchemy.orm import Session
from app.repositories.book_repository import BookRepository
from app.schemas import BookCreate, BookResponse
from app.models.book import Book


class TestBookRepositoryMock(unittest.TestCase):
    def setUp(self):
        self.mock_session = MagicMock(spec=Session)
        self.repo = BookRepository(self.mock_session)

    def test_create_book(self):
        # Arrange
        book_in = BookCreate(title="Mock Book", author="Mock Author", isbn="12345")

        # Mock session.refresh to populate generated fields
        def mock_refresh(obj):
            obj.id = uuid4()
            from datetime import datetime

            obj.created_at = datetime.now()
            obj.updated_at = datetime.now()

        self.mock_session.refresh.side_effect = mock_refresh

        # Act
        result = self.repo.create(book_in)

        # Assert
        self.mock_session.add.assert_called_once()
        self.mock_session.commit.assert_called_once()
        self.mock_session.refresh.assert_called_once()
        self.assertIsInstance(result, BookResponse)
        self.assertEqual(result.title, "Mock Book")
        self.assertIsNotNone(result.id)
        self.assertIsNotNone(result.created_at)

    def test_get_book(self):
        # Arrange
        book_id = uuid4()
        from datetime import datetime

        now = datetime.now()
        mock_book = Book(
            id=book_id,
            title="Test",
            author="A",
            isbn="1",
            total_copies=1,
            available_copies=1,
            created_at=now,
            updated_at=now,
        )

        # Prepare the mock scalar_one_or_none return
        self.mock_session.execute.return_value.scalar_one_or_none.return_value = (
            mock_book
        )

        # Act
        result = self.repo.get(book_id)

        # Assert
        self.mock_session.execute.assert_called_once()
        self.assertIsNotNone(result)
        self.assertEqual(result.id, book_id)
