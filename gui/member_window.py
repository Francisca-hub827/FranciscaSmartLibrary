# members_window.py

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
)

from .style import apply_base_style
from Roots.daos import get_loans_for_member, list_members
# ^^^ if your DAO uses a different name (e.g. list_all_members),
# change list_members to that name.


class MembersWindow(QDialog):
    """
    Librarian view of all members.
    - Top: title
    - Middle: members table (from database)
    - Bottom: summary of loans for the selected member
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Members – Francisca SmartLibrary")
        self.resize(600, 400)

        layout = QVBoxLayout(self)

        # ---- Title label ----
        title = QLabel("Members management")
        title.setObjectName("TitleLabel")
        layout.addWidget(title)

        # ---- Members table ----
        self.table = QTableWidget(self)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Email"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        # ---- Member loan summary (unique feature) ----
        self.member_loan_summary = QLabel("Select a member to see their loans.")
        self.member_loan_summary.setWordWrap(True)
        layout.addWidget(self.member_loan_summary)

        apply_base_style(self)

        # load data + connect selection
        self._load_members()
        self._connect_signals()

    # -------------------------------------------------
    # Helpers
    # -------------------------------------------------

    def _connect_signals(self):
        """
        When the selection changes in the table, update the loan summary.
        """
        self.table.selectionModel().selectionChanged.connect(
            self._update_selected_member_loans
        )

    def _load_members(self):
        """
        Fill the members table from the database.
        Expects list_members() to return a list of Member objects
        with at least: member_id, full_name, email
        """
        members = list_members()

        self.table.setRowCount(len(members))
        for row, m in enumerate(members):
            self.table.setItem(row, 0, QTableWidgetItem(str(m.member_id)))
            self.table.setItem(row, 1, QTableWidgetItem(m.full_name))
            self.table.setItem(row, 2, QTableWidgetItem(m.email))

        # optional: select first row automatically
        if members:
            self.table.selectRow(0)
            self._update_selected_member_loans()

    def _selected_member_id(self) -> int | None:
        """
        Return the member_id of the currently selected row, or None.
        """
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return None

        row = indexes[0].row()
        member_id_item = self.table.item(row, 0)  # column 0 = ID
        if member_id_item is None:
            return None

        return int(member_id_item.text())

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

        # active loans = not yet returned
        active = [l for l in loans if l.return_date is None]
        active_count = len(active)

        if active:
            # earliest due date among active loans
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
