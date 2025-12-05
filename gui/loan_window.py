# Librarian / Member loan management window for Francisca SmartLibrary

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
)

from .style import apply_base_style
from Roots.models import Member
from Roots.daos import (
    find_member_by_email,
    find_book_by_isbn,
    list_all_loans,
    get_loans_for_member,
    return_book,
    borrow_book_by_email_and_isbn,
    count_active_loans,
)


class LoansWindow(QDialog):
    """
    Loan management window.

    - When opened from the LIBRARIAN dashboard (member=None):
        * shows ALL loans
        * librarian can borrow for any member using email + ISBN.
    - When opened from the MEMBER dashboard (member is a Member object):
        * shows ONLY that member's loans
        * email field is locked to the logged-in member
        * member can only borrow books for themselves.
    """

    def __init__(self, parent=None, member: Member | None = None):
        super().__init__(parent)
        self.member = member

        if self.member is not None:
            self.setWindowTitle("My loans - Francisca SmartLibrary")
        else:
            self.setWindowTitle("Loans management - Francisca SmartLibrary")

        self.resize(900, 500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        # ---- Heading ----
        title = QLabel("SmartLibrary Loan Management")
        title.setObjectName("TitleLabel")
        layout.addWidget(title)

        subtitle = QLabel(
            "Borrow and return books for members. "
            "Use email + ISBN to create a new loan."
        )
        subtitle.setObjectName("SubtitleLabel")
        layout.addWidget(subtitle)

        # If this is the member's own "My loans" view, adjust subtitle
        if self.member is not None:
            subtitle.setText(
                "Borrow and return books for your own account only."
            )

        # ---- Input row: member email + book ISBN ----
        inputs = QHBoxLayout()

        self.member_email_input = QLineEdit()
        self.member_email_input.setPlaceholderText("Enter member email")

        self.book_isbn_input = QLineEdit()
        self.book_isbn_input.setPlaceholderText("Enter book ISBN")

        inputs.addWidget(self.member_email_input)
        inputs.addWidget(self.book_isbn_input)

        layout.addLayout(inputs)

        # If opened for a specific member, lock the email field to that member
        if self.member is not None:
            self.member_email_input.setText(self.member.email)
            self.member_email_input.setReadOnly(True)
            self.member_email_input.setToolTip(
                "You are logged in as this member. Loans will be created for this account."
            )

        # ---- Actions row: borrow / return / sort / refresh ----
        actions = QHBoxLayout()

        self.btn_borrow = QPushButton("Borrow book")
        self.btn_return = QPushButton("Return book")

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(
            ["Sort by newest", "Sort by oldest", "Sort by due date"]
        )

        self.btn_refresh = QPushButton("Refresh")

        actions.addWidget(self.btn_borrow)
        actions.addWidget(self.btn_return)
        actions.addStretch(1)
        actions.addWidget(self.sort_combo)
        actions.addWidget(self.btn_refresh)

        layout.addLayout(actions)

        # ---- Loans table ----
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            [
                "Loan ID",
                "Member",
                "Email",
                "Book",
                "Loan date",
                "Due date",
                "Returned on / Status",
            ]
        )
        self.table.setSelectionBehavior(self.table.SelectRows)
        self.table.setSelectionMode(self.table.SingleSelection)
        self.table.setEditTriggers(self.table.NoEditTriggers)

        layout.addWidget(self.table)

        # ---- Footer: active loans count ----
        footer = QHBoxLayout()
        self.lbl_active = QLabel("")
        footer.addWidget(self.lbl_active)
        footer.addStretch(1)
        layout.addLayout(footer)

        apply_base_style(self)
        self._connect()
        self.load_loans_table()  # initial load

    # ------------------- Wiring -------------------

    def _connect(self):
        self.btn_refresh.clicked.connect(self.load_loans_table)
        self.btn_borrow.clicked.connect(self._on_borrow_for_member)
        self.btn_return.clicked.connect(self._on_return_selected_loan)
        self.sort_combo.currentIndexChanged.connect(self.load_loans_table)

    # ------------------- Helpers -------------------

    def _current_order_by(self) -> str:
        text = self.sort_combo.currentText().lower()
        if "oldest" in text:
            return "oldest"
        if "due" in text:
            return "due"
        return "newest"

    def _selected_loan_id(self):
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return None
        row = indexes[0].row()
        item = self.table.item(row, 0)  # column 0 = Loan ID
        if item is None:
            return None
        try:
            return int(item.text())
        except ValueError:
            return None

    # ------------------- Loading data -------------------

    def load_loans_table(self):
        """
        Load loans into the table.

        - Librarian: all loans, with chosen sort order.
        - Member: only this member's loans.
        """
        if self.member is not None:
            # Member view – only their own loans
            loans = get_loans_for_member(self.member.member_id)
        else:
            order_by = self._current_order_by()
            loans = list_all_loans(order_by=order_by)

        self.table.setRowCount(len(loans))

        for row_index, loan in enumerate(loans):
            # Status / returned
            if loan.return_date is None:
                status = "Active"
            else:
                status = f"Returned: {loan.return_date}"

            values = [
                str(loan.loan_id),
                loan.member.full_name,
                loan.member.email,
                loan.book.title,
                str(loan.loan_date),
                str(loan.due_date),
                status,
            ]

            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                self.table.setItem(row_index, col, item)

        # Update active loans label
        if self.member is not None:
            active = sum(1 for loan in loans if loan.return_date is None)
            self.lbl_active.setText(f"Your active loans: {active}")
        else:
            active = count_active_loans()
            self.lbl_active.setText(f"Active loans: {active}")

    # ------------------- Actions -------------------

    def _on_borrow_for_member(self):
        """
        Borrow a book.

        - Librarian mode: type member email + book ISBN.
        - Member mode: email is locked to the logged-in member.
        """
        isbn = self.book_isbn_input.text().strip()
        if not isbn:
            QMessageBox.warning(
                self,
                "Input error",
                "Please enter the book ISBN.",
            )
            return

        # Determine which email to use
        if self.member is not None:
            email = self.member.email.strip().lower()
        else:
            email = self.member_email_input.text().strip()
            if not email:
                QMessageBox.warning(
                    self,
                    "Input error",
                    "Please enter the member email.",
                )
                return

        # Check that member exists (librarian mode mainly; in member mode it should always exist)
        member = find_member_by_email(email)
        if member is None:
            QMessageBox.warning(
                self,
                "Member not found",
                f"No member found with email/username:\n{email}",
            )
            return

        # Check that book exists
        book = find_book_by_isbn(isbn)
        if book is None:
            QMessageBox.warning(
                self,
                "Book not found",
                f"No book found with ISBN:\n{isbn}",
            )
            return

        # Now perform borrow via DAO helper
        success, msg = borrow_book_by_email_and_isbn(email, isbn)

        if success:
            QMessageBox.information(self, "Success", msg)
            self.load_loans_table()
        else:
            QMessageBox.warning(self, "Borrow failed", msg)

    def _on_return_selected_loan(self):
        """
        Mark the currently selected loan as returned.
        """
        loan_id = self._selected_loan_id()
        if loan_id is None:
            QMessageBox.warning(
                self,
                "No selection",
                "Please select a loan in the table first.",
            )
            return

        success, msg = return_book(loan_id)

        if success:
            QMessageBox.information(self, "Returned", msg)
            self.load_loans_table()
        else:
            QMessageBox.warning(self, "Return failed", msg)
