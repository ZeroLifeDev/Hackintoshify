from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QComboBox, QCheckBox, QPushButton, QHBoxLayout, QMessageBox, QFrame,
    QFileDialog, QLineEdit, QScrollArea, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
import configparser
import os
import sys
import json

def get_config_path():
    if sys.platform == "win32":
        return os.path.join(os.getenv("ProgramData"), "Hackintoshify", "config.ini")
    elif sys.platform == "darwin":
        return "/Library/Application Support/Hackintoshify/config.ini"
    else: # linux
        return os.path.join(os.path.expanduser("~"), ".config", "hackintoshify", "config.ini")

def get_setup_details_path():
    if sys.platform == "win32":
        config_dir = os.path.join(os.getenv("ProgramData"), "Hackintoshify")
    elif sys.platform == "darwin":
        config_dir = "/Library/Application Support/Hackintoshify"
    else:  # Linux
        config_dir = os.path.join(os.path.expanduser("~"), ".config", "hackintoshify")
    return os.path.join(config_dir, "setup_details.json")

class SettingsScreen(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedWidth(650)
        self.setFixedHeight(700)
        self.config_path = get_config_path()
        self.setup_path = get_setup_details_path()
        self.config = configparser.ConfigParser()
        self.setup_details = {}
        self.current_theme = 'Dark'
        
        # Load config fully
        self.load_data()
        
        # Determine theme from config
        if 'Settings' in self.config:
            self.current_theme = self.config['Settings'].get('theme', 'Dark')
            
        self._build_ui()
        self.apply_theme(self.current_theme)

    def load_data(self):
        try:
            self.config.read(self.config_path)
        except Exception:
            pass 

        try:
            if os.path.exists(self.setup_path):
                with open(self.setup_path, 'r') as f:
                    self.setup_details = json.load(f)
        except Exception:
            self.setup_details = {}

    def _build_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # --- Header ---
        header = QFrame()
        header.setObjectName("header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(30, 25, 30, 25)
        
        title = QLabel("Settings")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header_layout.addWidget(title)
        self.main_layout.addWidget(header)

        # --- Scrollable Content ---
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setObjectName("scroll_area")
        
        content_frame = QFrame()
        content_frame.setObjectName("content")
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(30, 20, 30, 30)
        content_layout.setSpacing(25)
        
        scroll_area.setWidget(content_frame)
        self.main_layout.addWidget(scroll_area)

        # 1. Appearance Section
        self._add_section_header(content_layout, "Interface")
        
        theme_card = QFrame()
        theme_card.setObjectName("card")
        theme_layout = QHBoxLayout(theme_card)
        theme_layout.setContentsMargins(20, 15, 20, 15)
        
        theme_label = QLabel("Theme")
        theme_label.setFont(QFont("Segoe UI", 11))
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])
        self.theme_combo.setFixedWidth(160)
        self.theme_combo.setCursor(Qt.PointingHandCursor)
        self.theme_combo.currentTextChanged.connect(self.preview_theme)
        
        if 'Settings' in self.config:
            self.theme_combo.setCurrentText(self.config['Settings'].get('theme', 'Dark'))

        theme_layout.addWidget(theme_label)
        theme_layout.addStretch()
        theme_layout.addWidget(self.theme_combo)
        content_layout.addWidget(theme_card)

        # 2. Workspace Paths Section
        self._add_section_header(content_layout, "Paths & Environment")
        
        paths_card = QFrame()
        paths_card.setObjectName("card")
        paths_layout = QVBoxLayout(paths_card)
        paths_layout.setContentsMargins(20, 20, 20, 20)
        paths_layout.setSpacing(20)
        
        # Download Path
        self.download_path_input = self._add_path_row(paths_layout, "macOS Download Path", self.setup_details.get("download_path", ""))
        self.download_path_input.browse_btn.clicked.connect(lambda: self.browse_folder(self.download_path_input))

        # EFI Path
        self.efi_path_input = self._add_path_row(paths_layout, "EFI Builds Output", self.setup_details.get("efi_path", ""))
        self.efi_path_input.browse_btn.clicked.connect(lambda: self.browse_folder(self.efi_path_input))

        content_layout.addWidget(paths_card)



        # 4. System Section
        self._add_section_header(content_layout, "System")
        
        sys_card = QFrame()
        sys_card.setObjectName("card")
        sys_layout = QVBoxLayout(sys_card)
        sys_layout.setContentsMargins(20, 15, 20, 15)
        sys_layout.setSpacing(10)
        
        self.verbose_chk = QCheckBox("Enable Verbose Logging")
        self.verbose_chk.setCursor(Qt.PointingHandCursor)
        
        self.updates_chk = QCheckBox("Check for Updates on Startup")
        self.updates_chk.setCursor(Qt.PointingHandCursor)
        
        if 'Settings' in self.config:
            self.verbose_chk.setChecked(self.config['Settings'].getboolean('verbose_logging', False))
            self.updates_chk.setChecked(self.config['Settings'].getboolean('check_updates', True))
        
        sys_layout.addWidget(self.verbose_chk)
        sys_layout.addWidget(self.updates_chk)
        content_layout.addWidget(sys_card)
        
        content_layout.addStretch()

        # --- Footer ---
        footer = QFrame()
        footer.setObjectName("footer")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(30, 20, 30, 20)
        footer_layout.setSpacing(15)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("secondary_btn")
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)
        
        self.save_btn = QPushButton("Save Changes")
        self.save_btn.setObjectName("primary_btn")
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.clicked.connect(self.save_settings)
        
        footer_layout.addStretch()
        footer_layout.addWidget(self.cancel_btn)
        footer_layout.addWidget(self.save_btn)
        self.main_layout.addWidget(footer)

    def _add_section_header(self, layout, text):
        label = QLabel(text)
        label.setObjectName("section_header")
        layout.addWidget(label)

    def _add_path_row(self, layout, label_text, current_path):
        # Simplified: Label above, Input + Button below. No extra framing.
        container = QWidget() 
        row = QVBoxLayout(container)
        row.setContentsMargins(0,0,0,0)
        row.setSpacing(8)
        
        lbl = QLabel(label_text)
        lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
        lbl.setObjectName("field_label")
        
        input_row = QHBoxLayout()
        line_edit = QLineEdit(current_path)
        line_edit.setReadOnly(True)
        line_edit.setObjectName("path_input")
        line_edit.setFixedHeight(36)
        
        browse_btn = QPushButton("Change")
        browse_btn.setObjectName("browse_btn")
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.setFixedSize(80, 36)
        
        input_row.addWidget(line_edit)
        input_row.addWidget(browse_btn)
        
        row.addWidget(lbl)
        row.addLayout(input_row)
        layout.addWidget(container)
        
        line_edit.browse_btn = browse_btn
        return line_edit

    def browse_folder(self, line_edit):
        folder = QFileDialog.getExistingDirectory(self, "Select Directory", line_edit.text() or "")
        if folder:
            line_edit.setText(folder)

    def preview_theme(self, text):
        self.apply_theme(text)

    def save_settings(self):
        if not self.config.has_section('Settings'): self.config.add_section('Settings')
        theme = self.theme_combo.currentText()
        verbose = self.verbose_chk.isChecked()
        updates = self.updates_chk.isChecked()
        
        self.config.set('Settings', 'theme', theme)
        self.config.set('Settings', 'verbose_logging', str(verbose))
        self.config.set('Settings', 'check_updates', str(updates))
        
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as configfile:
                self.config.write(configfile)
            parent = self.parent()
            if parent and hasattr(parent, 'apply_theme'):
                parent.apply_theme(theme)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save config.ini:\n{e}")
            return

        new_details = {
            "download_path": self.download_path_input.text(),
            "efi_path": self.efi_path_input.text(),
            "setup_complete": True
        }
        self.setup_details.update(new_details)
        
        try:
            os.makedirs(os.path.dirname(self.setup_path), exist_ok=True)
            with open(self.setup_path, 'w') as f:
                json.dump(self.setup_details, f, indent=4)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save setup_details.json:\n{e}")
            return

        self.accept()

    def apply_theme(self, theme_name):
        is_dark = theme_name.lower().startswith('dark')
        bg = '#0f172a' if is_dark else '#f1f5f9'
        card_bg = '#1e293b' if is_dark else '#ffffff'
        text_primary = '#f1f5f9' if is_dark else '#0f172a'
        text_secondary = '#94a3b8' if is_dark else '#64748b'
        accent = '#38bdf8' if is_dark else '#0ea5e9'
        border = '#334155' if is_dark else '#e2e8f0'
        input_bg = '#020617' if is_dark else '#f1f5f9'
        
        # Checkbox SVG (Encoded # as %23)
        check_icon_url = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='4' stroke-linecap='round' stroke-linejoin='round'><polyline points='20 6 9 17 4 12'></polyline></svg>"
        
        # Dropdown Arrow (Accent colored)
        # Using %23 for '#' in accent color if it's hex
        accent_enc = accent.replace('#', '%23')
        arrow_icon_url = f"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='{accent_enc}' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><polyline points='6 9 12 15 18 9'></polyline></svg>"

        self.setStyleSheet(f"""
            QDialog {{ background-color: {bg}; color: {text_primary}; }}
            
            QFrame#header {{ background-color: {bg}; border-bottom: 1px solid {border}; }}
            QFrame#footer {{ background-color: {card_bg}; border-top: 1px solid {border}; }}
            
            QScrollArea {{ border: none; background-color: {bg}; }}
            QScrollArea > QWidget > QWidget {{ background-color: {bg}; }}
            
            QFrame#card {{
                background-color: {card_bg};
                border: 1px solid {border};
                border-radius: 12px;
            }}
            
            QLabel {{ color: {text_primary}; font-family: 'Segoe UI', sans-serif; background: transparent; }}
            QLabel#section_header {{
                color: {text_secondary}; font-weight: 700; font-size: 13px;
                text-transform: uppercase; letter-spacing: 1px; margin-top: 10px;
            }}
            QLabel#field_label {{ color: {text_primary}; font-size: 13px; font-weight: 600; }}
            
            QLineEdit {{
                background-color: {input_bg};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 0 12px;
                color: {text_primary}; 
                font-size: 13px;
            }}
            QLineEdit:focus {{ border: 1px solid {accent}; }}
            
            /* Enhanced Checkbox */
            QCheckBox {{
                color: {text_primary};
                font-size: 13px;
                spacing: 10px;
                background: transparent;
            }}
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border: 2px solid {border};
                border-radius: 6px;
                background: {input_bg};
            }}
            QCheckBox::indicator:hover {{ border-color: {accent}; }}
            QCheckBox::indicator:checked {{
                background-color: {accent};
                border-color: {accent};
                image: url("{check_icon_url}");
            }}

            QComboBox {{
                background-color: {input_bg};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 6px 12px;
                color: {text_primary};
            }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QComboBox::down-arrow {{ 
                image: url("{arrow_icon_url}");
                width: 12px; height: 12px;
            }}
            
            QPushButton#primary_btn {{
                background-color: {accent}; color: #0f172a; border: none; border-radius: 6px;
                padding: 10px 20px; font-weight: 600;
            }}
            QPushButton#primary_btn:hover {{ background-color: {QColor(accent).lighter(110).name()}; }}
            
            QPushButton#secondary_btn {{
                background-color: transparent; color: {text_secondary};
                border: 1px solid {border}; border-radius: 6px; padding: 10px 20px; font-weight: 600;
            }}
            QPushButton#secondary_btn:hover {{ color: {text_primary}; border-color: {text_primary}; }}
            
            QPushButton#browse_btn {{
                background-color: {card_bg}; color: {accent}; border: 1px solid {border};
                border-radius: 6px; font-weight: 600; font-size: 12px;
            }}
            QPushButton#browse_btn:hover {{ border-color: {accent}; background-color: {input_bg}; }}
        """)