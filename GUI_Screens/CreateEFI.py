from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QComboBox, QScrollArea, 
    QMessageBox, QLineEdit
)
from PySide6.QtGui import QFont, QIcon
from PySide6.QtCore import Qt, Signal

import os

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
        # --- Header ---
        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(70)
        h_layout = QHBoxLayout(header)
        title = QLabel("EFI Creator")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setObjectName("title")
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.clicked.connect(self.close)
        close_btn.setObjectName("close_btn")
        
        h_layout.addWidget(title)
        h_layout.addStretch()
        h_layout.addWidget(close_btn)
        self.layout.addWidget(header)
        
        # --- Content ---
        content = QWidget()
        c_layout = QVBoxLayout(content)
        c_layout.setContentsMargins(40, 40, 40, 40)
        c_layout.setSpacing(20)
        
        # Title
        l1 = QLabel("Configure Your EFI")
        l1.setFont(QFont("Segoe UI", 20, QFont.Bold))
        l1.setStyleSheet("background: transparent; border: none;")
        c_layout.addWidget(l1)
        
        # CPU Generation
        row1 = QHBoxLayout()
        lbl_cpu = QLabel("CPU Family:")
        lbl_cpu.setFont(QFont("Segoe UI", 11))
        lbl_cpu.setStyleSheet("background: transparent; border: none;")
        self.combo_cpu = QComboBox()
        self.combo_cpu.addItems([
            "Select CPU...",
            "Intel Desktop (Coffee Lake)",
            "Intel Desktop (Comet Lake)",
            "Intel Desktop (Kaby Lake)",
            "Intel Desktop (Skylake)",
            "Intel Desktop (Haswell)",
            "Intel Desktop (Ivy Bridge)",
            "Intel Desktop (Sandy Bridge)",
            "AMD Ryzen (Zen/Zen2/Zen3)",
            "Intel Laptop (Ice Lake)",
            "Intel Laptop (Coffee Lake Plus)",
            "Intel Laptop (Kaby Lake)",
        ])
        self.combo_cpu.setFixedHeight(40)
        
        row1.addWidget(lbl_cpu)
        row1.addWidget(self.combo_cpu, 1)
        c_layout.addLayout(row1)

        # Boot Mode (UEFI / Legacy)
        row2 = QHBoxLayout()
        lbl_boot = QLabel("Boot Mode:")
        lbl_boot.setFont(QFont("Segoe UI", 11))
        lbl_boot.setStyleSheet("background: transparent; border: none;")
        
        self.btn_uefi = QPushButton("UEFI (Modern)")
        self.btn_uefi.setCheckable(True)
        self.btn_uefi.setChecked(True)
        self.btn_uefi.setFixedSize(120, 40)
        self.btn_uefi.setCursor(Qt.PointingHandCursor)
        self.btn_uefi.clicked.connect(lambda: self.toggle_boot_mode("UEFI"))
        self.btn_uefi.setStyleSheet(self._get_btn_style(True))
        
        self.btn_legacy = QPushButton("Legacy BIOS")
        self.btn_legacy.setCheckable(True)
        self.btn_legacy.setFixedSize(120, 40)
        self.btn_legacy.setCursor(Qt.PointingHandCursor)
        self.btn_legacy.clicked.connect(lambda: self.toggle_boot_mode("Legacy"))
        self.btn_legacy.setStyleSheet(self._get_btn_style(False))
        
        row2.addWidget(lbl_boot)
        row2.addWidget(self.btn_uefi)
        row2.addWidget(self.btn_legacy)
        row2.addStretch()
        c_layout.addLayout(row2)
        
        # Placeholder for more options
        info = QLabel("This tool will generate a basic OpenCore EFI based on your hardware selection.\n(This is a placeholder for the EFI generation logic)")
        info.setWordWrap(True)
        info.setStyleSheet("color: #94a3b8; background: transparent; border: none;")
        c_layout.addWidget(info)
        
        c_layout.addStretch()
        
        # Generate Button
        self.btn_create = QPushButton("Generate EFI")
        self.btn_create.setFixedHeight(50)
        self.btn_create.setCursor(Qt.PointingHandCursor)
        self.btn_create.setObjectName("btn_primary")
        self.btn_create.clicked.connect(self.generate_efi)
        c_layout.addWidget(self.btn_create)
        
        self.layout.addWidget(content)

    def generate_efi(self):
        # Placeholder logic
        if self.combo_cpu.currentIndex() == 0:
            QMessageBox.warning(self, "Selection Required", "Please select your CPU family.")
            return

        # Simulate creation
        QMessageBox.information(self, "Success", "EFI Folder 'Generated' (Mock).")
        
        # In real app, we would create folder. For now, let's just return a dummy path or prompt user to save
        from PySide6.QtWidgets import QFileDialog
        path = QFileDialog.getExistingDirectory(self, "Select Output Folder for EFI")
        if path:
            final_path = os.path.join(path, "EFI")
            # Create dummy
            try:
                os.makedirs(final_path, exist_ok=True)
                os.makedirs(os.path.join(final_path, "OC"), exist_ok=True)
                os.makedirs(os.path.join(final_path, "BOOT"), exist_ok=True)
            except: pass
            
            self.efi_selected.emit(final_path)
            self.close()

    def toggle_boot_mode(self, mode):
        is_uefi = (mode == "UEFI")
        self.btn_uefi.setChecked(is_uefi)
        self.btn_legacy.setChecked(not is_uefi)
        self.btn_uefi.setStyleSheet(self._get_btn_style(is_uefi))
        self.btn_legacy.setStyleSheet(self._get_btn_style(not is_uefi))

    def _get_btn_style(self, active):
        # We need colors from theme, but for now hardcode or use simple logic
        # Ideally we pull from a theme dict
        accent = "#38bdf8"
        bg_active = "rgba(56, 189, 248, 0.2)"
        border_active = accent
        bg_inactive = "transparent"
        border_inactive = "#334155"
        
        if active:
            return f"background-color: {bg_active}; border: 1px solid {border_active}; color: {accent}; border-radius: 6px;"
        else:
            return f"background-color: {bg_inactive}; border: 1px solid {border_inactive}; color: #94a3b8; border-radius: 6px;"

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
