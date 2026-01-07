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
    Books management / catalogue screen.

    - Librarian (member=None): full CRUD (add/edit/delete) + filters.
    - Member (member is a Member object): read-only catalogue (no add/edit/delete).
    """

    def __init__(self, parent=None, librarian_name: str = "", member: Member = None):
        super().__init__(parent)
        self.setWindowTitle("Books – Francisca SmartLibrary")
        self.resize(900, 480)
        self.librarian_name = librarian_name
        self.member = member  # None for librarian, Member for normal users

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        header = QLabel(
            f"Books Management ({self.librarian_name})"
            if not self.member
            else f"Books catalogue ({self.member.full_name})"
        )
        header.setObjectName("TitleLabel")

        subtitle = QLabel(
            "View, add, update and delete books in Francisca SmartLibrary."
            if not self.member
            else "Browse the catalogue of Francisca SmartLibrary."
        )
        subtitle.setObjectName("SubtitleLabel")

        layout.addWidget(header)
        layout.addWidget(subtitle)

        # --- Back row ---
        back_row = QHBoxLayout()
        self.btn_back = QPushButton("< Back")
        self.btn_back.setFixedWidth(80)
        back_row.addWidget(self.btn_back)
        back_row.addStretch(1)
        layout.addLayout(back_row)

        # --- Top buttons + filters row ---
        top_row = QHBoxLayout()

        self.btn_add = QPushButton("Add book")
        self.btn_edit = QPushButton("Edit book")
        self.btn_delete = QPushButton("Delete book")
        self.btn_refresh = QPushButton("Refresh")
        self.btn_view_details = QPushButton("View details")

        top_row.addWidget(self.btn_add)
        top_row.addWidget(self.btn_edit)
        top_row.addWidget(self.btn_delete)
        top_row.addWidget(self.btn_refresh)
        top_row.addWidget(self.btn_view_details)

        top_row.addStretch(1)

        # search box
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by title, author or ISBN...")
        self.search_input.setFixedWidth(220)
        top_row.addWidget(self.search_input)

        layout.addLayout(top_row)

        # second small row: genre + availability filters
        filter_row = QHBoxLayout()
        filter_row.addStretch(1)

        self.genre_filter = QComboBox()
        self.genre_filter.addItem("All genres")
        filter_row.addWidget(self.genre_filter)

        self.availability_filter = QComboBox()
        self.availability_filter.addItems(["All books", "Only available"])
        filter_row.addWidget(self.availability_filter)

        layout.addLayout(filter_row)

        # --- Table (7 columns, including ISBN) ---
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

        # If opened for a normal member: HIDE admin buttons completely
        if self.member is not None:
            self.btn_add.hide()
            self.btn_edit.hide()
            self.btn_delete.hide()
            subtitle.setText("Browse the catalogue of Francisca SmartLibrary.")

        apply_base_style(self)
        self._connect_signals()
        self._load_books()  # fills table and populates filter combos

    # ------------------------------------------------------------------
    # Wiring
    # ------------------------------------------------------------------

    def _connect_signals(self):
        self.btn_add.clicked.connect(self._handle_add)
        self.btn_edit.clicked.connect(self._handle_edit)
        self.btn_delete.clicked.connect(self._handle_delete)
        self.btn_refresh.clicked.connect(self._load_books)
        self.btn_back.clicked.connect(self.close)
        self.btn_view_details.clicked.connect(self._handle_view_details)

        self.search_input.textChanged.connect(self._apply_filters)
        self.genre_filter.currentIndexChanged.connect(self._apply_filters)
        self.availability_filter.currentIndexChanged.connect(self._apply_filters)

    # ------------------------------------------------------------------
    # Data loading + filter helpers
    # ------------------------------------------------------------------

    def _load_books(self):
        """Load all books from the database into the table."""
        books = list_books()
        self.table.setRowCount(len(books))

        for row, book in enumerate(books):
            self.table.setItem(row, 0, QTableWidgetItem(str(book.book_id)))
            self.table.setItem(row, 1, QTableWidgetItem(book.isbn))
            self.table.setItem(row, 2, QTableWidgetItem(book.title))
            self.table.setItem(row, 3, QTableWidgetItem(book.author_name))
            self.table.setItem(row, 4, QTableWidgetItem(book.genre))
            self.table.setItem(row, 5, QTableWidgetItem(str(book.total_copies)))
            self.table.setItem(row, 6, QTableWidgetItem(str(book.available_copies)))

        self._refresh_genre_filter_options()
        self._apply_filters()

    def _refresh_genre_filter_options(self):
        """Rebuild the 'All genres' combo based on the genres currently in the table."""
        genres = set()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 4)  # Genre column
            if item:
                text = item.text().strip()
                if text:
                    genres.add(text)

        current = self.genre_filter.currentText()
        self.genre_filter.blockSignals(True)
        self.genre_filter.clear()
        self.genre_filter.addItem("All genres")
        for g in sorted(genres):
            self.genre_filter.addItem(g)
        self.genre_filter.blockSignals(False)

        # try to keep previous selection if still present
        if current and current in [self.genre_filter.itemText(i) for i in range(self.genre_filter.count())]:
            index = self.genre_filter.findText(current)
            if index >= 0:
                self.genre_filter.setCurrentIndex(index)

    def _apply_filters(self):
        """
        Apply search text + genre + availability filters
        to the rows that are already loaded in the table.
        No extra DB calls → avoids crashes.
        """
        search = (self.search_input.text() or "").strip().lower()
        selected_genre = self.genre_filter.currentText()
        availability_mode = self.availability_filter.currentText()

        for row in range(self.table.rowCount()):
            show = True

            # search filter (ISBN, Title, Author)
            if search:
                match = False
                for col in (1, 2, 3):  # ISBN, Title, Author
                    item = self.table.item(row, col)
                    if item and search in item.text().lower():
                        match = True
                        break
                if not match:
                    show = False

            # genre filter
            if show and selected_genre != "All genres":
                genre_item = self.table.item(row, 4)
                if not genre_item or genre_item.text().strip() != selected_genre:
                    show = False

            # availability filter
            if show and availability_mode == "Only available":
                avail_item = self.table.item(row, 6)
                try:
                    available_copies = int(avail_item.text()) if avail_item else 0
                except (TypeError, ValueError):
                    available_copies = 0
                if available_copies <= 0:
                    show = False

            self.table.setRowHidden(row, not show)

    # ------------------------------------------------------------------
    # Selection helper
    # ------------------------------------------------------------------

    def _selected_book_id(self):
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            QMessageBox.information(self, "No selection", "Please select a row first.")
            return None
        row = indexes[0].row()
        book_id_item = self.table.item(row, 0)
        if not book_id_item:
            return None
        try:
            return int(book_id_item.text())
        except ValueError:
            return None

    # ------------------------------------------------------------------
    # Buttons: CRUD + details
    # ------------------------------------------------------------------

    def _handle_view_details(self):
        """Show a small popup with the details of the selected book."""
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            QMessageBox.information(self, "No selection", "Please select a book first.")
            return

        row = indexes[0].row()
        id_ = self.table.item(row, 0).text()
        isbn = self.table.item(row, 1).text()
        title = self.table.item(row, 2).text()
        author = self.table.item(row, 3).text()
        genre = self.table.item(row, 4).text()
        total = self.table.item(row, 5).text()
        available = self.table.item(row, 6).text()

        msg = (
            f"ID: {id_}\n"
            f"ISBN: {isbn}\n"
            f"Title: {title}\n"
            f"Author: {author}\n"
            f"Genre: {genre}\n"
            f"Total copies: {total}\n"
            f"Available: {available}\n"
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

        # ISBN (optional)
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

        add_book(title.strip(), author.strip(), genre.strip(), copies, isbn.strip())
        self._load_books()

    def _handle_edit(self):
        book_id = self._selected_book_id()
        if book_id is None:
            return

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
