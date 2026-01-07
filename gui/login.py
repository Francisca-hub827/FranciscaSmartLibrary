# login.py

import os
import random
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QComboBox, QLineEdit,
    QPushButton, QHBoxLayout, QFormLayout, QMessageBox, QFrame
)

from .style import apply_base_style
from Roots.daos import authenticate_librarian, authenticate_member

MOTIVATION_LINES = [
    "Sign in and let your next chapter begin.",
    "Stories, notes and smart loans – all in one place.",
    "Welcome back – your books missed you.",
    "Today is a good day to finish a chapter.",
]


class LoginWindow(QDialog):
    """
    Login screen with Pinterest-style background image.

    - Full window background = gui/assets/library_bg.jpg
    - White rounded card in the centre with form + buttons.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("LoginWindow")
        self.setWindowTitle("SmartLibrary – Login")

        # Show normal window buttons (min, max)
        self.setWindowFlag(Qt.WindowMinimizeButtonHint, True)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)

        # Start maximised so the background fills the screen
        self.setWindowState(Qt.WindowMaximized)

        self.logged_in_user = None
        self.role = "librarian"   # default

        # =========================
        #  ROOT LAYOUT + BACKGROUND
        # =========================
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Background image label
        self.bg_label = QLabel()
        self.bg_label.setObjectName("BgLabel")
        self.bg_label.setScaledContents(True)  # image stretches to fill window
        root.addWidget(self.bg_label)

        # Layout ON TOP of the background label (overlay)
        overlay = QVBoxLayout(self.bg_label)
        overlay.setContentsMargins(40, 40, 40, 40)
        overlay.setSpacing(10)

        # =========================
        #  PINK HEADER STRIP
        # =========================
        header_frame = QFrame()
        header_frame.setObjectName("LoginHeaderFrame")
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(24, 16, 24, 18)
        header_layout.setSpacing(4)

        title = QLabel("Welcome to Francisca SmartLibrary")
        title.setObjectName("LoginTitleLabel")
        title.setAlignment(Qt.AlignHCenter)

        subtitle_text = random.choice(MOTIVATION_LINES)
        subtitle = QLabel(
            subtitle_text + "\nSign in as Librarian (admin) or Member (user)."
        )
        subtitle.setObjectName("LoginSubtitleLabel")
        subtitle.setAlignment(Qt.AlignHCenter)

        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)

        overlay.addWidget(header_frame)

        # =========================
        #  LOGIN CARD
        # =========================
        card = QFrame()
        card.setObjectName("LoginCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(10)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)

        self.role_combo = QComboBox()
        self.role_combo.addItems(["Librarian (Admin)", "Member (User)"])
        self.role_combo.currentIndexChanged.connect(self._on_role_changed)

        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText(
            "Email (e.g. francisca.kabina@smartlibrary.edu)"
        )

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

        # Centre the card vertically
        overlay.addStretch(1)
        overlay.addWidget(card, 0, Qt.AlignHCenter)
        overlay.addStretch(2)

        # =========================
        #  STYLES + SIGNALS
        # =========================
        apply_base_style(self)         # your existing theme (fonts, base colours)
        self._apply_card_styles()      # extra styles for header/card/buttons
        self._load_background_image()  # Pinterest image

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_login.clicked.connect(self._handle_login)

    # -------------------------------------------------
    #  VISUALS
    # -------------------------------------------------
    def _load_background_image(self):
        """
        Load gui/assets/library_bg.jpg into self.bg_label.
        """
        base_dir = os.path.dirname(os.path.abspath(__file__))
        bg_path = os.path.join(base_dir, "assets", "library_bg.jpg")

        print("LOGIN BG: looking for:", bg_path)

        if not os.path.exists(bg_path):
            print("LOGIN BG: file NOT found")
            return

        pix = QPixmap(bg_path)
        if pix.isNull():
            print("LOGIN BG: failed to load pixmap (isNull=True)")
            return

        print("LOGIN BG: loaded OK")
        self.bg_label.setPixmap(pix)

    def _apply_card_styles(self):
        """
        Style the floating login card and the header text.
        """
        self.setStyleSheet("""
        QFrame#LoginCard {
            background: rgba(255, 255, 255, 0.94);
            border-radius: 18px;
        }

        /* Pink header strip */
        QFrame#LoginHeaderFrame {
            background: rgba(255, 255, 255, 0.90);
            border-radius: 18px;
            border: 2px solid #F9A8D4;   /* soft pink border */
        }

        QLabel#LoginTitleLabel {
            color: #BE185D;              /* deep pink */
            font-size: 32px;
            font-weight: 800;
        }

        QLabel#LoginSubtitleLabel {
            color: #4B5563;              /* soft grey */
            font-size: 14px;
        }

        QLineEdit {
            background: #ffffff;
            border-radius: 8px;
            padding: 6px 10px;
        }

        QPushButton {
            min-width: 95px;
            padding: 6px 12px;
            border-radius: 10px;
            font-weight: 600;
        }

        QPushButton#Secondary {
            background: transparent;
            border: 1px solid #FBCFE8;
            color: #9D174D;
        }

        QPushButton#Secondary:hover {
            background: rgba(252, 231, 243, 0.6);
        }

        QPushButton:not(#Secondary) {
            background-color: #EC4899;   /* main pink button */
            color: white;
            border: none;
        }

        QPushButton:not(#Secondary):hover {
            background-color: #DB2777;
        }
        """)

    # -------------------------------------------------
    #  LOGIC
    # -------------------------------------------------
    def _on_role_changed(self, index: int):
        # 0 -> Librarian, 1 -> Member
        self.role = "librarian" if index == 0 else "member"

    def _handle_login(self):
        email = self.email_edit.text().strip()
        password = self.password_edit.text().strip()

        if not email or not password:
            QMessageBox.warning(self, "Missing data",
                                "Please enter email and password.")
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
