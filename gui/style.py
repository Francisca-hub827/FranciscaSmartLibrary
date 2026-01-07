# style.py
from PyQt5.QtWidgets import QMainWindow, QWidget

# ====== GIRL-POWER PALETTE (soft pink / Pinterest) ======
PINK = "#EC4899"        # main accent / buttons
PINK_DARK = "#DB2777"   # hover / stronger accent
BLUSH = "#FFF5F7"       # very light pink background
LILAC = "#E9D5FF"       # soft purple for accents if needed
WHITE = "#FFFFFF"
TEXT_DARK = "#111827"   # near-black text
TEXT_MUTED = "#6B7280"  # grey for hints
BORDER = "#E5E7EB"
ALERT_RED = "#EF4444"

BASE_QSS = f"""
/* ===== General ===== */
QMainWindow, QWidget {{
    background-color: {BLUSH};
    font-family: Segoe UI, Arial;
    color: {TEXT_DARK};
}}

/* ===== Big titles / section headers ===== */
QLabel#TitleLabel {{
    font-size: 22px;
    font-weight: 800;
    color: {TEXT_DARK};
}}

QLabel#SubtitleLabel {{
    font-size: 13px;
    color: {TEXT_MUTED};
}}

/* Top “Welcome, Tracy Coker” on member dashboard */
QLabel#MemberWelcomeTitle {{
    font-size: 24px;
    font-weight: 900;
    color: {TEXT_DARK};
}}

QLabel#MemberWelcomeSubtitle {{
    font-size: 13px;
    color: {TEXT_MUTED};
}}

/* Small hint / footer text on dashboard */
QLabel#MemberHintLabel {{
    font-size: 11px;
    color: {TEXT_MUTED};
}}

/* Badge line: “Badge: New Reader – Books finished: 0” */
QLabel#BadgeLabel {{
    font-size: 12px;
    font-weight: 700;
    color: {ALERT_RED};
}}

/* ===== Buttons ===== */
QPushButton {{
    background-color: {PINK};
    color: {WHITE};
    border-radius: 6px;
    padding: 8px 14px;
    font-weight: 600;
    border: none;
}}

QPushButton:hover {{
    background-color: {PINK_DARK};
}}

QPushButton#Secondary {{
    background-color: {WHITE};
    color: {TEXT_DARK};
    border-radius: 6px;
    padding: 6px 12px;
    border: 1px solid {BORDER};
}}

QPushButton#Secondary:hover {{
    background-color: rgba(255, 255, 255, 0.9);
}}

/* Member dashboard quick-action buttons (right side) */
QPushButton#DashboardAction {{
    font-size: 13px;
}}

/* ===== Tables ===== */
QTableWidget {{
    background-color: {WHITE};
    gridline-color: {BORDER};
    alternate-background-color: #FAFAFA;
    border: 1px solid {BORDER};
    border-radius: 6px;
}}

QHeaderView::section {{
    background-color: {LILAC};
    border: 1px solid {BORDER};
    padding: 4px;
    font-weight: 600;
}}

/* ===== Inputs ===== */
QLineEdit, QComboBox {{
    background-color: {WHITE};
    border-radius: 4px;
    border: 1px solid {BORDER};
    padding: 4px 6px;
}}

/* ===== Dashboard cards (big left + right panels) ===== */
QFrame#MemberDashboardCard {{
    background-color: {WHITE};
    border-radius: 14px;
    border: 1px solid {BORDER};
}}

QLabel#StatLabel {{
    font-size: 11px;
    color: {TEXT_MUTED};
}}

QLabel#StatValue {{
    font-size: 18px;
    font-weight: 700;
    color: {PINK};
}}

/* Progress bar for reading progress */
QProgressBar {{
    border: 1px solid {BORDER};
    border-radius: 6px;
    background: {WHITE};
}}

QProgressBar::chunk {{
    background-color: {PINK};
    border-radius: 6px;
}}

/* ===== Login screen header ===== */

QFrame#LoginHeaderFrame {{
    background-color: rgba(236, 72, 153, 220);   /* soft pink strip */
    border-radius: 12px;
    padding: 18px 26px;
}}

QLabel#LoginTitleLabel {{
    font-size: 28px;
    font-weight: 900;
    color: {WHITE};
}}

QLabel#LoginSubtitleLabel {{
    font-size: 13px;
    color: {WHITE};
}}

/* Let background image show, keep central widgets clean */
QMainWindow#MemberDashboard,
QWidget#MemberDashboardCentral {{
    background-color: transparent;
}}
"""

def apply_base_style(widget):
    widget.setStyleSheet(BASE_QSS)
