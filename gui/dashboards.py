import os  # for path to background image

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QMessageBox,
    QFrame,
    QDialog,
    QSizePolicy,   # NEW: to make cards expand nicely
)

from .style import apply_base_style, ORANGE, TEAL
from Roots.models import Librarian, Member
from .books_window import BooksWindow
from .member_window import MembersWindow
from .loan_window import LoansWindow
from .club_window import LibrarianClubsWindow, MemberClubsWindow
from .login import LoginWindow  # used for logout → back to login


# ---------------------------------------------------------------------------
# Background helper – apply image behind dashboard content
# ---------------------------------------------------------------------------

# relative to THIS file (dashboard.py is in gui/, image is in gui/assets/)
DASHBOARD_BG_RELATIVE = "assets/library_bg.jpg"


def _set_dashboard_background(widget: QWidget, image_relative: str = DASHBOARD_BG_RELATIVE):
    """
    Apply a stretched background image to the given widget using a stylesheet.

    Looks for the image at: <folder_of_this_file> / image_relative
    In your case: gui/assets/library_bg.jpg

    If the image is missing, it silently does nothing.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))  # .../gui
    image_path = os.path.join(base_dir, image_relative)    # .../gui/assets/library_bg.jpg

    if not os.path.exists(image_path):
        # Optional: uncomment to debug if needed
        # print(f"[dashboard] Background image not found: {image_path}")
        return

    # Use forward slashes so Qt is happy on Windows too
    image_path = image_path.replace("\\", "/")

    # Ensure widget has an object name so the selector works
    if not widget.objectName():
        widget.setObjectName("DashboardCentral")

    widget.setStyleSheet(
        f"""
        #{widget.objectName()} {{
            border-image: url('{image_path}') 0 0 0 0 stretch stretch;
        }}
        """
    )


# ---------------------------------------------------------------------------
# Helper: small “tile” widget used on both dashboards
# ---------------------------------------------------------------------------

def _make_tile(title: str, number: str, color: str) -> QWidget:
    """
    Create a small info tile with a title and a big number.
    Used in both LibrarianDashboard and MemberDashboard.
    """
    frame = QFrame()
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(8, 8, 8, 8)

    header = QLabel(title.upper())
    header.setObjectName("SubtitleLabel")

    value = QLabel(number)
    # Slightly bigger numbers so they are readable on large screens
    value.setStyleSheet(
        f"font-size: 22px; font-weight: 700; color: {color};"
    )

    layout.addWidget(header)
    layout.addWidget(value)

    return frame


def _make_list_panel(title: str, lines: list[str]) -> QWidget:
    """
    Small panel showing a title and a few lines (used for
    'Most borrowed books' and 'Most active members').
    """
    frame = QFrame()
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(8, 8, 8, 8)

    header = QLabel(title)
    header.setObjectName("SubtitleLabel")
    layout.addWidget(header)

    if not lines:
        layout.addWidget(QLabel("No data yet."))
    else:
        for text in lines:
            lbl = QLabel(text)
            lbl.setWordWrap(True)
            layout.addWidget(lbl)

    return frame


# ---------------------------------------------------------------------------
# Shared helper for logout → go back to login
# ---------------------------------------------------------------------------

def _perform_logout_and_relogin(current_window: QMainWindow):
    """
    Close the current dashboard and go back to the login screen.

    Flow:
      1. Show LoginWindow again.
      2. If user logs in:
           - If librarian → open LibrarianDashboard
           - If member    → open MemberDashboard
      3. Close the old dashboard.
    """
    login = LoginWindow(current_window)
    # clear old values for a fresh feeling
    login.email_edit.clear()
    login.password_edit.clear()

    result = login.exec_()
    user = getattr(login, "logged_in_user", None)

    if result == QDialog.Accepted and user is not None:
        if login.role == "librarian" and isinstance(user, Librarian):
            new_window = LibrarianDashboard(user)
            new_window.show()
        elif login.role == "member" and isinstance(user, Member):
            new_window = MemberDashboard(user)
            new_window.show()
        else:
            QMessageBox.warning(
                current_window,
                "Login error",
                "Your account role did not match any dashboard.",
            )

    current_window.close()


# ---------------------------------------------------------------------------
# Librarian dashboard (admin view)
# ---------------------------------------------------------------------------

class LibrarianDashboard(QMainWindow):
    """
    Admin view for Francisca, Abril, Abubakar.
    """

    def __init__(self, librarian: Librarian):
        super().__init__()

        self.librarian = librarian
        self.setWindowTitle("Francisca SmartLibrary - Librarian Dashboard")
        self.resize(900, 520)

        central = QWidget()
        central.setObjectName("LibrarianDashboardCentral")  # for background style
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        # header text
        title = QLabel(f"Welcome, {self.librarian.full_name}")
        title.setObjectName("TitleLabel")

        subtitle = QLabel(
            "Librarian control panel – manage books, members, loans & clubs."
        )
        subtitle.setObjectName("SubtitleLabel")

        layout.addWidget(title)
        layout.addWidget(subtitle)

        # real numbers from database
        members_count = count_members()
        books_count = count_books()
        loans_count = count_active_loans()
        clubs_count = count_clubs()

        # tiles grid
        tiles = QGridLayout()
        tiles.setSpacing(10)
        tiles.addWidget(
            _make_tile("Members", str(members_count), ORANGE), 0, 0
        )
        tiles.addWidget(
            _make_tile("Issued books", str(loans_count), TEAL), 0, 1
        )
        tiles.addWidget(
            _make_tile("Books", str(books_count), ORANGE), 1, 0
        )
        tiles.addWidget(
            _make_tile("Clubs", str(clubs_count), TEAL), 1, 1
        )

        layout.addLayout(tiles)

        # -------------------------------------------------------------------
        # Most borrowed books + Most active members (assignment feature)
        # -------------------------------------------------------------------
        top_books = get_top_borrowed_books(limit=3)
        top_members = get_top_active_members(limit=3)

        book_lines = [
            f"{i}. {row['title']} ({row['borrow_count']} loans)"
            for i, row in enumerate(top_books, start=1)
        ]

        member_lines = [
            f"{i}. {row['full_name']} ({row['borrow_count']} loans)"
            for i, row in enumerate(top_members, start=1)
        ]

        lists_row = QHBoxLayout()
        lists_row.setSpacing(10)
        lists_row.addWidget(_make_list_panel("Most borrowed books", book_lines))
        lists_row.addWidget(_make_list_panel("Most active members", member_lines))

        layout.addSpacing(10)
        layout.addLayout(lists_row)

        # buttons row
        btn_row = QHBoxLayout()
        self.btn_books = QPushButton("Manage books")
        self.btn_members = QPushButton("Manage members")
        self.btn_loans = QPushButton("Manage loans")
        self.btn_clubs = QPushButton("Manage clubs")
        self.btn_logout = QPushButton("Logout")
        self.btn_logout.setObjectName("Secondary")

        for btn in [
            self.btn_books,
            self.btn_members,
            self.btn_loans,
            self.btn_clubs,
        ]:
            btn.setMinimumHeight(40)
            btn_row.addWidget(btn)

        layout.addSpacing(10)
        layout.addLayout(btn_row)
        layout.addStretch(1)
        layout.addWidget(self.btn_logout, alignment=Qt.AlignRight)

        apply_base_style(self)
        _set_dashboard_background(self.centralWidget())  # background

        self._connect()

    # --- signal wiring -----------------------------------------------------

    def _connect(self):
        self.btn_books.clicked.connect(self._open_books)
        self.btn_members.clicked.connect(self._open_members)
        self.btn_loans.clicked.connect(self._open_loans)
        self.btn_clubs.clicked.connect(self._open_clubs)

        # go back to login instead of just closing the app
        self.btn_logout.clicked.connect(
            lambda: _perform_logout_and_relogin(self)
        )

    # --- button handlers ---------------------------------------------------

    def _open_books(self):
        dlg = BooksWindow(self, librarian_name=self.librarian.full_name)
        dlg.exec_()

    def _open_members(self):
        dlg = MembersWindow(self)
        dlg.exec_()

    def _open_loans(self):
        dlg = LoansWindow(self)
        dlg.exec_()

    def _open_clubs(self):
        dlg = LibrarianClubsWindow(self)
        dlg.exec_()


# ---------------------------------------------------------------------------
# Member dashboard (normal user view)
# ---------------------------------------------------------------------------

class MemberDashboard(QMainWindow):
    """
    Simpler dashboard for normal members.

    Includes your idea of a reminder:
    when they log in, show a popup if books are due soon.
    """

    def __init__(self, member: Member):
        super().__init__()

        self.member = member
        self.setObjectName("MemberDashboard")
        self.setWindowTitle("Francisca SmartLibrary - Member Dashboard")
        self.resize(900, 520)

        central = QWidget()
        central.setObjectName("MemberDashboardCentral")
        # Let the background image show through
        central.setStyleSheet("background: transparent;")
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # --------------------------------------------------
        # HERO BANNER (like the top of the Pinterest design)
        # --------------------------------------------------
        hero = QFrame()
        hero.setObjectName("MemberHero")
        hero.setStyleSheet(
            """
            QFrame#MemberHero {
                background: rgba(0, 0, 0, 0.55);   /* dark overlay */
                border-radius: 8px;
                color: white;
            }
            """
        )
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(16, 10, 16, 12)
        hero_layout.setSpacing(4)

        title = QLabel(f"Welcome, {self.member.full_name}")
        # big clear heading
        title.setStyleSheet("font-size: 26px; font-weight: 800;")
        subtitle = QLabel("Browse books, track your reading and join clubs.")
        subtitle.setStyleSheet("font-size: 15px;")

        hero_layout.addWidget(title)
        hero_layout.addWidget(subtitle)

        layout.addWidget(hero)

        # --- stats for this member ---
        my_loans = get_loans_for_member(self.member.member_id)
        my_loans_count = len(my_loans)

        completed_loans = sum(1 for loan in my_loans if loan.return_date is not None)
        if my_loans_count == 0:
            progress_percent = 0
        else:
            progress_percent = round(completed_loans / my_loans_count * 100)

        # demo numbers
        reserved_count = 1
        clubs_joined = 2

        # --------------------------------------
        # MAIN CONTENT: left stats, right actions
        # white cards like Pinterest example
        # --------------------------------------
        content_row = QHBoxLayout()
        content_row.setSpacing(16)

        # LEFT CARD – stats
        left_card = QFrame()
        left_card.setObjectName("MemberStatsCard")
        left_card.setStyleSheet(
            """
            QFrame#MemberStatsCard {
                background: rgba(255, 255, 255, 0.92);
                border-radius: 8px;
            }
            """
        )
        left_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(16, 14, 16, 14)
        left_layout.setSpacing(10)

        stats_title = QLabel("Your library at a glance")
        stats_title.setStyleSheet("font-size: 18px; font-weight: 800;")
        left_layout.addWidget(stats_title)

        stats_grid = QGridLayout()
        stats_grid.setSpacing(14)

        stats_grid.addWidget(
            _make_tile("My loans", str(my_loans_count), "#1f6feb"), 0, 0
        )
        stats_grid.addWidget(
            _make_tile("Reserved books", str(reserved_count), "#15998e"), 0, 1
        )
        stats_grid.addWidget(
            _make_tile("Clubs joined", str(clubs_joined), "#2563eb"), 1, 0
        )
        stats_grid.addWidget(
            _make_tile("Reading progress", f"{progress_percent}%", "#14b8a6"),
            1, 1
        )

        left_layout.addLayout(stats_grid)

        # RIGHT CARD – quick actions
        right_card = QFrame()
        right_card.setObjectName("MemberShortcutsCard")
        right_card.setStyleSheet(
            """
            QFrame#MemberShortcutsCard {
                background: rgba(255, 255, 255, 0.95);
                border-radius: 8px;
            }
            """
        )
        right_card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(16, 14, 16, 14)
        right_layout.setSpacing(12)

        shortcuts_title = QLabel("Quick actions")
        shortcuts_title.setStyleSheet("font-size: 17px; font-weight: 700;")
        right_layout.addWidget(shortcuts_title)

        self.btn_view_books = QPushButton("Browse books catalogue")
        self.btn_my_loans = QPushButton("View my loans")
        self.btn_my_clubs = QPushButton("My clubs & memberships")
        self.btn_logout = QPushButton("Logout")
        self.btn_logout.setObjectName("Secondary")

        for btn in [self.btn_view_books, self.btn_my_loans, self.btn_my_clubs]:
            btn.setMinimumHeight(52)
            btn.setCursor(Qt.PointingHandCursor)
            # bigger button text like the Pinterest call-to-actions
            btn.setStyleSheet("font-size: 15px; font-weight: 600;")
            right_layout.addWidget(btn)

        right_layout.addStretch(1)

        content_row.addWidget(left_card, 3)
        content_row.addWidget(right_card, 2)

        layout.addLayout(content_row)

        # Logout bottom right
        layout.addSpacing(6)
        layout.addWidget(self.btn_logout, alignment=Qt.AlignRight)

        apply_base_style(self)
        _set_dashboard_background(self.centralWidget())  # keep your photo

        self._connect()
        self._show_due_soon_reminder()

    # --- signal wiring -----------------------------------------------------

    def _connect(self):
        self.btn_view_books.clicked.connect(self._open_books_readonly)
        self.btn_my_loans.clicked.connect(self._info_loans)
        self.btn_my_clubs.clicked.connect(self._open_member_clubs)

        self.btn_logout.clicked.connect(
            lambda: _perform_logout_and_relogin(self)
        )

    # --- button handlers ---------------------------------------------------

    def _open_books_readonly(self):
        """
        Opens the Books window in read-only mode for members.
        They can browse but not add/edit/delete.
        """
        dlg = BooksWindow(self, librarian_name=self.member.full_name)
        dlg.btn_add.setDisabled(True)
        dlg.btn_edit.setDisabled(True)
        dlg.btn_delete.setDisabled(True)
        dlg.setWindowTitle("Books catalogue - Francisca SmartLibrary")
        dlg.exec_()

    def _info_loans(self):
        # Open the Loans window, filtered for THIS member
        dlg = LoansWindow(self, member=self.member)
        dlg.exec_()

    def _open_member_clubs(self):
        dlg = MemberClubsWindow(self, member=self.member)
        dlg.exec_()

    # --- reminder when books are nearly due -------------------------------

    def _show_due_soon_reminder(self):
        """
        When the member logs in, check for books due soon (e.g. next 3 days)
        and show a friendly reminder popup.
        IMPORTANT: use member.member_id, because DAO expects member_id,
        not user_id.
        """
        loans = get_due_soon_loans_for_member(self.member.member_id)
        if not loans:
            return

        count = len(loans)
        nearest_due = min(loan.due_date for loan in loans)

        msg = (
            f"You have {count} book(s) due soon.\n"
            f"Nearest due date: {nearest_due}.\n\n"
            "Please return your books on time."
        )

        QMessageBox.information(self, "Friendly reminder", msg)


# ---------------------------------------------------------------------------
# DAO imports at the bottom (to avoid circular issues in some setups)
# ---------------------------------------------------------------------------

from Roots.daos import (
    get_due_soon_loans_for_member,
    get_loans_for_member,
    count_members,
    count_books,
    count_active_loans,
    count_clubs,
    get_top_borrowed_books,
    get_top_active_members,
)