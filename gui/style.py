# style.py
from PyQt5.QtWidgets import QMainWindow, QWidget

# ====== COLOUR PALETTE (teal / coffee theme) ======
# NOTE: We keep the same variable NAMES so existing code continues to work,
# but the VALUES are now green/teal instead of bright orange.

ORANGE = "#0D9488"       # primary button colour (teal green)
ORANGE_DARK = "#0F766E"  # hover / darker teal
BROWN = "#3F2A1F"        # headings / titles (coffee brown)
BEIGE = "#F4E9DC"        # main background (warm beige)
WHITE = "#FFFFFF"
TEAL = "#14B8A6"         # accent (lighter teal)
GREY = "#E5E7EB"
RED = "#DC2626"

BASE_QSS = f"""
/* ===== General ===== */
QMainWindow, QWidget {{
    background-color: {BEIGE};
    font-family: Segoe UI, Arial;
    color: {BROWN};
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

/* ===== Buttons ===== */
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

QPushButton#Secondary:hover {{
    background-color: rgba(255, 255, 255, 0.8);
}}

/* ===== Tables ===== */
QTableWidget {{
    background-color: {WHITE};
    gridline-color: {GREY};
    alternate-background-color: #FAFAFA;
    border: 1px solid {GREY};
    border-radius: 6px;
}}

QHeaderView::section {{
    background-color: {BEIGE};
    border: 1px solid {GREY};
    padding: 4px;
    font-weight: 600;
}}

/* ===== Inputs ===== */
QLineEdit, QComboBox {{
    background-color: {WHITE};
    border-radius: 4px;
    border: 1px solid {GREY};
    padding: 4px 6px;
}}

/* ===== Dashboard stat cards (we'll use these in member_window.py) ===== */
QFrame#StatCard {{
    background-color: rgba(255, 255, 255, 0.92);
    border-radius: 10px;
    border: 1px solid {GREY};
}}

QLabel#StatLabel {{
    font-size: 11px;
    color: #6B7280;  /* soft grey text */
}}

QLabel#StatValue {{
    font-size: 18px;
    font-weight: 700;
    color: {ORANGE};
}}

/* Progress bar for reading progress (if used) */
QProgressBar {{
    border: 1px solid {GREY};
    border-radius: 6px;
    background: {WHITE};
}}

QProgressBar::chunk {{
    background-color: {ORANGE};
    border-radius: 6px;
}}

/* ===== Overrides for Member dashboard (remove beige background) ===== */
QMainWindow#MemberDashboard,
QWidget#MemberDashboardCentral {{
    background-color: transparent;
}}
"""   # <-- THIS closes BASE_QSS, nothing else goes above it
def apply_base_style(widget):
    widget.setStyleSheet(BASE_QSS)

def apply_base_style(widget):
    widget.setStyleSheet(BASE_QSS)
