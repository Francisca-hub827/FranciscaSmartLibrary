# login.py
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QComboBox, QLineEdit,
    QPushButton, QHBoxLayout, QFormLayout, QMessageBox, QFrame
)

from .style import apply_base_style
from Roots.daos import authenticate_librarian, authenticate_member


class LoginWindow(QDialog):
    """
    Login screen. User chooses role (Librarian / Member),
    types email + password. We authenticate via DAOs and
    return a Librarian or Member object to the caller.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SmartLibrary – Login")
        self.resize(420, 280)
        self.logged_in_user = None
        self.role = "librarian"   # default role

        # ---- layout ----
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(10)

        title = QLabel("Welcome to Francisca SmartLibrary")
        title.setObjectName("TitleLabel")

        subtitle = QLabel("Sign in as Librarian (admin) or Member (user).")
        subtitle.setObjectName("SubtitleLabel")

        root.addWidget(title)
        root.addWidget(subtitle)

        card = QFrame()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(8)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)

        self.role_combo = QComboBox()
        self.role_combo.addItems(["Librarian (Admin)", "Member (User)"])
        self.role_combo.currentIndexChanged.connect(self._on_role_changed)

        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("Email (e.g. francisca.kabina@smartlibrary.edu)")

        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Password")
        self.password_edit.setEchoMode(QLineEdit.Password)

        form.addRow("Role:", self.role_combo)
        form.addRow("Email:", self.email_edit)
        form.addRow("Password:", self.password_edit)

        card_layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("Secondary")
        self.btn_login = QPushButton("Login")

        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_login)

        card_layout.addLayout(btn_row)
        root.addWidget(card, 1)

        apply_base_style(self)

        # signals
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_login.clicked.connect(self._handle_login)

    def _on_role_changed(self, index: int):
        # index 0 -> Librarian, 1 -> Member
        self.role = "librarian" if index == 0 else "member"

    def _handle_login(self):
        email = self.email_edit.text().strip()
        password = self.password_edit.text().strip()

        if not email or not password:
            QMessageBox.warning(self, "Missing data", "Please enter email and password.")
            return

        if self.role == "librarian":
            user = authenticate_librarian(email, password)
            if user is None:
                QMessageBox.critical(
                    self,
                    "Login failed",
                    "Unknown librarian.\nUse one of: Francisca, Abril, Abubakar emails.",
                )
                return
        else:
            user = authenticate_member(email, password)
            if user is None:
                QMessageBox.critical(
                    self,
                    "Login failed",
                    "Member not found in the system.",
                )
                return

        self.logged_in_user = user
        self.accept()
