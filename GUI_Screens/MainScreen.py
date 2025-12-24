# GUI_Screens/MainScreen.py

"""
Main Screen for hackintoshify GUI tool
Author: PanCakeeYT (Abdelrahman)
Date: December 2025
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QMessageBox, QFrame, QGraphicsDropShadowEffect
)
from PySide6.QtGui import QFont, QColor, QCursor
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect, QPoint, QSize

class ActionCard(QFrame):
    def __init__(self, title, description, emoji, callback, parent=None):
        super().__init__(parent)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.callback = callback
        self.setObjectName("ActionCard")
        
        # Default Theme Colors (Dark) - Updated via set_theme_colors
        self.bg_normal = "#1e293b"
        self.bg_hover = "#1e293b" # Usually same or slightly lighter
        self.border_normal = "#334155"
        self.border_hover = "#38bdf8"
        
        # Layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(25, 25, 25, 25)
        self.layout.setSpacing(10)
        
        # Emoji/Icon
        self.icon_label = QLabel(emoji)
        self.icon_label.setFont(QFont("Segoe UI Emoji", 32))
        self.icon_label.setStyleSheet("background: transparent; border: none;")
        self.layout.addWidget(self.icon_label)
        
        # Title
        self.title_label = QLabel(title)
        self.title_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self.title_label.setStyleSheet("background: transparent; border: none; color: #f1f5f9;")
        self.layout.addWidget(self.title_label)
        
        # Description
        self.desc_label = QLabel(description)
        self.desc_label.setFont(QFont("Segoe UI", 11))
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet("background: transparent; border: none; color: #94a3b8;")
        self.layout.addWidget(self.desc_label)
        
        self.layout.addStretch()

        # Shadow Effect
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(20)
        self.shadow.setXOffset(0)
        self.shadow.setYOffset(4)
        self.shadow.setColor(QColor(0, 0, 0, 60))
        self.setGraphicsEffect(self.shadow)

        # Animations
        self.anim_hover = QPropertyAnimation(self, b"pos")
        self.anim_hover.setDuration(150)
        self.anim_hover.setEasingCurve(QEasingCurve.OutQuad)

    def set_theme_colors(self, bg, border, text_p, text_s, border_h, shadow_alpha=60):
        self.bg_normal = bg
        self.border_normal = border
        self.border_hover = border_h
        
        # Apply base style immediately
        self.update_style(hover=False)
        self.title_label.setStyleSheet(f"background: transparent; border: none; color: {text_p};")
        self.desc_label.setStyleSheet(f"background: transparent; border: none; color: {text_s};")
        
        # Update Shadow
        self.shadow.setColor(QColor(0, 0, 0, shadow_alpha))

    def update_style(self, hover=False):
        border = self.border_hover if hover else self.border_normal
        # We keep background same for now, or could change it
        self.setStyleSheet(f"""
            #ActionCard {{
                background-color: {self.bg_normal};
                border: 1px solid {border};
                border-radius: 16px;
            }}
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.callback()
    
    def enterEvent(self, event):
        # Lift effect
        self.original_pos = self.pos()
        self.anim_hover.setStartValue(self.pos())
        self.anim_hover.setEndValue(self.pos() + QPoint(0, -4))
        self.anim_hover.start()
        
        # Highlight border
        self.update_style(hover=True)

    def leaveEvent(self, event):
        # Return to position
        self.anim_hover.setStartValue(self.pos())
        self.anim_hover.setEndValue(self.original_pos)
        self.anim_hover.start()
        
        # Remove highlight
        self.update_style(hover=False)

import configparser
import os
import sys

def get_config_path():
    if sys.platform == "win32":
        return os.path.join(os.getenv("ProgramData"), "Hackintoshify", "config.ini")
    elif sys.platform == "darwin":
        return "/Library/Application Support/Hackintoshify/config.ini"
    else: # linux
        return os.path.join(os.path.expanduser("~"), ".config", "hackintoshify", "config.ini")

class MainScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hackintoshify")
        self.setGeometry(100, 100, 1100, 750)
        
        # Load Config
        self.config = configparser.ConfigParser()
        self.config_path = get_config_path()
        self.current_theme = 'Dark' # Default
        try:
            self.config.read(self.config_path)
            if 'Settings' in self.config:
                self.current_theme = self.config['Settings'].get('theme', 'Dark')
        except Exception:
            pass
        
        self._build_ui()
        self.apply_theme(self.current_theme)

    def _build_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # --- Top Bar ---
        top_bar = QFrame()
        top_bar.setObjectName("top_bar")
        top_bar.setFixedHeight(60)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(30, 0, 30, 0)
        
        app_title = QLabel("Hackintoshify")
        app_title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        app_title.setObjectName("app_title")
        
        self.settings_btn = QPushButton("Settings")
        self.settings_btn.setFixedSize(90, 32)
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.clicked.connect(self.open_settings)
        self.settings_btn.setObjectName("settings_btn")
        
        top_layout.addWidget(app_title)
        top_layout.addStretch()
        top_layout.addWidget(self.settings_btn)
        self.main_layout.addWidget(top_bar)

        # Separator Line (Fix for "cut line")
        nav_sep = QFrame()
        nav_sep.setObjectName("nav_sep")
        nav_sep.setFixedHeight(1)
        self.main_layout.addWidget(nav_sep)

        # --- Content Area ---
        content_wrapper = QWidget()
        content_wrapper.setObjectName("content_wrapper")
        content_layout = QVBoxLayout(content_wrapper)
        content_layout.setContentsMargins(50, 40, 50, 40)
        content_layout.setSpacing(40)
        
        # Hero Section
        hero_layout = QVBoxLayout()
        hero_layout.setSpacing(5)
        hero_title = QLabel("Welcome Back")
        hero_title.setFont(QFont("Segoe UI", 32, QFont.Bold))
        hero_title.setObjectName("hero_title")
        
        hero_sub = QLabel("Select an action to begin your hackintosh journey.")
        hero_sub.setFont(QFont("Segoe UI", 14))
        hero_sub.setObjectName("hero_sub")
        
        hero_layout.addWidget(hero_title)
        hero_layout.addWidget(hero_sub)
        content_layout.addLayout(hero_layout)

        # Cards Grid
        grid = QGridLayout()
        grid.setSpacing(25)
        grid.setContentsMargins(0, 10, 0, 10)
        
        self.cards_data = [
            ("Create Installer", "Download macOS and create a bootable USB drive.", "🚀", self.create_installer),
            ("Select Image", "Use a pre-downloaded macOS image file.", "💿", self.select_image),
            ("Select EFI", "Verify and install an existing EFI configuration.", "⚙️", self.select_efi),
            ("Help & Guides", "Documentation and troubleshooting steps.", "❓", self.open_help),
        ]

        for i, (title, desc, emoji, cb) in enumerate(self.cards_data):
            card = ActionCard(title, desc, emoji, cb, self)
            grid.addWidget(card, i // 2, i % 2)
            
        content_layout.addLayout(grid)
        content_layout.addStretch()
        
        self.main_layout.addWidget(content_wrapper)

    def apply_theme(self, theme_name='Dark'):
        self.current_theme = theme_name
        is_dark = theme_name.lower().startswith('dark')
        
        # Theme Palette
        bg_color = "#0f172a" if is_dark else "#f8fafc"      # Slate 900 / Slate 50
        card_bg = "#1e293b" if is_dark else "#ffffff"       # Slate 800 / White
        border_color = "#334155" if is_dark else "#cbd5e1"  # Slate 700 / Slate 300
        text_primary = "#f1f5f9" if is_dark else "#0f172a"  # Slate 100 / Slate 900
        text_secondary = "#94a3b8" if is_dark else "#64748b"# Slate 400 / Slate 500
        accent = "#38bdf8" if is_dark else "#0284c7"        # Sky 400 / Sky 600
        accent_bg = "rgba(56, 189, 248, 0.1)" if is_dark else "rgba(2, 132, 199, 0.1)"

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                font-family: 'Segoe UI', sans-serif;
                color: {text_primary};
            }}
            
            QFrame#top_bar {{
                background-color: {bg_color};
                border: none;
            }}
            
            QFrame#nav_sep {{
                background-color: {border_color};
            }}
            
            QLabel#app_title {{
                color: {text_primary};
            }}
            
            QPushButton#settings_btn {{
                background-color: {accent_bg};
                color: {accent};
                border: 1px solid {accent};
                border-radius: 6px;
                font-weight: 600;
            }}
            QPushButton#settings_btn:hover {{
                background-color: {accent};
                color: {bg_color if is_dark else '#ffffff'};
            }}
            
            QLabel#hero_title {{ color: {text_primary}; }}
            QLabel#hero_sub {{ color: {text_secondary}; }}
        """)
        
        # Update custom ActionCards
        children = self.findChildren(QFrame, "ActionCard")
        for child in children:
            if hasattr(child, 'set_theme_colors'):
                child.set_theme_colors(
                    bg=card_bg,
                    border=border_color,
                    text_p=text_primary,
                    text_s=text_secondary,
                    border_h=accent,
                    shadow_alpha=60 if is_dark else 30
                )

    # Actions
    def create_installer(self):
        QMessageBox.information(self, "Create Installer", "Opening installer creator...")
    
    def select_image(self):
        QMessageBox.information(self, "Select Image", "Opening image selector...")

    def select_efi(self):
        QMessageBox.information(self, "Select EFI", "Opening EFI selector...")

    def open_help(self):
        QMessageBox.information(self, "Help", "Opening guides...")

    def open_settings(self):
        try:
            from .SettingsScreen import SettingsScreen
            dlg = SettingsScreen(parent=self)
            dlg.setWindowModality(Qt.ApplicationModal)
            dlg.show()
        except ImportError:
            QMessageBox.warning(self, "Error", "Settings module not found.")