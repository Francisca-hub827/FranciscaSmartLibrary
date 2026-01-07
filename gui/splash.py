# splash.py  – pink girl-power splash for Francisca SmartLibrary

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QProgressBar,
)

from .style import apply_base_style, PINK, BLUSH, WHITE, TEXT_DARK, TEXT_MUTED


class SplashScreen(QWidget):
    """
    Small splash window shown before login.

    - Cute pink progress bar
    - Automatically closes after a short time
    - Emits `finished` so app.py can open the LoginWindow
    """

    finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.SplashScreen
        )
        self.setObjectName("SplashScreen")
        self.setFixedSize(420, 220)

        # ------------ Layout ------------
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        card = QFrame()
        card.setObjectName("SplashCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setSpacing(12)

        title = QLabel("Francisca SmartLibrary")
        title.setAlignment(Qt.AlignHCenter)
        title.setStyleSheet(
            f"font-size: 18px; font-weight: 800; color: {TEXT_DARK};"
        )

        subtitle = QLabel("Loading your girl-power library experience…")
        subtitle.setAlignment(Qt.AlignHCenter)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(
            f"font-size: 12px; color: {TEXT_MUTED};"
        )

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(
            f"""
            QProgressBar {{
                background-color: {WHITE};
                border-radius: 6px;
                border: 1px solid #E5E7EB;
                min-height: 10px;
            }}
            QProgressBar::chunk {{
                background-color: {PINK};
                border-radius: 6px;
            }}
            """
        )

        footer = QLabel("Tip: You’re just a few clicks away from your next great book.")
        footer.setAlignment(Qt.AlignHCenter)
        footer.setWordWrap(True)
        footer.setStyleSheet(
            f"font-size: 11px; color: {TEXT_MUTED};"
        )

        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addWidget(self.progress_bar)
        card_layout.addWidget(footer)

        layout.addWidget(card)

        apply_base_style(self)
        self._apply_card_style()

        # ------------ Timer / progress ------------
        self._progress = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance_progress)
        # ~2.5 seconds total: 50 ms * 50 steps
        self._timer.start(50)

        # Centre on screen
        self._center_on_screen()

    def _center_on_screen(self):
        screen = self.screen()
        if not screen:
            return
        geo = screen.geometry()
        x = geo.x() + (geo.width() - self.width()) // 2
        y = geo.y() + (geo.height() - self.height()) // 2
        self.move(x, y)

    def _apply_card_style(self):
        self.setStyleSheet(
            self.styleSheet()
            + f"""
            QWidget#SplashScreen {{
                background-color: transparent;
            }}
            QFrame#SplashCard {{
                background-color: {BLUSH};
                border-radius: 18px;
                border: 1px solid #F9A8D4;
            }}
            """
        )

    def _advance_progress(self):
        """
        Called repeatedly by the timer.
        Once progress reaches 100, stop timer, emit finished and fully remove
        the splash widget so it cannot stay on the login screen.
        """
        self._progress += 4
        if self._progress >= 100:
            self._progress = 100
            self.progress_bar.setValue(self._progress)

            # Stop the timer first
            self._timer.stop()

            # 👇 make absolutely sure the splash disappears
            self.hide()          # remove from the screen
            self.finished.emit() # tell app.py "I'm done"
            self.deleteLater()   # mark the widget to be destroyed

            return

        self.progress_bar.setValue(self._progress)

