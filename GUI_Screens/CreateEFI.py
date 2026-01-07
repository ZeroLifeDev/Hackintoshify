from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QComboBox, QScrollArea, 
    QMessageBox, QListWidget, QListWidgetItem, QGroupBox, QFileDialog
)
from PySide6.QtGui import QFont, QIcon, QColor, QPainter
from PySide6.QtCore import Qt, Signal, QThread, QSize
from .Functionality.EFIBuilder import EFIBuilderWorker
from .Functionality.HardwareSniffer import HardwareSniffer

import os
import sys
import json
import datetime

class CreateEFIScreen(QWidget):
    efi_selected = Signal(str) # Emits path

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("EFI Hub")
        self.resize(900, 650)
        self.setWindowFlags(Qt.Window)
        
        self.scan_mode = False # False = List View, True = Creation Mode
        self.efi_dir = self._get_default_efi_path()
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self._build_ui()
        self.apply_theme("Dark")
        self._load_efi_list()

    def _get_default_efi_path(self):
        # Logic to get saved EFI path
        try:
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
                    return data.get("efi_path", "")
        except: pass
        return ""

    def _build_ui(self):
        # Header
        header = QFrame()
        header.setObjectName("header")
        header_layout = QHBoxLayout(header)
        
        self.lbl_title = QLabel("My EFI Builds")
        self.lbl_title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        
        btn_close = QPushButton("×")
        btn_close.setFixedSize(30, 30)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(self.close)
        btn_close.setObjectName("close_btn")
        
        header_layout.addWidget(self.lbl_title)
        header_layout.addStretch()
        header_layout.addWidget(btn_close)
        
        self.layout.addWidget(header)
        
        # --- List View Container ---
        self.list_container = QWidget()
        list_layout = QVBoxLayout(self.list_container)
        list_layout.setContentsMargins(30, 30, 30, 30)
        
        # Info bar
        self.lbl_path_info = QLabel(f"Looking in: {self.efi_dir}" if self.efi_dir else "No default EFI path set.")
        self.lbl_path_info.setStyleSheet("color: #94a3b8; font-style: italic;")
        list_layout.addWidget(self.lbl_path_info)
        
        # List Widget
        self.efi_list = QListWidget()
        self.efi_list.setStyleSheet("""
            QListWidget { background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; }
            QListWidget::item { padding: 10px; border-bottom: 1px solid #334155; }
            QListWidget::item:hover { background-color: #334155; }
        """)
        list_layout.addWidget(self.efi_list)
        
        # Buttons
        btn_row = QHBoxLayout()
        self.btn_new = QPushButton("Create New EFI")
        self.btn_new.setFixedHeight(45)
        self.btn_new.setObjectName("btn_primary")
        self.btn_new.setCursor(Qt.PointingHandCursor)
        self.btn_new.clicked.connect(self.switch_to_create_mode)
        
        btn_row.addStretch()
        btn_row.addWidget(self.btn_new)
        
        list_layout.addLayout(btn_row)
        self.layout.addWidget(self.list_container)
        
        # --- Creation View Container (Hidden initially) ---
        self.create_container = QWidget()
        self.create_container.setVisible(False)
        create_layout = QVBoxLayout(self.create_container)
        create_layout.setContentsMargins(30, 10, 30, 30)
        
        # Back Button
        btn_back = QPushButton("← Back to List")
        btn_back.setStyleSheet("border: none; color: #38bdf8; text-align: left; font-weight: bold;")
        btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.clicked.connect(self.switch_to_list_mode)
        create_layout.addWidget(btn_back)
        
        # Hardware Info Scroll Area (Expanded)
        self.hw_scroll = QScrollArea()
        self.hw_scroll.setWidgetResizable(True)
        self.hw_scroll.setStyleSheet("background: transparent; border: none;")
        
        hw_widget = QWidget()
        self.hw_layout = QVBoxLayout(hw_widget)
        self.hw_layout.setSpacing(15)
        
        self.hw_scroll.setWidget(hw_widget)
        create_layout.addWidget(self.hw_scroll)
        
        # Boot Mode
        row_boot = QHBoxLayout()
        row_boot.addWidget(QLabel("Boot Mode:"))
        self.btn_uefi = QPushButton("UEFI (Modern)")
        self.btn_uefi.setCheckable(True); self.btn_uefi.setChecked(True)
        self.btn_legacy = QPushButton("Legacy (BIOS)")
        self.btn_legacy.setCheckable(True)
        
        # Group logic
        self.btn_uefi.clicked.connect(lambda: self._set_boot(True))
        self.btn_legacy.clicked.connect(lambda: self._set_boot(False))
        
        row_boot.addWidget(self.btn_uefi)
        row_boot.addWidget(self.btn_legacy)
        row_boot.addStretch()
        create_layout.addLayout(row_boot)
        
        # Generate Button
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #fbbf24;")
        
        self.btn_generate = QPushButton("One-Click Build")
        self.btn_generate.setFixedHeight(50)
        self.btn_generate.setObjectName("btn_primary")
        self.btn_generate.clicked.connect(self.generate_efi)
        
        gen_row = QHBoxLayout()
        gen_row.addWidget(self.lbl_status)
        gen_row.addStretch()
        gen_row.addWidget(self.btn_generate)
        create_layout.addLayout(gen_row)
        
        self.layout.addWidget(self.create_container)

    def _load_efi_list(self):
        self.efi_list.clear()
        if not self.efi_dir or not os.path.exists(self.efi_dir):
            item = QListWidgetItem("No default directory accessible.")
            item.setFlags(Qt.NoItemFlags)
            self.efi_list.addItem(item)
            return

        # Scan for direct EFI folders or subfolders named 'EFI'
        # Let's assume user builds go into named folders, e.g. "MyBuild/EFI"
        # Or simple check:
        found_any = False
        try:
            for d in os.listdir(self.efi_dir):
                full_path = os.path.join(self.efi_dir, d)
                if os.path.isdir(full_path):
                    # Check if it has an OC folder inside EFI or is an EFI folder
                    is_efi_root = os.path.exists(os.path.join(full_path, "EFI", "OC"))
                    is_direct_efi = os.path.exists(os.path.join(full_path, "OC"))
                    
                    if is_efi_root or is_direct_efi:
                        found_any = True
                        self._add_efi_item(d, full_path)
        except: pass
        
        if not found_any:
            self.efi_list.addItem(QListWidgetItem("No EFI builds found in default path."))

    def _add_efi_item(self, name, path):
        item = QListWidgetItem()
        widget = QWidget()
        widget.setObjectName("efi_item_widget")
        
        h = QHBoxLayout(widget)
        h.setContentsMargins(20, 15, 20, 15)
        h.setSpacing(20)
        
        # Icon
        icon_lbl = QLabel("🍎")
        icon_lbl.setFont(QFont("Segoe UI Emoji", 28))
        
        # Text
        v = QVBoxLayout()
        v.setSpacing(4)
        v.setAlignment(Qt.AlignVCenter)
        
        lbl_name = QLabel(name)
        lbl_name.setFont(QFont("Segoe UI", 14, QFont.Bold))
        lbl_name.setStyleSheet("color: white;")
        
        # Meta
        ts = os.path.getmtime(path)
        date_str = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
        display_path = path.replace("\\", "/")
        lbl_meta = QLabel(f"{date_str} • {display_path}")
        lbl_meta.setStyleSheet("color: #94a3b8; font-size: 12px;")
        lbl_meta.setWordWrap(False)
        lbl_meta.setTextInteractionFlags(Qt.TextSelectableByMouse)
        
        v.addWidget(lbl_name)
        v.addWidget(lbl_meta)
        
        # Actions
        btn_config = QPushButton("Configure")
        btn_config.setFixedSize(110, 36)
        btn_config.setCursor(Qt.PointingHandCursor)
        btn_config.setStyleSheet("""
            QPushButton {
                background-color: transparent; border: 1px solid #475569; 
                color: #f1f5f9; border-radius: 6px; font-weight: 600;
            }
            QPushButton:hover { background-color: #334155; border-color: #94a3b8; }
        """)
        btn_config.clicked.connect(lambda: self.open_config(path))
        
        h.addWidget(icon_lbl)
        h.addLayout(v)
        h.addStretch()
        h.addWidget(btn_config)
        
        # Calculate size
        widget.adjustSize()
        # Enforce a comfortable height
        item.setSizeHint(QSize(widget.sizeHint().width(), 95))
        
        self.efi_list.addItem(item)
        self.efi_list.setItemWidget(item, widget)

    def switch_to_create_mode(self):
        self.list_container.setVisible(False)
        self.lbl_title.setText("New Build Scanner")
        self.create_container.setVisible(True)
        self.scan_mode = True
        
        # Trigger Scan
        self.scan_hardware()

    def switch_to_list_mode(self):
        self.create_container.setVisible(False)
        self.lbl_title.setText("My EFI Builds")
        self.list_container.setVisible(True)
        self.scan_mode = False
        self._load_efi_list()

    def scan_hardware(self):
        # Clear previous
        for i in range(self.hw_layout.count()):
            w = self.hw_layout.itemAt(i).widget()
            if w: w.deleteLater()

        lbl_loading = QLabel("Scanning components...")
        self.hw_layout.addWidget(lbl_loading)
        
        # Run scan
        self.sniffer = HardwareSniffer()
        self.hw_info = self.sniffer.detect()
        
        lbl_loading.deleteLater()
        
        # Populate UI with nice cards for each component
        self._add_hw_result("CPU", self.hw_info.get('cpu_model'), self.hw_info.get('cpu_family', 'Unknown'), "cpu")
        self._add_hw_result("GPU", self.hw_info.get('gpu_model'), self.hw_info.get('gpu_vendor'), "gpu")
        self._add_hw_result("Motherboard", f"{self.hw_info.get('mobo_vendor')} {self.hw_info.get('mobo_model')}", "", "mobo")
        
        net_str = f"Ethernet: {self.hw_info.get('ethernet_model', 'None')}\nWi-Fi: {self.hw_info.get('wifi_model', 'None')}"
        self._add_hw_result("Network", net_str, "", "network")

        bt_str = self.hw_info.get('bt_model', 'Not Detected')
        self._add_hw_result("Bluetooth", bt_str, "", "bluetooth")
        
        inp_str = f"Keyboard: {self.hw_info.get('keyboard_type')}\nMouse: {self.hw_info.get('mouse_type')}"
        self._add_hw_result("Input Devices", inp_str, "", "input")

        storage = self.hw_info.get('storage', [])
        stor_str = "\n".join(storage) if storage else "Unknown"
        self._add_hw_result("Storage", stor_str, "", "storage")

    def _add_hw_result(self, title, main_text, sub_text, icon_key):
        frame = QFrame()
        frame.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 8px;")
        f_layout = QHBoxLayout(frame)
        
        # Icon placeholder
        lbl_icon = QLabel("🖥️") # Dynamic later
        if icon_key == "cpu": lbl_icon.setText("🧠")
        if icon_key == "gpu": lbl_icon.setText("🎮")
        if icon_key == "network": lbl_icon.setText("🌐")
        if icon_key == "bluetooth": lbl_icon.setText("🦷")
        if icon_key == "storage": lbl_icon.setText("💾")
        if icon_key == "input": lbl_icon.setText("⌨️")
        
        lbl_icon.setFont(QFont("Segoe UI Emoji", 20))
        
        v = QVBoxLayout()
        t = QLabel(title)
        t.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold; text-transform: uppercase;")
        
        m = QLabel(str(main_text))
        m.setStyleSheet("color: white; font-weight: bold; font-size: 13px;")
        m.setWordWrap(True)
        
        v.addWidget(t)
        v.addWidget(m)
        if sub_text:
            s = QLabel(str(sub_text))
            s.setStyleSheet("color: #38bdf8; font-size: 11px;")
            v.addWidget(s)
            
        f_layout.addWidget(lbl_icon)
        f_layout.addLayout(v)
        f_layout.addStretch()
        
        self.hw_layout.addWidget(frame)

    def _set_boot(self, is_uefi):
        self.btn_uefi.setChecked(is_uefi)
        self.btn_legacy.setChecked(not is_uefi)
        self._style_toggles()

    def _style_toggles(self):
        # Helper to style the toggle buttons state
        # (Simplified, assume self.apply_theme handles basic colors)
        pass

    def generate_efi(self):
        # 1. Determine Path
        base_path = self.efi_dir
        if not base_path:
             # Ask
             path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
             if not path: return
             base_path = path

        # Create subfolder with timestamp or name
        folder_name = f"EFI_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        target_path = os.path.join(base_path, folder_name)
        os.makedirs(target_path, exist_ok=True)
        
        self.btn_generate.setEnabled(False)
        self.btn_generate.setText("Building...")
        
        cpu_family = self.hw_info.get('cpu_family', 'Unknown')
        is_uefi = self.btn_uefi.isChecked()
        
        self.worker = EFIBuilderWorker(target_path, cpu_family, is_uefi)
        self.worker.progress.connect(self.on_build_prog)
        self.worker.finished.connect(self.on_build_fin)
        self.worker.start()

    def on_build_prog(self, pct, msg):
        self.lbl_status.setText(msg)

    def on_build_fin(self, path):
        self.btn_generate.setEnabled(True)
        self.btn_generate.setText("One-Click Build")
        self.lbl_status.setText("Done!")
        
        res = QMessageBox.question(self, "Success", f"EFI Built!\nManage Kexts now?", QMessageBox.Yes | QMessageBox.No)
        if res == QMessageBox.Yes:
            self.open_config(path)
        else:
            self.switch_to_list_mode()

    def open_config(self, path):
        # Open EFIManager
        try:
            from .EFIManager import EFIManager
            # If path points to root folder, ensure we pass the folder containing 'EFI' or 'OC' properly
            # EFIManager expects the root containing "OC/config.plist" usually inside "EFI"
            # Adjust path if needed
            check_path = os.path.join(path, "EFI")
            if os.path.exists(check_path): 
                target = check_path
            else: 
                target = path
                
            self.mgr = EFIManager(target)
            self.mgr.show()
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open Config: {e}")

    def apply_theme(self, theme_name='Dark'):
        is_dark = theme_name.lower().startswith('dark')
        bg = "#0f172a" if is_dark else "#f8fafc"
        card = "#1e293b" if is_dark else "#ffffff"
        text = "#f1f5f9"
        accent = "#38bdf8"
        
        self.setStyleSheet(f"""
            QWidget {{ background-color: {bg}; color: {text}; font-family: 'Segoe UI'; }}
            QFrame#header {{ background-color: {bg}; border-bottom: 1px solid #334155; }}
            QPushButton#btn_primary {{ background-color: {accent}; color: white; border: none; border-radius: 6px; font-weight: bold; font-size: 14px; }}
            QPushButton#btn_secondary {{ background-color: transparent; border: 1px solid #475569; color: {text}; border-radius: 6px; }}
            QPushButton#close_btn {{ background: transparent; color: #94a3b8; font-size: 20px; border: none; }}
        """)
