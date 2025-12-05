from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QMessageBox,
    QInputDialog, QLineEdit
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
        btn_row = QHBoxLayout()
        self.btn_add = QPushButton("Add book")
        self.btn_edit = QPushButton("Edit book")
        self.btn_delete = QPushButton("Delete book")
        self.btn_refresh = QPushButton("Refresh")
        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_edit)
        btn_row.addWidget(self.btn_delete)
        btn_row.addWidget(self.btn_refresh)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        # NEW: search box
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by title, author or ISBN...")
        btn_row.addWidget(self.search_input)

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

    # ------------------------------------------------------------------

    def _connect_signals(self):
        self.btn_add.clicked.connect(self._handle_add)
        self.btn_edit.clicked.connect(self._handle_edit)
        self.btn_delete.clicked.connect(self._handle_delete)
        self.btn_refresh.clicked.connect(self._load_books)
        self.btn_back.clicked.connect(self.close)

    def _load_books(self):
        books = list_books()
        self.table.setRowCount(len(books))
        for row, book in enumerate(books):
            # book is a Book object from models.Book
            self.table.setItem(row, 0, QTableWidgetItem(str(book.book_id)))
            self.table.setItem(row, 1, QTableWidgetItem(book.isbn))
            self.table.setItem(row, 2, QTableWidgetItem(book.title))
            self.table.setItem(row, 3, QTableWidgetItem(book.author_name))
            self.table.setItem(row, 4, QTableWidgetItem(book.genre))
            self.table.setItem(row, 5, QTableWidgetItem(str(book.total_copies)))
            self.table.setItem(row, 6, QTableWidgetItem(str(book.available_copies)))

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
        Hides rows that do not contain the text in ISBN / Title / Author columns.
        """
        text = (text or "").strip().lower()

        for row in range(self.table.rowCount()):
            if not text:
                # show everything when search box is empty
                self.table.setRowHidden(row, False)
                continue

            row_matches = False
            # adjust column indexes if your table order is different:
            # 0: ID, 1: ISBN, 2: Title, 3: Author, 4: Genre, ...
            for col in (1, 2, 3):
                item = self.table.item(row, col)
                if item and text in item.text().lower():
                    row_matches = True
                    break

            self.table.setRowHidden(row, not row_matches)



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
