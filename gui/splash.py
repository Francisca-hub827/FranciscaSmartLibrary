# splash.py
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from .style import BROWN, BEIGE, WHITE


class SplashScreen(QWidget):

    finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SplashScreen
        )
        self.setFixedSize(460, 260)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(10)

        title = QLabel("Francisca's SmartLibrary")
        title.setObjectName("splashTitle")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            f"font-size: 24px; font-weight: 800; color: {WHITE};"
        )

        subtitle = QLabel(
            "Read • Learn • Rise\n"
            "Librarians: Francisca · Abriel · Abubakar"
        )
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet(
            f"font-size: 12px; color: {BEIGE};"
        )

        layout.addStretch(1)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch(1)

        self.setStyleSheet(f"background-color: {BROWN};")

        QTimer.singleShot(6000, self._done)

    def _done(self):
        self.hide()
        self.finished.emit()
        self.close()
