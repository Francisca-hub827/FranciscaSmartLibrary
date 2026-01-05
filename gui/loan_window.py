# Librarian / Member loan management window for Francisca SmartLibrary
import csv
from datetime import date, datetime
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
    QInputDialog,
)
from PyQt5.QtGui import QColor

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
    create_extension_request,
    list_pending_extension_requests,
    review_extension_request,
)

class ExtensionRequestsDialog(QDialog):
    """
    Librarian view: review all pending loan extension requests.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Loan extension requests")
        self.resize(800, 400)

        layout = QVBoxLayout(self)

        title = QLabel("Pending extension requests")
        title.setObjectName("TitleLabel")
        layout.addWidget(title)

        # Table
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            [
                "Request ID",
                "Member",
                "Email",
                "Book",
                "Current due",
                "Requested new due",
                "Reason",
            ]
        )
        self.table.setSelectionBehavior(self.table.SelectRows)
        self.table.setSelectionMode(self.table.SingleSelection)
        self.table.setEditTriggers(self.table.NoEditTriggers)
        layout.addWidget(self.table)

        # Buttons
        btn_row = QHBoxLayout()
        self.btn_approve = QPushButton("Approve")
        self.btn_reject = QPushButton("Reject")
        self.btn_close = QPushButton("Close")
        btn_row.addWidget(self.btn_approve)
        btn_row.addWidget(self.btn_reject)
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_close)
        layout.addLayout(btn_row)

        apply_base_style(self)
        self._connect()
        self._load_requests()

    def _connect(self):
        self.btn_close.clicked.connect(self.close)
        self.btn_approve.clicked.connect(lambda: self._handle_review(True))
        self.btn_reject.clicked.connect(lambda: self._handle_review(False))

    def _load_requests(self):
        requests = list_pending_extension_requests()
        self.table.setRowCount(len(requests))

        for row, r in enumerate(requests):
            values = [
                str(r["request_id"]),
                r["full_name"],
                r["email"],
                r["title"],
                str(r["current_due_date"]),
                str(r["requested_new_due_date"]),
                r["reason"] or "",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                self.table.setItem(row, col, item)

        self.table.resizeColumnsToContents()

    def _selected_request_id(self) -> int | None:
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return None
        row = indexes[0].row()
        item = self.table.item(row, 0)
        if not item:
            return None
        try:
            return int(item.text())
        except ValueError:
            return None

    def _handle_review(self, approve: bool):
        request_id = self._selected_request_id()
        if request_id is None:
            QMessageBox.warning(self, "No selection", "Select a request first.")
            return

        ok, msg = review_extension_request(request_id, approve)
        if ok:
            QMessageBox.information(self, "Extension request", msg)
            self._load_requests()
        else:
            QMessageBox.warning(self, "Extension request", msg)


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
        self.btn_export = QPushButton("Export to CSV")   # NEW
        self.btn_help = QPushButton("Help")              # NEW

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(
            ["Sort by newest", "Sort by oldest", "Sort by due date"]
        )

        self.btn_refresh = QPushButton("Refresh")

        actions.addWidget(self.btn_borrow)
        actions.addWidget(self.btn_return)
        actions.addWidget(self.btn_export)
        actions.addWidget(self.btn_help)
        actions.addStretch(1)
        actions.addWidget(self.sort_combo)
        actions.addWidget(self.btn_refresh)

        layout.addLayout(actions)


        # Member sees "Request extension", librarian sees "Review requests"
        if self.member is not None:
            actions.addWidget(self.btn_request_extension)
        else:
            actions.addWidget(self.btn_view_requests)

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
        self.btn_export.clicked.connect(self._export_to_csv)  # NEW
        self.btn_help.clicked.connect(self._show_help)  # NEW

        if self.member is not None:
            # Member: can request extension for their own loans
            self.btn_request_extension.clicked.connect(self._on_request_extension)
        else:
            # Librarian: can review all extension requests
            self.btn_view_requests.clicked.connect(self._on_open_extension_requests)


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

        today = date.today()

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

            # --- colour highlighting for due soon / overdue ---
            colour = None
            if loan.return_date is None:
                # active loan
                if loan.due_date < today:
                    # overdue – light red
                    colour = QColor(255, 204, 204)
                else:
                    days_left = (loan.due_date - today).days
                    if days_left <= 3:
                        # due soon – light yellow
                        colour = QColor(255, 249, 196)

            if colour is not None:
                for c in range(self.table.columnCount()):
                    item = self.table.item(row_index, c)
                    if item is not None:
                        item.setBackground(colour)

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


    def _export_to_csv(self):
        """
        Export the loans currently shown in the table to a CSV file.
        Saves as 'smartlibrary_loans_export_YYYYMMDD_HHMMSS.csv'
        in the current working directory.
        """
        row_count = self.table.rowCount()
        col_count = self.table.columnCount()
        if row_count == 0:
            QMessageBox.information(self, "Export", "There are no loans to export.")
            return

        filename = f"smartlibrary_loans_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        try:
            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                # headers
                headers = [
                    self.table.horizontalHeaderItem(c).text()
                    for c in range(col_count)
                ]
                writer.writerow(headers)

                # rows
                for r in range(row_count):
                    row_data = []
                    for c in range(col_count):
                        item = self.table.item(r, c)
                        row_data.append(item.text() if item else "")
                    writer.writerow(row_data)
        except Exception as ex:
            QMessageBox.warning(self, "Export failed", f"Could not write CSV:\n{ex}")
            return

        QMessageBox.information(
            self,
            "Export complete",
            f"Loans exported to:\n{filename}",
        )

    def _show_help(self):
        """
        Show a short explanation of how to use the Loans window.
        """
        text = (
            "How to use this screen:\n\n"
            "- Type the member email and the book ISBN, then click 'Borrow book'.\n"
            "- In member mode, the email is locked to the logged-in member.\n"
            "- Select a row and click 'Return book' to mark it as returned.\n"
            "- Use the drop-down on the right to sort by newest, oldest, or due date.\n"
            "- 'Export to CSV' saves the table data to a CSV file for Excel.\n"
            "- Colours:\n"
            "    • Light yellow = due soon (within 3 days).\n"
            "    • Light red = overdue.\n"
        )
        QMessageBox.information(self, "Loans help", text)



    def _on_request_extension(self):
        """
        Member: request more time for the selected loan.
        """
        loan_id = self._selected_loan_id()
        if loan_id is None:
            QMessageBox.warning(
                self,
                "No selection",
                "Please select one of your loans first.",
            )
            return

        # Ask for new due date
        text, ok = QInputDialog.getText(
            self,
            "Request extension",
            "Requested new due date (YYYY-MM-DD):",
        )
        if not ok or not text.strip():
            return

        from datetime import datetime

        try:
            new_due = datetime.strptime(text.strip(), "%Y-%m-%d").date()
        except ValueError:
            QMessageBox.warning(
                self,
                "Invalid date",
                "Please use the format YYYY-MM-DD.",
            )
            return

        reason, ok2 = QInputDialog.getMultiLineText(
            self,
            "Reason (optional)",
            "Why do you need more time?",
            "",
        )
        if not ok2:
            return

        success, msg = create_extension_request(loan_id, new_due, reason)
        if success:
            QMessageBox.information(self, "Extension request", msg)
        else:
            QMessageBox.warning(self, "Extension request", msg)

    def _on_open_extension_requests(self):
        """
        Librarian: open the dialog listing all pending extension requests.
        """
        dlg = ExtensionRequestsDialog(self)
        dlg.exec_()

