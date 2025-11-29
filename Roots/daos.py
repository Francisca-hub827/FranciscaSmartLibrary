"""
DAO layer for Francisca SmartLibrary using your real PostgreSQL schema.

Schema (from your script):
- app_user(user_id, username, password_hash, role)
- member(member_id, full_name, email, user_id)
- author(author_id, name)
- book(book_id, isbn, title, author_id, genre, total_copies, available_copies)
- loan(loan_id, member_id, book_id, loan_date, due_date, return_date)

We use pgcrypto's crypt() for password checking.
"""

from datetime import date, timedelta
from typing import List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

from .models import Librarian, Member, Book, Loan


# ========== DB CONFIG – MATCHES YOUR SCRIPT ==========

DB_CONFIG = {
    "dbname": "SmartLibrary",     # from GRANT CONNECT ON DATABASE "SmartLibrary"
    "user": "smartlib_user",      # created in your script
    "password": "smartlib_pass",  # set in your script
    "host": "localhost",
    "port": 5432,
}


def get_connection():
    """
    Open a connection to PostgreSQL with RealDictCursor
    so we can access row["column"].
    """
    return psycopg2.connect(**DB_CONFIG)


# For nicer librarian display names (since app_user has only username)
LIBRARIAN_DISPLAY_NAMES = {
    "francisca.kabina@smartlibrary.edu": "Francisca Kabina",
    "abriel@smartlibrary.edu": "Abriel",   # username exactly as in your SQL
    "abubakar@smartlibrary.edu": "Abubakar",
}


# ========== AUTHENTICATION ==========


def authenticate_librarian(email: str, password: str) -> Optional[Librarian]:
    """
    Authenticate a librarian using app_user + pgcrypto.

    app_user.role = 'LIBRARIAN'
    password_hash is verified with crypt(password, password_hash).
    """
    email = email.strip().lower()

    sql = """
        SELECT user_id, username, role
        FROM app_user
        WHERE username = %s
          AND role = 'LIBRARIAN'
          AND password_hash = crypt(%s, password_hash);
    """

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (email, password))
            row = cur.fetchone()
            if not row:
                return None

            username = row["username"]
            full_name = LIBRARIAN_DISPLAY_NAMES.get(username, username)

            librarian = Librarian(
                user_id=row["user_id"],
                username=username,
                full_name=full_name,
            )
            return librarian
    finally:
        conn.close()


def authenticate_member(email: str, password: str) -> Optional[Member]:
    """
    Authenticate a member by joining app_user + member.

    - app_user.username = email
    - app_user.role = 'MEMBER'
    - app_user.password_hash is checked with crypt
    - member.user_id links to app_user.user_id
    """
    email = email.strip().lower()

    sql = """
        SELECT
            u.user_id,
            u.username,
            m.member_id,
            m.full_name,
            m.email
        FROM app_user u
        JOIN member m ON m.user_id = u.user_id
        WHERE u.username = %s
          AND u.role = 'MEMBER'
          AND u.password_hash = crypt(%s, u.password_hash);
    """

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (email, password))
            row = cur.fetchone()
            if not row:
                return None

            member = Member(
                user_id=row["user_id"],
                username=row["username"],
                member_id=row["member_id"],
                full_name=row["full_name"],
                email=row["email"],
            )
            return member
    finally:
        conn.close()


# ========== BOOK CRUD (book + author) ==========


def list_books() -> List[Book]:
    """
    Get all books, joined with their author name.
    """
    sql = """
        SELECT
            b.book_id,
            b.isbn,
            b.title,
            a.name AS author_name,
            b.genre,
            b.total_copies,
            b.available_copies
        FROM book b
        JOIN author a ON a.author_id = b.author_id
        ORDER BY b.book_id;
    """

    conn = get_connection()
    books: List[Book] = []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            for row in rows:
                books.append(
                    Book(
                        book_id=row["book_id"],
                        isbn=row["isbn"],
                        title=row["title"],
                        author_name=row["author_name"],
                        genre=row["genre"],
                        total_copies=row["total_copies"],
                        available_copies=row["available_copies"],
                    )
                )
    finally:
        conn.close()

    return books


def _get_or_create_author_id(conn, author_name: str) -> int:
    """
    Helper: find author_id for this name, or insert a new author.
    Uses existing connection/transaction.
    """
    author_name = author_name.strip()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT author_id FROM author WHERE name = %s;", (author_name,))
        row = cur.fetchone()
        if row:
            return row["author_id"]

        cur.execute(
            "INSERT INTO author(name) VALUES (%s) RETURNING author_id;",
            (author_name,),
        )
        row = cur.fetchone()
        return row["author_id"]


def add_book(title: str, author_name: str, genre: str, copies: int, isbn: str = "") -> Book:
    """
    Insert a new book. If ISBN is empty, we generate a simple placeholder.
    total_copies and available_copies both start as 'copies'.
    """
    if not isbn.strip():
        isbn = f"AUTO-{title[:3].upper()}"

    conn = get_connection()
    try:
        with conn:
            author_id = _get_or_create_author_id(conn, author_name)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO book(isbn, title, author_id, genre, total_copies, available_copies)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING
                        book_id, isbn, title, genre, total_copies, available_copies;
                    """,
                    (isbn, title, author_id, genre, copies, copies),
                )
                row = cur.fetchone()

        return Book(
            book_id=row["book_id"],
            isbn=row["isbn"],
            title=row["title"],
            author_name=author_name,
            genre=row["genre"],
            total_copies=row["total_copies"],
            available_copies=row["available_copies"],
        )
    finally:
        conn.close()


def update_book(
    book_id: int,
    title: str,
    author_name: str,
    genre: str,
    total_copies: int,
    available_copies: int,
) -> bool:
    """
    Update existing book, including author name.
    We pass both total_copies and available_copies from the GUI.
    """
    conn = get_connection()
    try:
        with conn:
            author_id = _get_or_create_author_id(conn, author_name)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE book
                    SET title = %s,
                        author_id = %s,
                        genre = %s,
                        total_copies = %s,
                        available_copies = %s
                    WHERE book_id = %s;
                    """,
                    (title, author_id, genre, total_copies, available_copies, book_id),
                )
                updated = cur.rowcount > 0
        return updated
    finally:
        conn.close()


def delete_book(book_id: int) -> bool:
    """
    Delete a book by book_id.
    """
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM book WHERE book_id = %s;", (book_id,))
                deleted = cur.rowcount > 0
        return deleted
    finally:
        conn.close()


def list_members() -> List[Member]:
    """
    Return all members as Member objects.

    Uses:
      - member(member_id, full_name, email, user_id)
      - app_user(user_id, username)

    We join app_user so we can fill both username and email.
    """
    sql = """
        SELECT
            u.user_id,
            u.username,
            m.member_id,
            m.full_name,
            m.email
        FROM member m
        JOIN app_user u ON u.user_id = m.user_id
        ORDER BY m.member_id;
    """

    conn = get_connection()
    members: List[Member] = []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            for row in rows:
                member = Member(
                    user_id=row["user_id"],
                    username=row["username"],
                    member_id=row["member_id"],
                    full_name=row["full_name"],
                    email=row["email"],
                )
                members.append(member)
    finally:
        conn.close()

    return members


# ---------- MEMBER CRUD (create / update / delete) ----------

def create_member(full_name: str, email: str, password: str) -> tuple[bool, str]:
    """
    Create a new member:

    - Inserts into app_user (username = email, role = 'MEMBER', password_hash using crypt)
    - Inserts into member(full_name, email, user_id)

    Returns: (success, message)
    """
    full_name = (full_name or "").strip()
    email = (email or "").strip().lower()
    password = (password or "").strip()

    if not full_name:
        return False, "Full name cannot be empty."
    if "@" not in email:
        return False, "Email must contain '@'."
    if len(password) < 4:
        return False, "Password should be at least 4 characters."

    conn = get_connection()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Make sure email is not already used
                cur.execute("SELECT 1 FROM app_user WHERE username = %s;", (email,))
                if cur.fetchone():
                    return False, "An account with that email already exists."

                # 1) Create app_user row
                cur.execute(
                    """
                    INSERT INTO app_user(username, password_hash, role)
                    VALUES (%s, crypt(%s, gen_salt('bf')), 'MEMBER')
                    RETURNING user_id;
                    """,
                    (email, password),
                )
                user_row = cur.fetchone()
                user_id = int(user_row["user_id"])

                # 2) Create member row
                cur.execute(
                    """
                    INSERT INTO member(full_name, email, user_id)
                    VALUES (%s, %s, %s)
                    RETURNING member_id;
                    """,
                    (full_name, email, user_id),
                )
                mem_row = cur.fetchone()
                member_id = int(mem_row["member_id"])

        return True, f"Member created successfully (ID {member_id})."
    except Exception as ex:
        # simple error text for GUI
        return False, f"Error creating member: {ex}"
    finally:
        conn.close()


def update_member(
    member_id: int,
    full_name: str,
    email: str,
    new_password: str | None = None,
) -> tuple[bool, str]:
    """
    Update an existing member's full name, email, and optionally password.

    - Updates member(full_name, email)
    - Updates app_user.username (email)
    - If new_password is provided and not empty, resets password_hash.
    """
    full_name = (full_name or "").strip()
    email = (email or "").strip().lower()
    if not full_name:
        return False, "Full name cannot be empty."
    if "@" not in email:
        return False, "Email must contain '@'."

    conn = get_connection()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Find linked user_id
                cur.execute(
                    "SELECT user_id FROM member WHERE member_id = %s;",
                    (member_id,),
                )
                row = cur.fetchone()
                if not row:
                    return False, "Member not found."
                user_id = int(row["user_id"])

                # Update member table
                cur.execute(
                    """
                    UPDATE member
                    SET full_name = %s,
                        email = %s
                    WHERE member_id = %s;
                    """,
                    (full_name, email, member_id),
                )
                if cur.rowcount == 0:
                    return False, "Member not found (update failed)."

                # Update app_user username (email)
                cur.execute(
                    """
                    UPDATE app_user
                    SET username = %s
                    WHERE user_id = %s;
                    """,
                    (email, user_id),
                )

                # Optionally update password
                new_password = (new_password or "").strip()
                if new_password:
                    cur.execute(
                        """
                        UPDATE app_user
                        SET password_hash = crypt(%s, gen_salt('bf'))
                        WHERE user_id = %s;
                        """,
                        (new_password, user_id),
                    )

        return True, "Member updated successfully."
    except Exception as ex:
        return False, f"Error updating member: {ex}"
    finally:
        conn.close()


def delete_member(member_id: int) -> tuple[bool, str]:
    """
    Delete a member and the linked app_user row.

    - Because loan.member_id and club_member.member_id use ON DELETE CASCADE,
      their rows will be removed automatically when the member row is deleted.
    """
    conn = get_connection()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get user_id before deleting member row
                cur.execute(
                    "SELECT user_id FROM member WHERE member_id = %s;",
                    (member_id,),
                )
                row = cur.fetchone()
                if not row:
                    return False, "Member not found."
                user_id = int(row["user_id"])

                # Delete member row (this will cascade to loans, club_member)
                cur.execute("DELETE FROM member WHERE member_id = %s;", (member_id,))
                if cur.rowcount == 0:
                    return False, "Member not found (nothing deleted)."

                # Delete app_user row
                cur.execute("DELETE FROM app_user WHERE user_id = %s;", (user_id,))

        return True, "Member deleted successfully."
    except Exception as ex:
        return False, f"Error deleting member: {ex}"
    finally:
        conn.close()


# ========== SIMPLE STATS FOR DASHBOARD ==========


def count_members() -> int:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM member;")
            (cnt,) = cur.fetchone()
            return int(cnt)
    finally:
        conn.close()


def count_books() -> int:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM book;")
            (cnt,) = cur.fetchone()
            return int(cnt)
    finally:
        conn.close()


def count_active_loans() -> int:
    """
    Loans that are currently not returned.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM loan WHERE return_date IS NULL;")
            (cnt,) = cur.fetchone()
            return int(cnt)
    finally:
        conn.close()


def count_clubs() -> int:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM club;")
            (cnt,) = cur.fetchone()
            return int(cnt)
    finally:
        conn.close()

# ========== BOOK CLUBS ==========

from typing import Dict  # (you already import typing at top, just be sure List, Optional are there)

def list_all_clubs() -> List[dict]:
    """Return all clubs as simple dicts."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT club_id, name, description FROM club ORDER BY club_id;"
            )
            rows = cur.fetchall()
            return list(rows)
    finally:
        conn.close()


def list_members_in_club(club_id: int) -> List[dict]:
    """Members that belong to a specific club."""
    sql = """
        SELECT m.member_id, m.full_name, m.email
        FROM club_member cm
        JOIN member m ON m.member_id = cm.member_id
        WHERE cm.club_id = %s
        ORDER BY m.member_id;
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (club_id,))
            rows = cur.fetchall()
            return list(rows)
    finally:
        conn.close()


def create_club(name: str, description: str = "") -> tuple[bool, str]:
    """Create a new club (name must be unique)."""
    name = name.strip()
    description = (description or "").strip()
    if not name:
        return False, "Club name cannot be empty."

    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO club(name, description)
                    VALUES (%s, %s)
                    ON CONFLICT (name) DO NOTHING
                    RETURNING club_id;
                    """,
                    (name, description),
                )
                row = cur.fetchone()
                if not row:
                    return False, "A club with that name already exists."
        return True, "Club created successfully."
    finally:
        conn.close()


def delete_club(club_id: int) -> tuple[bool, str]:
    """
    Delete a club. club_member rows will be removed automatically
    because of ON DELETE CASCADE.
    """
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM club WHERE club_id = %s;", (club_id,))
                if cur.rowcount == 0:
                    return False, "Club not found."
        return True, "Club deleted."
    finally:
        conn.close()


def add_member_to_club(member_id: int, club_id: int) -> tuple[bool, str]:
    """Attach a member to a club."""
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                # already inside?
                cur.execute(
                    """
                    SELECT 1 FROM club_member
                    WHERE member_id = %s AND club_id = %s;
                    """,
                    (member_id, club_id),
                )
                if cur.fetchone():
                    return False, "Member is already in this club."

                cur.execute(
                    """
                    INSERT INTO club_member(member_id, club_id)
                    VALUES (%s, %s);
                    """,
                    (member_id, club_id),
                )
        return True, "Member added to club."
    finally:
        conn.close()


def remove_member_from_club(member_id: int, club_id: int) -> tuple[bool, str]:
    """Remove a member from a club."""
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM club_member WHERE member_id = %s AND club_id = %s;",
                    (member_id, club_id),
                )
                if cur.rowcount == 0:
                    return False, "Member was not in this club."
        return True, "Member removed from club."
    finally:
        conn.close()


def list_clubs_for_member(member_id: int) -> List[dict]:
    """Clubs a member already joined."""
    sql = """
        SELECT c.club_id, c.name, c.description
        FROM club_member cm
        JOIN club c ON c.club_id = cm.club_id
        WHERE cm.member_id = %s
        ORDER BY c.name;
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (member_id,))
            rows = cur.fetchall()
            return list(rows)
    finally:
        conn.close()


def list_clubs_not_joined(member_id: int) -> List[dict]:
    """Clubs the member is NOT part of yet."""
    sql = """
        SELECT c.club_id, c.name, c.description
        FROM club c
        WHERE NOT EXISTS (
            SELECT 1 FROM club_member cm
            WHERE cm.club_id = c.club_id
              AND cm.member_id = %s
        )
        ORDER BY c.name;
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (member_id,))
            rows = cur.fetchall()
            return list(rows)
    finally:
        conn.close()



# ========== LOANS & REMINDERS ==========


def get_loans_for_member(member_id: int) -> List[Loan]:
    """
    Return all loans for a member, joined with book + author + member.
    member_id is from member.member_id (NOT app_user.user_id).
    """
    sql = """
        SELECT
            l.loan_id,
            l.loan_date,
            l.due_date,
            l.return_date,
            m.member_id,
            m.full_name,
            m.email,
            u.user_id,
            u.username,
            b.book_id,
            b.isbn,
            b.title,
            b.genre,
            b.total_copies,
            b.available_copies,
            a.name AS author_name
        FROM loan l
        JOIN member m ON m.member_id = l.member_id
        JOIN app_user u ON u.user_id = m.user_id
        JOIN book b ON b.book_id = l.book_id
        JOIN author a ON a.author_id = b.author_id
        WHERE m.member_id = %s
        ORDER BY l.loan_date DESC;
    """

    conn = get_connection()
    loans: List[Loan] = []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (member_id,))
            rows = cur.fetchall()
            for row in rows:
                member = Member(
                    user_id=row["user_id"],
                    username=row["username"],
                    member_id=row["member_id"],
                    full_name=row["full_name"],
                    email=row["email"],
                )
                book = Book(
                    book_id=row["book_id"],
                    isbn=row["isbn"],
                    title=row["title"],
                    author_name=row["author_name"],
                    genre=row["genre"],
                    total_copies=row["total_copies"],
                    available_copies=row["available_copies"],
                )
                loan = Loan(
                    loan_id=row["loan_id"],
                    member=member,
                    book=book,
                    loan_date=row["loan_date"],
                    due_date=row["due_date"],
                    return_date=row["return_date"],
                )
                loans.append(loan)
    finally:
        conn.close()

    return loans


def get_due_soon_loans_for_member(member_id: int, days: int = 3) -> List[Loan]:
    """
    Loans due in the next 'days' days, not yet returned.
    Powers your reminder popup.
    member_id is from member.member_id.
    """
    today = date.today()
    deadline = today + timedelta(days=days)

    sql = """
        SELECT
            l.loan_id,
            l.loan_date,
            l.due_date,
            l.return_date,
            m.member_id,
            m.full_name,
            m.email,
            u.user_id,
            u.username,
            b.book_id,
            b.isbn,
            b.title,
            b.genre,
            b.total_copies,
            b.available_copies,
            a.name AS author_name
        FROM loan l
        JOIN member m ON m.member_id = l.member_id
        JOIN app_user u ON u.user_id = m.user_id
        JOIN book b ON b.book_id = l.book_id
        JOIN author a ON a.author_id = b.author_id
        WHERE m.member_id = %s
          AND l.return_date IS NULL
          AND l.due_date BETWEEN %s AND %s
        ORDER BY l.due_date ASC;
    """

    conn = get_connection()
    loans: List[Loan] = []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (member_id, today, deadline))
            rows = cur.fetchall()
            for row in rows:
                member = Member(
                    user_id=row["user_id"],
                    username=row["username"],
                    member_id=row["member_id"],
                    full_name=row["full_name"],
                    email=row["email"],
                )
                book = Book(
                    book_id=row["book_id"],
                    isbn=row["isbn"],
                    title=row["title"],
                    author_name=row["author_name"],
                    genre=row["genre"],
                    total_copies=row["total_copies"],
                    available_copies=row["available_copies"],
                )
                loan = Loan(
                    loan_id=row["loan_id"],
                    member=member,
                    book=book,
                    loan_date=row["loan_date"],
                    due_date=row["due_date"],
                    return_date=row["return_date"],
                )
                loans.append(loan)
    finally:
        conn.close()

    return loans

# ========== EXTRA HELPERS FOR LOANS WINDOW,(Borrow/ return) ==========
def find_member_by_email(email: str) -> Optional[Member]:
    """
    Look up a member by email (member.email) or username (app_user.username).
    Returns a Member object or None.
    """
    email = email.strip().lower()
    if not email:
        return None

    sql = """
        SELECT
            m.member_id,
            m.full_name,
            m.email,
            u.user_id,
            u.username
        FROM member m
        JOIN app_user u ON u.user_id = m.user_id
        WHERE LOWER(m.email) = %s
           OR LOWER(u.username) = %s
        LIMIT 1;
    """

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (email, email))
            row = cur.fetchone()
            if not row:
                return None

            return Member(
                user_id=row["user_id"],
                username=row["username"],
                member_id=row["member_id"],
                full_name=row["full_name"],
                email=row["email"],
            )
    finally:
        conn.close()


def find_book_by_isbn(isbn: str) -> Optional[Book]:
    """
    Look up a book by its ISBN.
    """
    isbn = isbn.strip()
    if not isbn:
        return None

    sql = """
        SELECT
            b.book_id,
            b.isbn,
            b.title,
            b.genre,
            b.total_copies,
            b.available_copies,
            a.name AS author_name
        FROM book b
        JOIN author a ON a.author_id = b.author_id
        WHERE b.isbn = %s
        LIMIT 1;
    """

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (isbn,))
            row = cur.fetchone()
            if not row:
                return None

            return Book(
                book_id=row["book_id"],
                isbn=row["isbn"],
                title=row["title"],
                author_name=row["author_name"],
                genre=row["genre"],
                total_copies=row["total_copies"],
                available_copies=row["available_copies"],
            )
    finally:
        conn.close()


def list_all_loans(order_by: str = "newest") -> List[Loan]:
    """
    Return ALL loans (for all members), with book + member info.

    order_by:
        "newest"  -> latest loans first
        "oldest"  -> oldest loans first
        "due"     -> nearest due date first
    """
    order_by = order_by.lower()
    if order_by == "oldest":
        order_clause = "ORDER BY l.loan_date ASC, l.loan_id ASC"
    elif order_by == "due":
        order_clause = "ORDER BY l.due_date ASC, l.loan_id ASC"
    else:
        # default: newest
        order_clause = "ORDER BY l.loan_date DESC, l.loan_id DESC"

    sql = f"""
        SELECT
            l.loan_id,
            l.loan_date,
            l.due_date,
            l.return_date,
            m.member_id,
            m.full_name,
            m.email,
            u.user_id,
            u.username,
            b.book_id,
            b.isbn,
            b.title,
            b.genre,
            b.total_copies,
            b.available_copies,
            a.name AS author_name
        FROM loan l
        JOIN member m ON m.member_id = l.member_id
        JOIN app_user u ON u.user_id = m.user_id
        JOIN book b ON b.book_id = l.book_id
        JOIN author a ON a.author_id = b.author_id
        {order_clause};
    """

    conn = get_connection()
    loans: List[Loan] = []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            for row in rows:
                member = Member(
                    user_id=row["user_id"],
                    username=row["username"],
                    member_id=row["member_id"],
                    full_name=row["full_name"],
                    email=row["email"],
                )
                book = Book(
                    book_id=row["book_id"],
                    isbn=row["isbn"],
                    title=row["title"],
                    author_name=row["author_name"],
                    genre=row["genre"],
                    total_copies=row["total_copies"],
                    available_copies=row["available_copies"],
                )
                loan = Loan(
                    loan_id=row["loan_id"],
                    member=member,
                    book=book,
                    loan_date=row["loan_date"],
                    due_date=row["due_date"],
                    return_date=row["return_date"],
                )
                loans.append(loan)
    finally:
        conn.close()

    return loans




def find_book_by_isbn(isbn: str) -> Optional[Book]:
    """
    Look up a book by ISBN.
    Returns a Book object or None.
    """
    isbn = isbn.strip()
    sql = """
        SELECT
            b.book_id,
            b.isbn,
            b.title,
            b.genre,
            b.total_copies,
            b.available_copies,
            a.name AS author_name
        FROM book b
        JOIN author a ON a.author_id = b.author_id
        WHERE b.isbn = %s;
    """

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (isbn,))
            row = cur.fetchone()
            if not row:
                return None

            return Book(
                book_id=row["book_id"],
                isbn=row["isbn"],
                title=row["title"],
                author_name=row["author_name"],
                genre=row["genre"],
                total_copies=row["total_copies"],
                available_copies=row["available_copies"],
            )
    finally:
        conn.close()


def list_loans(order_by: str = "newest") -> List[Loan]:
    """
    List ALL loans in the system for the librarian Loans window.

    order_by:
      - "newest" -> loan_date DESC
      - "oldest" -> loan_date ASC
      - "due"    -> due_date ASC
    """
    order_map = {
        "newest": "l.loan_date DESC",
        "oldest": "l.loan_date ASC",
        "due": "l.due_date ASC",
    }
    order_clause = order_map.get(order_by, "l.loan_date DESC")

    sql = f"""
        SELECT
            l.loan_id,
            l.loan_date,
            l.due_date,
            l.return_date,
            m.member_id,
            m.full_name,
            m.email,
            u.user_id,
            u.username,
            b.book_id,
            b.isbn,
            b.title,
            b.genre,
            b.total_copies,
            b.available_copies,
            a.name AS author_name
        FROM loan l
        JOIN member m ON m.member_id = l.member_id
        JOIN app_user u ON u.user_id = m.user_id
        JOIN book b ON b.book_id = l.book_id
        JOIN author a ON a.author_id = b.author_id
        ORDER BY {order_clause};
    """

    conn = get_connection()
    loans: List[Loan] = []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            for row in rows:
                member = Member(
                    user_id=row["user_id"],
                    username=row["username"],
                    member_id=row["member_id"],
                    full_name=row["full_name"],
                    email=row["email"],
                )
                book = Book(
                    book_id=row["book_id"],
                    isbn=row["isbn"],
                    title=row["title"],
                    author_name=row["author_name"],
                    genre=row["genre"],
                    total_copies=row["total_copies"],
                    available_copies=row["available_copies"],
                )
                loan = Loan(
                    loan_id=row["loan_id"],
                    member=member,
                    book=book,
                    loan_date=row["loan_date"],
                    due_date=row["due_date"],
                    return_date=row["return_date"],
                )
                loans.append(loan)
    finally:
        conn.close()

    return loans


# ========== LOAN WORKFLOWS (BORROW / RETURN) ==========
# Business rules from assignment:
# - Max 3 active loans per member
# - Loan due date = loan_date + 7 days


from datetime import date, timedelta
from psycopg2.extras import RealDictCursor

# ...

def borrow_book(member_id: int, book_id: int) -> tuple[bool, str]:
    """
    Borrow a book for a member.

    Business rules:
    - Member must exist
    - Book must exist and have available_copies > 0
    - Member may have at most 3 ACTIVE loans (return_date IS NULL)
    - due_date = loan_date + 7 days

    Returns:
        (success, message)
    """
    today = date.today()
    due = today + timedelta(days=7)

    conn = get_connection()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 1) Check member exists
                cur.execute(
                    "SELECT member_id FROM member WHERE member_id = %s;",
                    (member_id,),
                )
                row = cur.fetchone()
                if not row:
                    return False, "Member not found."

                # 2) Check book exists + availability
                cur.execute(
                    """
                    SELECT book_id, title, available_copies
                    FROM book
                    WHERE book_id = %s;
                    """,
                    (book_id,),
                )
                book_row = cur.fetchone()
                if not book_row:
                    return False, "Book not found."

                if book_row["available_copies"] <= 0:
                    return False, "No available copies for this book."

                # 3) Check current active loans for this member
                cur.execute(
                    """
                    SELECT COUNT(*) AS active_count
                    FROM loan
                    WHERE member_id = %s
                      AND return_date IS NULL;
                    """,
                    (member_id,),
                )
                row = cur.fetchone() or {}
                # RealDictCursor returns a dict like {"active_count": 1}
                active_count_raw = row.get("active_count", 0)
                try:
                    active_count = int(active_count_raw)
                except (TypeError, ValueError):
                    active_count = 0

                if active_count >= 3:
                    return (
                        False,
                        "This member already has the maximum of 3 active loans.",
                    )

                # 4) Insert loan with due_date = today + 7 days
                cur.execute(
                    """
                    INSERT INTO loan(member_id, book_id, loan_date, due_date, return_date)
                    VALUES (%s, %s, %s, %s, NULL)
                    RETURNING loan_id;
                    """,
                    (member_id, book_id, today, due),
                )
                loan_id = cur.fetchone()["loan_id"]

        # if we reach here, transaction committed
        return True, f"Book borrowed successfully (Loan #{loan_id}). Due date: {due}."
    finally:
        conn.close()




def borrow_book_by_email_and_isbn(member_email: str, book_isbn: str) -> tuple[bool, str]:
    """
    Helper used by the LoansWindow dialog.

    - member_email: member.email (or username) from the GUI
    - book_isbn: ISBN typed in the GUI

    We:
      * look up member_id from member.email
      * look up book_id from book.isbn
      * call borrow_book(member_id, book_id)
    """
    member_email = member_email.strip().lower()
    book_isbn = book_isbn.strip()

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # find member_id by email
            cur.execute(
                "SELECT member_id FROM member WHERE lower(email) = %s;",
                (member_email,),
            )
            row = cur.fetchone()
            if not row:
                return False, "No member with that email."

            member_id = int(row["member_id"])

            # find book_id by ISBN
            cur.execute(
                "SELECT book_id FROM book WHERE isbn = %s;",
                (book_isbn,),
            )
            row = cur.fetchone()
            if not row:
                return False, "No book with that ISBN."

            book_id = int(row["book_id"])

    finally:
        conn.close()

    # Now use the core logic
    return borrow_book(member_id, book_id)




def return_book(loan_id: int) -> tuple[bool, str]:
    """
    Return a book:

    - Loan must exist and not already be returned
    - Sets return_date = today
    - Increases book.available_copies by 1

    Returns:
        (success, message)
    """
    today = date.today()

    conn = get_connection()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 1) Find the loan and associated book
                cur.execute(
                    """
                    SELECT loan_id, book_id, return_date
                    FROM loan
                    WHERE loan_id = %s;
                    """,
                    (loan_id,),
                )
                row = cur.fetchone()
                if not row:
                    return False, "Loan not found."

                if row["return_date"] is not None:
                    return False, "This loan is already returned."

                book_id = row["book_id"]

                # 2) Update loan.return_date
                # NOTE: We do NOT manually update available_copies here.
                # Your PostgreSQL trigger trg_return + inc_available_on_return()
                # will automatically increase available_copies when return_date changes
                # from NULL to a real date.
                cur.execute(
                    """
                    UPDATE loan
                    SET return_date = %s
                    WHERE loan_id = %s;
                    """,
                    (today, loan_id),
                )


        return True, "Book returned successfully."
    finally:
        conn.close()
