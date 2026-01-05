from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QMessageBox,
    QInputDialog, QLineEdit, QComboBox
)

from .style import apply_base_style
from Roots.models import Member
from Roots.daos import list_books, add_book, update_book, delete_book


class BooksWindow(QDialog):
    """
    Books management screen.
    Uses Book objects and daos.py for CRUD.

    If opened with a Member object (from MemberDashboard),
    the window becomes READ-ONLY: the Add/Edit/Delete buttons are hidden.
    """

    def __init__(self, parent=None, librarian_name: str = "", member: Member = None):
        super().__init__(parent)
        self.setWindowTitle("Books – Francisca SmartLibrary")
        self.resize(720, 420)
        self.librarian_name = librarian_name
        self.member = member  # None for librarian, Member for normal users

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        header = QLabel(f"Books Management ({self.librarian_name})")
        header.setObjectName("TitleLabel")

        subtitle = QLabel("View, add, update and delete books in Francisca SmartLibrary.")
        subtitle.setObjectName("SubtitleLabel")

        layout.addWidget(header)
        layout.addWidget(subtitle)

        # Back button row
        back_row = QHBoxLayout()
        self.btn_back = QPushButton("< Back")
        self.btn_back.setFixedWidth(80)
        back_row.addWidget(self.btn_back)
        back_row.addStretch(1)
        layout.addLayout(back_row)

        # Top buttons
        # Top buttons
        btn_row = QHBoxLayout()
        self.btn_add = QPushButton("Add book")
        self.btn_edit = QPushButton("Edit book")
        self.btn_delete = QPushButton("Delete book")
        self.btn_refresh = QPushButton("Refresh")
        self.btn_details = QPushButton("View details")   # NEW

        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_edit)
        btn_row.addWidget(self.btn_delete)
        btn_row.addWidget(self.btn_refresh)
        btn_row.addWidget(self.btn_details)

        btn_row.addStretch(1)

        # NEW: search + filters
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by title, author or ISBN...")
        self.genre_filter = QComboBox()
        self.genre_filter.addItem("All genres")
        self.availability_filter = QComboBox()
        self.availability_filter.addItems(["All books", "Only available"])

        btn_row.addWidget(self.search_input)
        btn_row.addWidget(self.genre_filter)
        btn_row.addWidget(self.availability_filter)

        layout.addLayout(btn_row)

        ...
        self.search_input.textChanged.connect(self._apply_search_filter)

        # If opened for a normal member: HIDE admin buttons completely
        if self.member is not None:
            self.btn_add.hide()
            self.btn_edit.hide()
            self.btn_delete.hide()
            subtitle.setText("Browse the catalogue of Francisca SmartLibrary.")

        # Table – now includes ISBN column
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["ID", "ISBN", "Title", "Author", "Genre", "Total copies", "Available"]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)

        layout.addWidget(self.table)

        apply_base_style(self)
        self._connect_signals()
        self._load_books()

        # connect filters + search
        self.search_input.textChanged.connect(self._apply_search_filter)
        self.genre_filter.currentIndexChanged.connect(self._apply_search_filter)
        self.availability_filter.currentIndexChanged.connect(self._apply_search_filter)

    # ------------------------------------------------------------------

    def _connect_signals(self):
        self.btn_add.clicked.connect(self._handle_add)
        self.btn_edit.clicked.connect(self._handle_edit)
        self.btn_delete.clicked.connect(self._handle_delete)
        self.btn_refresh.clicked.connect(self._load_books)
        self.btn_back.clicked.connect(self.close)
        self.btn_details.clicked.connect(self._show_details)  # NEW

    def _load_books(self):
        books = list_books()
        self.table.setRowCount(len(books))

        genres_seen = set()

        for row, book in enumerate(books):
            # book is a Book object from models.Book
            self.table.setItem(row, 0, QTableWidgetItem(str(book.book_id)))
            self.table.setItem(row, 1, QTableWidgetItem(book.isbn))
            self.table.setItem(row, 2, QTableWidgetItem(book.title))
            self.table.setItem(row, 3, QTableWidgetItem(book.author_name))
            self.table.setItem(row, 4, QTableWidgetItem(book.genre))
            self.table.setItem(row, 5, QTableWidgetItem(str(book.total_copies)))
            self.table.setItem(row, 6, QTableWidgetItem(str(book.available_copies)))

            if book.genre:
                genres_seen.add(book.genre)

        # update genre filter
        current = self.genre_filter.currentText()
        self.genre_filter.blockSignals(True)
        self.genre_filter.clear()
        self.genre_filter.addItem("All genres")
        for g in sorted(genres_seen):
            self.genre_filter.addItem(g)
        self.genre_filter.blockSignals(False)

        # re-apply search/filter after reload
        self._apply_search_filter(self.search_input.text())

    def _selected_book_id(self):
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            QMessageBox.information(self, "No selection", "Please select a row first.")
            return None
        row = indexes[0].row()
        book_id_item = self.table.item(row, 0)
        return int(book_id_item.text())

    # ------------------------------------------------------------------
    # CRUD handlers
    # ------------------------------------------------------------------

    def _apply_search_filter(self, text: str):
        """
        Simple client-side filter on the current table.
        Uses:
          - search text (ISBN / Title / Author)
          - genre filter
          - availability filter
        """
        text = (text or "").strip().lower()
        selected_genre = self.genre_filter.currentText()
        availability_mode = self.availability_filter.currentText()

        for row in range(self.table.rowCount()):
            # --- search text match ---
            if not text:
                text_matches = True
            else:
                text_matches = False
                for col in (1, 2, 3):  # ISBN, Title, Author
                    item = self.table.item(row, col)
                    if item and text in item.text().lower():
                        text_matches = True
                        break

            # --- genre match ---
            genre_item = self.table.item(row, 4)  # Genre
            genre_text = genre_item.text() if genre_item else ""
            genre_matches = (
                selected_genre == "All genres"
                or genre_text == selected_genre
            )

            # --- availability match ---
            avail_item = self.table.item(row, 6)  # Available copies
            is_available = False
            if avail_item:
                try:
                    is_available = int(avail_item.text()) > 0
                except ValueError:
                    is_available = False

            if availability_mode == "All books":
                availability_matches = True
            else:  # "Only available"
                availability_matches = is_available

            show_row = text_matches and genre_matches and availability_matches
            self.table.setRowHidden(row, not show_row)


    def _show_details(self):
        book_id = self._selected_book_id()
        if book_id is None:
            return

        # Find the row for this book
        row = None
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 0)
            if item and item.text() == str(book_id):
                row = r
                break

        if row is None:
            QMessageBox.warning(self, "Details", "Could not find book in table.")
            return

        isbn = self.table.item(row, 1).text()
        title = self.table.item(row, 2).text()
        author = self.table.item(row, 3).text()
        genre = self.table.item(row, 4).text()
        total = self.table.item(row, 5).text()
        available = self.table.item(row, 6).text()

        msg = (
            f"Title: {title}\n"
            f"Author: {author}\n"
            f"Genre: {genre}\n"
            f"ISBN: {isbn}\n"
            f"Total copies: {total}\n"
            f"Available: {available}"
        )
        QMessageBox.information(self, "Book details", msg)


    def _handle_add(self):
        # Title
        title, ok = QInputDialog.getText(self, "Add book", "Title:", QLineEdit.Normal)
        if not ok or not title.strip():
            return

        # Author
        author, ok = QInputDialog.getText(self, "Add book", "Author:", QLineEdit.Normal)
        if not ok or not author.strip():
            return

        # Genre
        genre, ok = QInputDialog.getText(self, "Add book", "Genre:", QLineEdit.Normal)
        if not ok or not genre.strip():
            return

        # NEW: ISBN (optional) – needed when borrowing by ISBN
        isbn, ok = QInputDialog.getText(
            self, "Add book", "ISBN (optional):", QLineEdit.Normal
        )
        if not ok:
            return

        # Copies
        copies_str, ok = QInputDialog.getText(
            self, "Add book", "Total copies:", QLineEdit.Normal, "1"
        )
        if not ok:
            return

        try:
            copies = int(copies_str)
        except ValueError:
            QMessageBox.warning(self, "Invalid", "Copies must be a whole number.")
            return

        # daos.add_book handles empty ISBN by generating a placeholder
        add_book(title.strip(), author.strip(), genre.strip(), copies, isbn.strip())
        self._load_books()

    def _handle_edit(self):
        book_id = self._selected_book_id()
        if book_id is None:
            return

        # For simplicity, we just ask new values (no pre-fill)
        title, ok = QInputDialog.getText(self, "Edit book", "New title:", QLineEdit.Normal)
        if not ok or not title.strip():
            return
        author, ok = QInputDialog.getText(self, "Edit book", "New author:", QLineEdit.Normal)
        if not ok or not author.strip():
            return
        genre, ok = QInputDialog.getText(self, "Edit book", "New genre:", QLineEdit.Normal)
        if not ok or not genre.strip():
            return
        copies_str, ok = QInputDialog.getText(
            self, "Edit book", "New total copies:", QLineEdit.Normal, "1"
        )
        if not ok:
            return

        try:
            copies = int(copies_str)
        except ValueError:
            QMessageBox.warning(self, "Invalid", "Copies must be a whole number.")
            return

        # We treat available_copies = total_copies for simplicity when editing.
        if not update_book(book_id, title.strip(), author.strip(), genre.strip(), copies, copies):
            QMessageBox.warning(self, "Error", "Book not found.")
            return

        self._load_books()

    def _handle_delete(self):
        book_id = self._selected_book_id()
        if book_id is None:
            return
        reply = QMessageBox.question(
            self, "Delete book", "Are you sure you want to delete this book?"
        )
        if reply != QMessageBox.Yes:
            return

        if not delete_book(book_id):
            QMessageBox.warning(self, "Error", "Book not found.")
            return

        self._load_books()
