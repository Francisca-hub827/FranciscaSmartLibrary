# club_window.py
#
# Book club management for Francisca SmartLibrary.
# - Librarian view: manage clubs, add/remove members
# - Member view: join / leave clubs

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QLineEdit, QMessageBox, QInputDialog
)

from .style import apply_base_style
from Roots.daos import (
    list_all_clubs,
    list_members_in_club,
    create_club,
    delete_club,
    add_member_to_club,
    remove_member_from_club,
    list_clubs_for_member,
    list_clubs_not_joined,
    find_member_by_email,
)


# -------------------------------
# 1) Librarian clubs window
# -------------------------------

class LibrarianClubsWindow(QDialog):
    """Full club management for librarians."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Book clubs – Francisca SmartLibrary")
        self.resize(900, 500)

        layout = QVBoxLayout(self)

        header = QLabel("Manage book clubs – create clubs and assign members.")
        header.setObjectName("TitleLabel")

        layout.addWidget(header)

        # Two tables side by side
        center = QHBoxLayout()

        self.clubs_table = QTableWidget(0, 3)
        self.clubs_table.setHorizontalHeaderLabels(["ID", "Name", "Description"])
        self.clubs_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.clubs_table.setSelectionMode(QTableWidget.SingleSelection)

        self.members_table = QTableWidget(0, 3)
        self.members_table.setHorizontalHeaderLabels(["Member ID", "Name", "Email"])
        self.members_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.members_table.setSelectionMode(QTableWidget.SingleSelection)

        center.addWidget(self.clubs_table, 2)
        center.addWidget(self.members_table, 3)
        layout.addLayout(center)

        # Buttons row
        btn_row = QHBoxLayout()

        self.add_club_btn = QPushButton("Add club")
        self.delete_club_btn = QPushButton("Delete club")
        self.add_member_btn = QPushButton("Add member to club")
        self.remove_member_btn = QPushButton("Remove member")
        self.refresh_btn = QPushButton("Refresh")
        self.close_btn = QPushButton("Close")

        btn_row.addWidget(self.add_club_btn)
        btn_row.addWidget(self.delete_club_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(self.add_member_btn)
        btn_row.addWidget(self.remove_member_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(self.refresh_btn)
        btn_row.addWidget(self.close_btn)

        layout.addLayout(btn_row)

        apply_base_style(self)

        # Signals
        self.clubs_table.selectionModel().selectionChanged.connect(
            self._on_club_selected
        )
        self.add_club_btn.clicked.connect(self._on_add_club)
        self.delete_club_btn.clicked.connect(self._on_delete_club)
        self.add_member_btn.clicked.connect(self._on_add_member)
        self.remove_member_btn.clicked.connect(self._on_remove_member)
        self.refresh_btn.clicked.connect(self.load_data)
        self.close_btn.clicked.connect(self.close)

        # initial load
        self.load_data()

    # ---- data loading helpers ----

    def load_data(self):
        self._load_clubs()
        self._load_members_for_selected()

    def _load_clubs(self):
        clubs = list_all_clubs()
        self.clubs_table.setRowCount(len(clubs))
        for row_idx, club in enumerate(clubs):
            self.clubs_table.setItem(row_idx, 0, QTableWidgetItem(str(club["club_id"])))
            self.clubs_table.setItem(row_idx, 1, QTableWidgetItem(club["name"]))
            self.clubs_table.setItem(
                row_idx, 2, QTableWidgetItem(club.get("description") or "")
            )
        self.clubs_table.resizeColumnsToContents()

    def _current_club_id(self):
        indexes = self.clubs_table.selectionModel().selectedRows()
        if not indexes:
            return None
        row = indexes[0].row()
        item = self.clubs_table.item(row, 0)
        if not item:
            return None
        try:
            return int(item.text())
        except ValueError:
            return None

    def _load_members_for_selected(self):
        club_id = self._current_club_id()
        if club_id is None:
            self.members_table.setRowCount(0)
            return

        members = list_members_in_club(club_id)
        self.members_table.setRowCount(len(members))
        for row_idx, m in enumerate(members):
            self.members_table.setItem(row_idx, 0, QTableWidgetItem(str(m["member_id"])))
            self.members_table.setItem(row_idx, 1, QTableWidgetItem(m["full_name"]))
            self.members_table.setItem(row_idx, 2, QTableWidgetItem(m["email"]))
        self.members_table.resizeColumnsToContents()

    # ---- slots ----

    def _on_club_selected(self, *_):
        self._load_members_for_selected()

    def _on_add_club(self):
        name, ok = QInputDialog.getText(self, "New club", "Club name:")
        if not ok or not name.strip():
            return
        desc, _ = QInputDialog.getText(self, "New club", "Description (optional):")

        success, msg = create_club(name, desc or "")
        if success:
            QMessageBox.information(self, "Club created", msg)
            self.load_data()
        else:
            QMessageBox.warning(self, "Could not create", msg)

    def _on_delete_club(self):
        club_id = self._current_club_id()
        if club_id is None:
            QMessageBox.warning(self, "No club selected", "Select a club first.")
            return
        reply = QMessageBox.question(
            self,
            "Delete club",
            "Are you sure you want to delete this club?\n"
            "All memberships in this club will be removed.",
        )
        if reply != QMessageBox.Yes:
            return

        success, msg = delete_club(club_id)
        if success:
            QMessageBox.information(self, "Club deleted", msg)
            self.load_data()
        else:
            QMessageBox.warning(self, "Could not delete", msg)

    def _on_add_member(self):
        club_id = self._current_club_id()
        if club_id is None:
            QMessageBox.warning(self, "No club selected", "Select a club first.")
            return

        email, ok = QInputDialog.getText(
            self, "Add member", "Enter member email (as in system):"
        )
        if not ok or not email.strip():
            return

        member = find_member_by_email(email)
        if not member:
            QMessageBox.warning(self, "Not found", "No member with that email.")
            return

        success, msg = add_member_to_club(member.member_id, club_id)
        if success:
            QMessageBox.information(self, "Member added", msg)
            self._load_members_for_selected()
        else:
            QMessageBox.warning(self, "Could not add", msg)

    def _on_remove_member(self):
        club_id = self._current_club_id()
        if club_id is None:
            QMessageBox.warning(self, "No club selected", "Select a club first.")
            return

        indexes = self.members_table.selectionModel().selectedRows()
        if not indexes:
            QMessageBox.warning(self, "No member selected", "Select a member first.")
            return

        row = indexes[0].row()
        item = self.members_table.item(row, 0)
        member_id = int(item.text())

        success, msg = remove_member_from_club(member_id, club_id)
        if success:
            QMessageBox.information(self, "Member removed", msg)
            self._load_members_for_selected()
        else:
            QMessageBox.warning(self, "Could not remove", msg)


# -------------------------------
# 2) Member clubs window
# -------------------------------

class MemberClubsWindow(QDialog):
    """Allow a member to join / leave clubs from their own dashboard."""

    def __init__(self, parent=None, member=None):
        super().__init__(parent)
        self.member = member
        self.setWindowTitle("My book clubs – Francisca SmartLibrary")
        self.resize(800, 450)

        layout = QVBoxLayout(self)

        name = member.full_name if member is not None else "member"
        header = QLabel(f"Book clubs for {name}")
        header.setObjectName("TitleLabel")
        layout.addWidget(header)

        center = QHBoxLayout()

        # left: clubs they can join
        self.available_table = QTableWidget(0, 2)
        self.available_table.setHorizontalHeaderLabels(["Club ID", "Club name"])
        self.available_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.available_table.setSelectionMode(QTableWidget.SingleSelection)

        # right: clubs they are already in
        self.my_table = QTableWidget(0, 2)
        self.my_table.setHorizontalHeaderLabels(["Club ID", "Club name"])
        self.my_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.my_table.setSelectionMode(QTableWidget.SingleSelection)

        center.addWidget(self.available_table, 1)
        center.addWidget(self.my_table, 1)

        layout.addLayout(center)

        # buttons
        btn_row = QHBoxLayout()
        self.join_btn = QPushButton("Join selected club")
        self.leave_btn = QPushButton("Leave selected club")
        self.close_btn = QPushButton("Close")

        btn_row.addWidget(self.join_btn)
        btn_row.addWidget(self.leave_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(self.close_btn)

        layout.addLayout(btn_row)

        apply_base_style(self)

        # signals
        self.join_btn.clicked.connect(self._on_join)
        self.leave_btn.clicked.connect(self._on_leave)
        self.close_btn.clicked.connect(self.close)

        self.load_data()

    # helpers

    def _current_id_from_table(self, table: QTableWidget):
        indexes = table.selectionModel().selectedRows()
        if not indexes:
            return None
        row = indexes[0].row()
        item = table.item(row, 0)
        if not item:
            return None
        try:
            return int(item.text())
        except ValueError:
            return None

    def load_data(self):
        if self.member is None:
            return

        my = list_clubs_for_member(self.member.member_id)
        avail = list_clubs_not_joined(self.member.member_id)

        # available
        self.available_table.setRowCount(len(avail))
        for r, c in enumerate(avail):
            self.available_table.setItem(r, 0, QTableWidgetItem(str(c["club_id"])))
            self.available_table.setItem(r, 1, QTableWidgetItem(c["name"]))
        self.available_table.resizeColumnsToContents()

        # my clubs
        self.my_table.setRowCount(len(my))
        for r, c in enumerate(my):
            self.my_table.setItem(r, 0, QTableWidgetItem(str(c["club_id"])))
            self.my_table.setItem(r, 1, QTableWidgetItem(c["name"]))
        self.my_table.resizeColumnsToContents()

    # slots

    def _on_join(self):
        club_id = self._current_id_from_table(self.available_table)
        if club_id is None:
            QMessageBox.warning(self, "No selection", "Select a club to join.")
            return

        success, msg = add_member_to_club(self.member.member_id, club_id)
        if success:
            QMessageBox.information(self, "Joined", msg)
            self.load_data()
        else:
            QMessageBox.warning(self, "Could not join", msg)

    def _on_leave(self):
        club_id = self._current_id_from_table(self.my_table)
        if club_id is None:
            QMessageBox.warning(self, "No selection", "Select a club to leave.")
            return

        success, msg = remove_member_from_club(self.member.member_id, club_id)
        if success:
            QMessageBox.information(self, "Left club", msg)
            self.load_data()
        else:
            QMessageBox.warning(self, "Could not leave", msg)
