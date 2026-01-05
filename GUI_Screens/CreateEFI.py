from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QComboBox, QScrollArea, 
    QMessageBox, QLineEdit, QGroupBox, QFileDialog
)
from PySide6.QtGui import QFont, QIcon
from PySide6.QtCore import Qt, Signal, QThread
from .Functionality.EFIBuilder import EFIBuilderWorker
from .Functionality.HardwareSniffer import HardwareSniffer

import os
import sys

class CreateEFIScreen(QWidget):
    efi_selected = Signal(str) # Emits path to the created/selected EFI

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create EFI Folder")
        self.resize(800, 600)
        self.setWindowFlags(Qt.Window)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self._build_ui()
        self.apply_theme("Dark")

    def _build_ui(self):
        # Header
        header = QFrame()
        header.setStyleSheet("background-color: #1e293b; border-bottom: 1px solid #334155;")
        header_layout = QHBoxLayout(header)

        lbl_title = QLabel("Create EFI Folder")
        lbl_title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        lbl_title.setStyleSheet("color: white;")

        btn_close = QPushButton("×")
        btn_close.setFixedSize(30, 30)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(self.close)
        btn_close.setStyleSheet("background: transparent; color: #94a3b8; font-size: 20px; border: none;")

        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        header_layout.addWidget(btn_close)

        self.layout.addWidget(header)

        # Content
        content = QFrame()
        c_layout = QVBoxLayout(content)
        c_layout.setSpacing(20)
        c_layout.setContentsMargins(30, 30, 30, 30)

        # Hardware Info Section (Display Only)
        info_group = QGroupBox("Detected Hardware")
        info_group.setStyleSheet("""
            QGroupBox {
                color: #e2e8f0; font-weight: bold; border: 1px solid #334155;
                border-radius: 8px; margin-top: 10px; padding-top: 15px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        """)
        ig_layout = QVBoxLayout(info_group)

        self.lbl_hw_info = QLabel("Initializing hardware scan...")
        self.lbl_hw_info.setStyleSheet("color: #94a3b8; font-family: Consolas;")
        self.lbl_hw_info.setWordWrap(True)
        ig_layout.addWidget(self.lbl_hw_info)

        c_layout.addWidget(info_group)


        # Boot Mode (UEFI / Legacy)
        row2 = QHBoxLayout()
        lbl_boot = QLabel("Boot Mode:")
        lbl_boot.setStyleSheet("color: #e2e8f0; font-weight: bold;")

        self.btn_uefi = QPushButton("UEFI (Modern)")
        self.btn_uefi.setCheckable(True)
        self.btn_uefi.setChecked(True)
        self.btn_uefi.setCursor(Qt.PointingHandCursor)
        self.btn_uefi.clicked.connect(lambda: self._toggle_boot_mode(True))

        self.btn_legacy = QPushButton("Legacy (BIOS)")
        self.btn_legacy.setCheckable(True)
        self.btn_legacy.setCursor(Qt.PointingHandCursor)
        self.btn_legacy.clicked.connect(lambda: self._toggle_boot_mode(False))

        self._set_btn_style(self.btn_uefi, active=True)
        self._set_btn_style(self.btn_legacy, active=False)

        row2.addWidget(lbl_boot)
        row2.addWidget(self.btn_uefi)
        row2.addWidget(self.btn_legacy)
        row2.addStretch()
        c_layout.addLayout(row2)

        c_layout.addStretch()

        # Action Buttons
        row_btns = QHBoxLayout()

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #fbbf24;")

        self.btn_create = QPushButton("Generate EFI")
        self.btn_create.setFixedSize(180, 50)
        self.btn_create.setCursor(Qt.PointingHandCursor)
        self.btn_create.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6; color: white; border-radius: 8px; font-weight: bold; font-size: 14px;
            }
            QPushButton:hover { background-color: #2563eb; }
            QPushButton:disabled { background-color: #475569; color: #94a3b8; }
        """)
        self.btn_create.clicked.connect(self.generate_efi)

        row_btns.addWidget(self.lbl_status)
        row_btns.addStretch()
        row_btns.addWidget(self.btn_create)

        c_layout.addLayout(row_btns)
        self.layout.addWidget(content)

        # Trigger Scan immediately
        QThread.currentThread().msleep(100)
        self.scan_hardware()

    def generate_efi(self):
        # Use detected info
        cpu_family = self.hw_info.get('cpu_family', 'Unknown')
        
        if cpu_family == 'Unknown':
            QMessageBox.warning(self, "Detection Failed", "Could not automatically identify CPU generation.\nEFI generation may use generic defaults.")
        
        # Check for default path in settings (Setup Details or Config)
        path = ""
        try:
            # 1. Try Setup Details JSON
            import json
            if sys.platform == "win32":
                config_dir = os.path.join(os.getenv("ProgramData"), "Hackintoshify")
            elif sys.platform == "darwin":
                config_dir = "/Library/Application Support/Hackintoshify"
            else:
                config_dir = os.path.join(os.path.expanduser("~"), ".config", "hackintoshify")
            
            setup_path = os.path.join(config_dir, "setup_details.json")
            if os.path.exists(setup_path):
                with open(setup_path, 'r') as f:
                    data = json.load(f)
                    path = data.get("efi_path", "")
            
            # 2. Fallback to Config.ini if JSON empty
            if not path and self.parent() and hasattr(self.parent(), 'config'):
                path = self.parent().config['Settings'].get('efi_path', '')
        except: pass

        if not path or not os.path.exists(path):
            # Fallback to dialog
            path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        
        if not path: return

        # Lock UI
        self.btn_create.setEnabled(False)
        self.btn_create.setText("Building EFI...")
        self.lbl_status.setText("Initializing...")
        
        is_uefi = self.btn_uefi.isChecked()
        
        self.worker = EFIBuilderWorker(path, cpu_family, is_uefi)
        self.worker.progress.connect(self.on_build_progress)
        self.worker.finished.connect(self.on_build_finished)
        self.worker.error.connect(self.on_build_error)
        self.worker.start()

    def on_build_progress(self, pct, msg):
        self.lbl_status.setText(f"{msg} ({pct}%)")

    def on_build_finished(self, efi_path):
        self.btn_create.setEnabled(True)
        self.btn_create.setText("Generate EFI")
        self.lbl_status.setText("Success!")

        res = QMessageBox.question(self, "Success", f"EFI Folder Created Successfully at:\n{efi_path}\n\nDo you want to manage Kexts (config.plist) now?", QMessageBox.Yes | QMessageBox.No)
        
        self.efi_selected.emit(efi_path)
        
        if res == QMessageBox.Yes:
            # Open Kext Manager
            try:
                from .EFIManager import EFIManager
                self.mgr = EFIManager(efi_path)
                self.mgr.show()
                self.close() # Close creator
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open Kext Manager: {e}")
        else:
            self.close()

    def scan_hardware(self):
        self.lbl_hw_info.setText("Scanning system hardware...")
        self.sniffer = HardwareSniffer()
        self.hw_info = self.sniffer.detect()

        info_text = f"""CPU: {self.hw_info.get('cpu_model', 'Unknown')}
Family: {self.hw_info.get('cpu_family', 'Unknown')}
GPU: {self.hw_info.get('gpu_model', 'Unknown')}
Motherboard: {self.hw_info.get('mobo_vendor', '')} {self.hw_info.get('mobo_model', '')}
Ethernet: {self.hw_info.get('ethernet', 'Unknown')}"""

        self.lbl_hw_info.setText(info_text)

    def on_build_error(self, err):
        self.btn_create.setEnabled(True)
        self.btn_create.setText("Generate EFI")
        self.lbl_status.setText("Error!")
        QMessageBox.critical(self, "Build Error", f"Failed to build EFI:\n{err}")

    def _toggle_boot_mode(self, is_uefi):
        self.btn_uefi.setChecked(is_uefi)
        self.btn_legacy.setChecked(not is_uefi)
        self._set_btn_style(self.btn_uefi, is_uefi)
        self._set_btn_style(self.btn_legacy, not is_uefi)

    def _set_btn_style(self, btn, active):
        # We need colors from theme, but for now hardcode or use simple logic
        accent = "#38bdf8"
        bg_active = "rgba(56, 189, 248, 0.2)"
        border_active = accent
        bg_inactive = "transparent"
        border_inactive = "#334155"
        
        style = ""
        if active:
            style = f"background-color: {bg_active}; border: 1px solid {border_active}; color: {accent}; border-radius: 6px; font-weight: bold;"
        else:
            style = f"background-color: {bg_inactive}; border: 1px solid {border_inactive}; color: #94a3b8; border-radius: 6px;"
        
        btn.setStyleSheet(style)

    def apply_theme(self, theme_name='Dark'):
        is_dark = theme_name.lower().startswith('dark')
        bg_color = "#0f172a" if is_dark else "#f8fafc"
        card_bg = "#1e293b" if is_dark else "#ffffff"
        text_p = "#f1f5f9" if is_dark else "#0f172a"
        border = "#334155" if is_dark else "#cbd5e1"
        accent = "#38bdf8" if is_dark else "#0284c7"
        
        self.setStyleSheet(f"""
            QWidget {{ background-color: {bg_color}; font-family: 'Segoe UI'; color: {text_p}; }}
            QFrame#header {{ background-color: {bg_color}; border-bottom: 1px solid {border}; }}
            QComboBox {{ background-color: {card_bg}; border: 1px solid {border}; padding: 5px; color: {text_p}; }}
            QPushButton#btn_primary {{ background-color: {accent}; color: white; border-radius: 6px; font-weight: bold; font-size: 14px; }}
            QPushButton#close_btn {{ background: transparent; border: none; color: {text_p}; font-size: 16px; }}
        """)
