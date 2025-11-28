"""
Core OOP models for Francisca SmartLibrary.
Aligned with your PostgreSQL schema (app_user, member, book, loan).

Shows:
- inheritance (Librarian, Member inherit from User)
- encapsulation (private attributes + @property)
- behaviour methods
"""

from datetime import date
from typing import Optional


class User:
    """
    Base class for any account in app_user.
    role is 'LIBRARIAN' or 'MEMBER'.
    """

    def __init__(
        self,
        user_id: int,
        username: str,
        role: str,
        full_name: Optional[str] = None,
        email: Optional[str] = None,
    ):
        self._user_id = user_id
        self._username = username
        self._role = role
        # For librarians, full_name/email may be derived from username
        self._full_name = full_name or username
        self._email = email or username

    # ---- properties (encapsulation) ----

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def username(self) -> str:
        return self._username

    @property
    def role(self) -> str:
        return self._role

    @property
    def full_name(self) -> str:
        return self._full_name

    @full_name.setter
    def full_name(self, value: str):
        if not value or not value.strip():
            raise ValueError("Full name cannot be empty.")
        self._full_name = value.strip()

    @property
    def email(self) -> str:
        return self._email

    @email.setter
    def email(self, value: str):
        value = value.strip()
        if "@" not in value:
            raise ValueError("Email must contain '@'.")
        self._email = value.lower()

    def __repr__(self) -> str:
        return f"<User {self._user_id} ({self._role}): {self._full_name}>"


class Librarian(User):
    """
    Librarian = user with role 'LIBRARIAN'.
    In DB: only in app_user (no separate librarian table).
    """

    def __init__(self, user_id: int, username: str, full_name: Optional[str] = None):
        # full_name may be friendly label for display
        super().__init__(
            user_id=user_id,
            username=username,
            role="LIBRARIAN",
            full_name=full_name or username,
            email=username,
        )

    def can_manage_inventory(self: bool):
        return True

    def __repr__(self) -> str:
        return f"<Librarian {self.user_id}: {self.full_name}>"


class Member(User):
    """
    Member = app_user row with role 'MEMBER'
    + linked row in member table (member_id, full_name, email).
    """

    def __init__(
        self,
        user_id: int,
        username: str,
        member_id: int,
        full_name: str,
        email: str,
    ):
        super().__init__(
            user_id=user_id,
            username=username,
            role="MEMBER",
            full_name=full_name,
            email=email,
        )
        self._member_id = member_id

    @property
    def member_id(self) -> int:
        return self._member_id

    def can_borrow_books(self) -> bool:
        return True

    def __repr__(self) -> str:
        return f"<Member {self.member_id}: {self.full_name}>"


class Book:
    """
    Represents a row from book JOIN author.

    book table:
      book_id, isbn, title, author_id, genre, total_copies, available_copies
    author table:
      author_id, name
    """

    def __init__(
        self,
        book_id: int,
        isbn: str,
        title: str,
        author_name: str,
        genre: str,
        total_copies: int,
        available_copies: int,
    ):
        self._book_id = book_id
        self.isbn = isbn
        self.title = title
        self.author_name = author_name
        self.genre = genre
        self.total_copies = total_copies
        self.available_copies = available_copies

    @property
    def book_id(self) -> int:
        return self._book_id

    @property
    def isbn(self) -> str:
        return self._isbn

    @isbn.setter
    def isbn(self, value: str):
        if not value or not value.strip():
            raise ValueError("ISBN cannot be empty.")
        self._isbn = value.strip()

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str):
        if not value or not value.strip():
            raise ValueError("Title cannot be empty.")
        self._title = value.strip()

    @property
    def author_name(self) -> str:
        return self._author_name

    @author_name.setter
    def author_name(self, value: str):
        if not value or not value.strip():
            raise ValueError("Author name cannot be empty.")
        self._author_name = value.strip()

    @property
    def genre(self) -> str:
        return self._genre

    @genre.setter
    def genre(self, value: str):
        self._genre = value.strip() or "Unknown"

    @property
    def total_copies(self) -> int:
        return self._total_copies

    @total_copies.setter
    def total_copies(self, value: int):
        if value < 0:
            raise ValueError("Total copies cannot be negative.")
        self._total_copies = value

    @property
    def available_copies(self) -> int:
        return self._available_copies

    @available_copies.setter
    def available_copies(self, value: int):
        if value < 0:
            raise ValueError("Available copies cannot be negative.")
        self._available_copies = value

    def __repr__(self) -> str:
        return (
            f"<Book {self.book_id}: {self.title} by {self.author_name} "
            f"({self.available_copies}/{self.total_copies} available)>"
        )


class Loan:
    """
    Represents a row from loan JOIN member JOIN book JOIN author.
    """

    def __init__(
        self,
        loan_id: int,
        member: Member,
        book: Book,
        loan_date: date,
        due_date: date,
        return_date: Optional[date],
    ):
        self._loan_id = loan_id
        self._member = member
        self._book = book
        self._loan_date = loan_date
        self._due_date = due_date
        self._return_date = return_date

    @property
    def loan_id(self) -> int:
        return self._loan_id

    @property
    def member(self) -> Member:
        return self._member

    @property
    def book(self) -> Book:
        return self._book

    @property
    def loan_date(self) -> date:
        return self._loan_date

    @property
    def due_date(self) -> date:
        return self._due_date

    @property
    def return_date(self) -> Optional[date]:
        return self._return_date

    @return_date.setter
    def return_date(self, value: Optional[date]):
        self._return_date = value

    def is_overdue(self, today: Optional[date] = None) -> bool:
        if today is None:
            today = date.today()
        return self._return_date is None and today > self._due_date

    def __repr__(self) -> str:
        status = "returned" if self._return_date else "active"
        return f"<Loan {self._loan_id} {status}: {self.book.title} to {self.member.full_name}>"
