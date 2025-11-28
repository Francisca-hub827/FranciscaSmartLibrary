# style.py

ORANGE = "#F97316"
ORANGE_DARK = "#EA580C"
BROWN = "#4E342E"
BEIGE = "#F5E9DA"
WHITE = "#FFFFFF"
TEAL = "#0D9488"
GREY = "#E5E7EB"
RED = "#DC2626"


BASE_QSS = f"""
QMainWindow, QWidget {{
    background-color: {BEIGE};
    font-family: Segoe UI, Arial;
}}

QLabel#TitleLabel {{
    font-size: 20px;
    font-weight: 700;
    color: {BROWN};
}}

QLabel#SubtitleLabel {{
    font-size: 12px;
    color: {BROWN};
}}

QPushButton {{
    background-color: {ORANGE};
    color: {WHITE};
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 600;
    border: none;
}}

QPushButton:hover {{
    background-color: {ORANGE_DARK};
}}

QPushButton#Secondary {{
    background-color: {WHITE};
    color: {BROWN};
    border-radius: 6px;
    padding: 6px 12px;
    border: 1px solid {GREY};
}}

QTableWidget {{
    background-color: {WHITE};
    gridline-color: {GREY};
    alternate-background-color: #FAFAFA;
}}

QHeaderView::section {{
    background-color: {BEIGE};
    border: 1px solid {GREY};
    padding: 4px;
    font-weight: 600;
}}

QLineEdit, QComboBox {{
    background-color: {WHITE};
    border-radius: 4px;
    border: 1px solid {GREY};
    padding: 4px 6px;
}}
"""


def apply_base_style(widget):
    widget.setStyleSheet(BASE_QSS)
