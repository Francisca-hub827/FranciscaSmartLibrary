# gui/members_window.py

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
    QHBoxLayout,
    QPushButton,
    QLineEdit,
    QMessageBox,
)

from .style import apply_base_style
from Roots.daos import (
    get_loans_for_member,
    list_members,
    create_member,
    update_member,
    delete_member,
)


class MemberFormDialog(QDialog):
    """
    Small popup form used for:
      - adding a new member
      - editing an existing member

    For "edit" mode, password fields are optional. If left blank,
    the password stays the same.
    """

    def __init__(
        self,
        parent=None,
        *,
        mode: str = "add",  # "add" or "edit"
        full_name: str = "",
        email: str = "",
    ):
        super().__init__(parent)
        self.mode = mode

        if self.mode == "add":
            self.setWindowTitle("Add new member")
        else:
            self.setWindowTitle("Edit member")

        layout = QVBoxLayout(self)

        # Title
        title = QLabel(
            "Add new member" if mode == "add" else "Edit member details"
        )
        title.setObjectName("TitleLabel")
        layout.addWidget(title)

        # Full name
        self.full_name_edit = QLineEdit(self)
        self.full_name_edit.setPlaceholderText("Full name")
        self.full_name_edit.setText(full_name)
        layout.addWidget(QLabel("Full name:"))
        layout.addWidget(self.full_name_edit)

        # Email
        self.email_edit = QLineEdit(self)
        self.email_edit.setPlaceholderText("Email (used for login)")
        self.email_edit.setText(email)
        layout.addWidget(QLabel("Email:"))
        layout.addWidget(self.email_edit)

        # Password fields
        self.password_edit = QLineEdit(self)
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText(
            "Password" if mode == "add" else "New password (optional)"
        )

        self.confirm_password_edit = QLineEdit(self)
        self.confirm_password_edit.setEchoMode(QLineEdit.Password)
        self.confirm_password_edit.setPlaceholderText(
            "Confirm password" if mode == "add" else "Confirm new password (optional)"
        )

        layout.addWidget(QLabel("Password:"))
        layout.addWidget(self.password_edit)
        layout.addWidget(QLabel("Confirm password:"))
        layout.addWidget(self.confirm_password_edit)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_ok = QPushButton("Save", self)
        self.btn_cancel = QPushButton("Cancel", self)
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

        self.btn_ok.clicked.connect(self._on_save_clicked)
        self.btn_cancel.clicked.connect(self.reject)

        apply_base_style(self)

    # -------------- helpers -----------------

    def _on_save_clicked(self):
        full_name = self.full_name_edit.text().strip()
        email = self.email_edit.text().strip()
        pwd = self.password_edit.text()
        pwd2 = self.confirm_password_edit.text()

        if not full_name:
            QMessageBox.warning(self, "Validation", "Full name cannot be empty.")
            return

        if "@" not in email:
            QMessageBox.warning(self, "Validation", "Please enter a valid email.")
            return

        # For "add" mode → password is required
        if self.mode == "add":
            if not pwd or not pwd2:
                QMessageBox.warning(
                    self, "Validation", "Password and confirmation are required."
                )
                return
        # For "edit" mode → allowed to leave password empty (no change)
        if pwd or pwd2:
            if pwd != pwd2:
                QMessageBox.warning(
                    self, "Validation", "Passwords do not match."
                )
                return

        self._full_name = full_name
        self._email = email
        # For "edit" mode, password may be empty string → means "no change"
        self._password = pwd if pwd else None

        self.accept()

    def get_data(self):
        """Return (full_name, email, password or None)."""
        return self._full_name, self._email, self._password


class MembersWindow(QDialog):
    """
    Librarian view of all members.

    Now supports:
      - Add member
      - Edit member
      - Delete member
      - Refresh
      - Summary of active loans for selected member
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Members – Francisca SmartLibrary")
        self.resize(700, 450)

        layout = QVBoxLayout(self)

        # ---- Title label ----
        title = QLabel("Members management")
        title.setObjectName("TitleLabel")
        layout.addWidget(title)

        # ---- Buttons row (Add / Edit / Delete / Refresh) ----
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("Add member")
        self.btn_edit = QPushButton("Edit member")
        self.btn_delete = QPushButton("Delete member")
        self.btn_refresh = QPushButton("Refresh")

        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addWidget(self.btn_refresh)

        layout.addLayout(btn_layout)

        # ---- Members table ----
        self.table = QTableWidget(self)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Email"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        # ---- Member loan summary (bottom label) ----
        self.member_loan_summary = QLabel("Select a member to see their loans.")
        self.member_loan_summary.setWordWrap(True)
        layout.addWidget(self.member_loan_summary)

        apply_base_style(self)

        # load data + connect signals
        self._load_members()
        self._connect_signals()

    # -------------------------------------------------
    # Wiring
    # -------------------------------------------------

    def _connect_signals(self):
        # Selection in table → update loan summary
        self.table.selectionModel().selectionChanged.connect(
            self._update_selected_member_loans
        )

        # Buttons
        self.btn_add.clicked.connect(self._on_add_member)
        self.btn_edit.clicked.connect(self._on_edit_member)
        self.btn_delete.clicked.connect(self._on_delete_member)
        self.btn_refresh.clicked.connect(self._load_members)

    # -------------------------------------------------
    # Data loading
    # -------------------------------------------------

    def _load_members(self):
        """
        Fill the members table from the database.
        Expects list_members() to return a list of Member objects
        with at least: member_id, full_name, email.
        """
        members = list_members()

        self.table.setRowCount(len(members))
        for row, m in enumerate(members):
            self.table.setItem(row, 0, QTableWidgetItem(str(m.member_id)))
            self.table.setItem(row, 1, QTableWidgetItem(m.full_name))
            self.table.setItem(row, 2, QTableWidgetItem(m.email))

        if members:
            self.table.selectRow(0)
            self._update_selected_member_loans()
        else:
            self.member_loan_summary.setText("No members in the system yet.")

    # -------------------------------------------------
    # Helpers
    # -------------------------------------------------

    def _selected_member_id(self) -> int | None:
        """
        Return the member_id of the currently selected row, or None.
        """
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return None

        row = indexes[0].row()
        item = self.table.item(row, 0)  # column 0 = ID
        if item is None:
            return None

        try:
            return int(item.text())
        except ValueError:
            return None

    def _selected_member_name_email(self) -> tuple[str, str] | None:
        """
        Return (name, email) of the selected member row, or None.
        """
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return None
        row = indexes[0].row()
        name_item = self.table.item(row, 1)
        email_item = self.table.item(row, 2)
        if not name_item or not email_item:
            return None
        return name_item.text(), email_item.text()

    # -------------------------------------------------
    # Loan summary
    # -------------------------------------------------

    def _update_selected_member_loans(self, *_) -> None:
        """
        Update the bottom summary label when a member is selected.
        Shows:
          - number of active loans
          - nearest due date
          - titles of books on loan
        """
        member_id = self._selected_member_id()
        if member_id is None:
            self.member_loan_summary.setText("Select a member to see their loans.")
            return

        loans = get_loans_for_member(member_id)

        active = [l for l in loans if l.return_date is None]
        active_count = len(active)

        if active:
            next_due = min(l.due_date for l in active)
            titles = ", ".join(l.book.title for l in active)
            text = (
                f"Active loans: {active_count}  |  "
                f"Next due: {next_due}  |  "
                f"Books: {titles}"
            )
        else:
            text = "This member has no active loans."

        self.member_loan_summary.setText(text)

    # -------------------------------------------------
    # Button handlers
    # -------------------------------------------------

    def _on_add_member(self):
        dlg = MemberFormDialog(self, mode="add")
        if dlg.exec_() != QDialog.Accepted:
            return

        full_name, email, password = dlg.get_data()
        ok, msg = create_member(full_name, email, password or "")
        if ok:
            QMessageBox.information(self, "Add member", msg)
            self._load_members()
        else:
            QMessageBox.warning(self, "Add member", msg)

    def _on_edit_member(self):
        member_id = self._selected_member_id()
        if member_id is None:
            QMessageBox.warning(self, "Edit member", "Please select a member first.")
            return

        name_email = self._selected_member_name_email()
        if not name_email:
            QMessageBox.warning(self, "Edit member", "Could not read member details.")
            return

        full_name, email = name_email
        dlg = MemberFormDialog(
            self, mode="edit", full_name=full_name, email=email
        )
        if dlg.exec_() != QDialog.Accepted:
            return

        new_full_name, new_email, new_password = dlg.get_data()
        ok, msg = update_member(member_id, new_full_name, new_email, new_password)
        if ok:
            QMessageBox.information(self, "Edit member", msg)
            self._load_members()
        else:
            QMessageBox.warning(self, "Edit member", msg)

    def _on_delete_member(self):
        member_id = self._selected_member_id()
        if member_id is None:
            QMessageBox.warning(self, "Delete member", "Please select a member first.")
            return

        reply = QMessageBox.question(
            self,
            "Delete member",
            "Are you sure you want to delete this member?\n"
            "This will also remove their loans and club memberships.",
        )
        if reply != QMessageBox.Yes:
            return

        ok, msg = delete_member(member_id)
        if ok:
            QMessageBox.information(self, "Delete member", msg)
            self._load_members()
        else:
            QMessageBox.warning(self, "Delete member", msg)
