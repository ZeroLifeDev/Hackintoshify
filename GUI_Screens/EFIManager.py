import os
import shutil
import plistlib
import requests
import zipfile
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, 
    QListWidgetItem, QPushButton, QFileDialog, QMessageBox, 
    QCheckBox, QFrame, QDialog, QProgressBar
)
from PySide6.QtGui import QFont, QIcon, QColor
from PySide6.QtCore import Qt, QThread, Signal, QSize

# --- Constants ---
KEXT_REPO = {
    "Lilu": {"url": "https://github.com/acidanthera/Lilu/releases/download/1.6.7/Lilu-1.6.7-RELEASE.zip", "desc": "Arbitrary kext patcher (Required)"},
    "VirtualSMC": {"url": "https://github.com/acidanthera/VirtualSMC/releases/download/1.3.2/VirtualSMC-1.3.2-RELEASE.zip", "desc": "SMC Emulator (Required)"},
    "WhateverGreen": {"url": "https://github.com/acidanthera/WhateverGreen/releases/download/1.6.6/WhateverGreen-1.6.6-RELEASE.zip", "desc": "Graphics Patching"},
    "AppleALC": {"url": "https://github.com/acidanthera/AppleALC/releases/download/1.8.7/AppleALC-1.8.7-RELEASE.zip", "desc": "Native Audio"},
    "VoodooPS2Controller": {"url": "https://github.com/acidanthera/VoodooPS2/releases/download/2.3.5/VoodooPS2Controller-2.3.5-RELEASE.zip", "desc": "PS/2 Inputs"},
    "IntelMausi": {"url": "https://github.com/acidanthera/IntelMausi/releases/download/1.0.7/IntelMausi-1.0.7-RELEASE.zip", "desc": "Intel Ethernet"},
    "RealtekRTL8111": {"url": "https://github.com/Mieze/RTL8111_driver_for_OS_X/releases/download/2.4.2/RealtekRTL8111-V2.4.2.zip", "desc": "Realtek Ethernet"},
    "USBToolBox": {"url": "https://github.com/USBToolBox/kext/releases/download/1.1.1/USBToolBox-1.1.1-RELEASE.zip", "desc": "USB Mapping Aid"},
    "NVMeFix": {"url": "https://github.com/acidanthera/NVMeFix/releases/download/1.1.1/NVMeFix-1.1.1-RELEASE.zip", "desc": "NVMe Power Managment"}
}

# --- Workers ---
class KextDownloader(QThread):
    progress = Signal(int)
    finished = Signal(str)
    error = Signal(str)
    
    def __init__(self, url, name, temp_dir):
        super().__init__()
        self.url = url
        self.name = name
        self.temp_dir = temp_dir
        
    def run(self):
        try:
            zip_path = os.path.join(self.temp_dir, f"{self.name}.zip")
            response = requests.get(self.url, stream=True, timeout=60)
            response.raise_for_status()
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            extract_path = os.path.join(self.temp_dir, f"ext_{self.name}")
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(extract_path)
            
            found_kext = None
            for root, dirs, files in os.walk(extract_path):
                for d in dirs:
                    if d.endswith(".kext") and not d.startswith("._"):
                        found_kext = os.path.join(root, d)
                        break
                if found_kext: break
            
            if found_kext: self.finished.emit(found_kext)
            else: self.error.emit(f"No .kext found in {self.name}")
        except Exception as e:
            self.error.emit(str(e))

# --- Dialogs ---
class RepoDialog(QDialog):
    kext_downloaded = Signal(str)

    def __init__(self, temp_dir, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kext Store")
        self.resize(700, 500)
        self.temp_dir = temp_dir
        self.workers = [] # Keep references to prevent GC
        
        self.setStyleSheet("""
            QDialog { background-color: #0f172a; color: white; font-family: 'Segoe UI'; }
            QListWidget { background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; outline: none; }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #334155; }
            QProgressBar { height: 6px; background: #334155; border-radius: 3px; border: none; }
            QProgressBar::chunk { background: #38bdf8; border-radius: 3px; }
        """)
        
        layout = QVBoxLayout(self)
        
        lbl = QLabel("Download Essential Kexts")
        lbl.setFont(QFont("Segoe UI", 16, QFont.Bold))
        layout.addWidget(lbl)
        
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)
        
        self._populate()
        
    def _populate(self):
        for name, data in KEXT_REPO.items():
            item = QListWidgetItem()
            w = QWidget()
            h = QHBoxLayout(w)
            h.setContentsMargins(5, 5, 5, 5)
            
            # Left: Info
            v = QVBoxLayout()
            n = QLabel(name)
            n.setStyleSheet("font-weight: bold; font-size: 14px;")
            d = QLabel(data['desc'])
            d.setStyleSheet("color: #94a3b8; font-size: 12px;")
            v.addWidget(n); v.addWidget(d)
            
            # Right: Action Stack (Button + Progress)
            action_stack = QVBoxLayout()
            action_stack.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            btn = QPushButton("Download")
            btn.setFixedSize(90, 30)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton { background-color: #38bdf8; border: none; border-radius: 4px; font-weight: bold; color: #020617; }
                QPushButton:hover { background-color: #0ea5e9; }
                QPushButton:disabled { background-color: #475569; color: #94a3b8; }
            """)
            
            bar = QProgressBar()
            bar.setFixedSize(90, 6)
            bar.setVisible(False)
            
            action_stack.addWidget(btn)
            action_stack.addWidget(bar)
            
            # Button Logic
            # We need to capture variables correctly in lambda
            btn.clicked.connect(lambda _, n=name, u=data['url'], b=btn, p=bar: self._start_download(n, u, b, p))
            
            h.addLayout(v)
            h.addLayout(action_stack)
            
            item.setSizeHint(QSize(w.sizeHint().width(), 70))
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, w)

    def _start_download(self, name, url, btn, bar):
        btn.setEnabled(False)
        btn.setText("Queued...")
        bar.setVisible(True)
        bar.setValue(0)
        
        worker = KextDownloader(url, name, self.temp_dir)
        worker.progress.connect(bar.setValue)
        
        # Success Closure
        def on_done(path):
            bar.setValue(100)
            btn.setText("Installed")
            btn.setStyleSheet("background-color: #22c55e; color: white;")
            worker.wait() # Cleanup thread
            if worker in self.workers: self.workers.remove(worker)
            self.kext_downloaded.emit(path)

        # Error Closure
        def on_fail(err):
            btn.setEnabled(True)
            btn.setText("Retry")
            bar.setVisible(False)
            QMessageBox.critical(self, "Download Error", f"Failed to download {name}:\n{err}")
            if worker in self.workers: self.workers.remove(worker)

        worker.finished.connect(on_done)
        worker.error.connect(on_fail)
        
        self.workers.append(worker)
        worker.start()

# --- Main Manager ---
class EFIManager(QWidget):
    def __init__(self, efi_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kext Manager")
        self.resize(1100, 700)
        
        # Paths
        self.efi_path = efi_path
        self.config_path = os.path.join(efi_path, "OC", "config.plist")
        self.kexts_dir = os.path.join(efi_path, "OC", "Kexts")
        self.temp_dir = os.path.join(efi_path, "temp_kexts")
        if not os.path.exists(self.temp_dir): os.makedirs(self.temp_dir)
        
        self.plist_data = None
        self.current_kext_idx = -1
        
        self._build_ui()
        self.apply_theme("Dark")
        
        # Initial Load
        if os.path.exists(self.config_path):
            self.load_data()
        else:
            QMessageBox.critical(self, "Config Missing", f"Could not find config.plist at:\n{self.config_path}")

    def _build_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # --- Left Sidebar (List) ---
        sidebar = QFrame()
        sidebar.setFixedWidth(320)
        sidebar.setStyleSheet("background-color: #0f172a; border-right: 1px solid #334155;")
        sb_layout = QVBoxLayout(sidebar)
        
        sb_header = QLabel("Installed Kexts")
        sb_header.setFont(QFont("Segoe UI", 14, QFont.Bold))
        sb_header.setStyleSheet("color: white; padding: 10px;")
        sb_layout.addWidget(sb_header)
        
        self.kext_list = QListWidget()
        self.kext_list.setStyleSheet("""
            QListWidget { background-color: transparent; border: none; }
            QListWidget::item { padding: 12px; border-bottom: 1px solid #1e293b; color: #cbd5e1; }
            QListWidget::item:selected { background-color: #1e293b; color: #38bdf8; border-left: 3px solid #38bdf8; }
        """)
        self.kext_list.currentRowChanged.connect(self._on_selection_change)
        sb_layout.addWidget(self.kext_list)
        
        # Action Buttons
        btn_box = QHBoxLayout()
        self.btn_store = QPushButton("+ Kext Store")
        self.btn_store.setStyleSheet("background-color: #38bdf8; color: #020617; border: none; padding: 12px; border-radius: 6px; font-weight: bold;")
        self.btn_store.setCursor(Qt.PointingHandCursor)
        self.btn_store.clicked.connect(self.open_store)
        
        btn_box.addWidget(self.btn_store)
        sb_layout.addLayout(btn_box)
        
        # --- Right Panel (Simplified Details) ---
        self.details_panel = QWidget()
        self.details_panel.setStyleSheet("background-color: #020617;")
        d_layout = QVBoxLayout(self.details_panel)
        d_layout.setContentsMargins(50, 50, 50, 50)
        
        # Info Header
        self.lbl_selected_title = QLabel("Select a Kext")
        self.lbl_selected_title.setFont(QFont("Segoe UI", 28, QFont.Bold))
        self.lbl_selected_title.setStyleSheet("color: white;")
        d_layout.addWidget(self.lbl_selected_title)
        
        self.lbl_status = QLabel("")
        self.lbl_status.setFont(QFont("Segoe UI", 12))
        d_layout.addWidget(self.lbl_status)
        
        d_layout.addSpacing(30)
        
        # Simple Toggle
        self.toggle_container = QFrame()
        self.toggle_container.setStyleSheet("background-color: #1e293b; border-radius: 12px; padding: 20px;")
        t_layout = QHBoxLayout(self.toggle_container)
        
        lbl_en = QLabel("Enable this Kext")
        lbl_en.setStyleSheet("color: white; font-size: 16px; font-weight: bold; border: none;")
        
        self.chk_enabled = QCheckBox()
        self.chk_enabled.setStyleSheet("QCheckBox::indicator { width: 24px; height: 24px; border-radius: 4px; }")
        self.chk_enabled.toggled.connect(self.save_state) # Auto-save on toggle

        t_layout.addWidget(lbl_en)
        t_layout.addStretch()
        t_layout.addWidget(self.chk_enabled)
        
        d_layout.addWidget(self.toggle_container)
        d_layout.addStretch()
        
        # Delete Button (Bottom Right)
        btn_del = QPushButton("Remove Kext")
        btn_del.setFixedSize(140, 45)
        btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.setStyleSheet("""
            QPushButton { background-color: transparent; border: 2px solid #dc2626; color: #dc2626; font-weight: bold; border-radius: 8px; }
            QPushButton:hover { background-color: #dc2626; color: white; }
        """)
        btn_del.clicked.connect(self.delete_current)
        
        del_row = QHBoxLayout()
        del_row.addStretch()
        del_row.addWidget(btn_del)
        
        self.editor_actions = QWidget()
        self.editor_actions.setLayout(del_row)
        d_layout.addWidget(self.editor_actions)
        
        # Init Visibility
        self.toggle_editor(False)
        
        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.details_panel)

    def toggle_editor(self, visible):
        self.toggle_container.setVisible(visible)
        self.editor_actions.setVisible(visible)
        if not visible:
            self.lbl_selected_title.setText("Select a Kext")
            self.lbl_status.setText("Manage your installed drivers here.")
        
    def load_data(self):
        self.kext_list.clear()
        try:
            with open(self.config_path, 'rb') as f:
                self.plist_data = plistlib.load(f)
            
            # --- AUTO-SYNC LOGIC ---
            # 1. Get all actual files
            if not os.path.exists(self.kexts_dir): os.makedirs(self.kexts_dir)
            actual_files = [f for f in os.listdir(self.kexts_dir) if f.endswith(".kext") and not f.startswith("._")]
            
            # 2. Get all config entries
            kernel_add = self.plist_data.get('Kernel', {}).get('Add', [])
            config_bundles = [e.get('BundlePath') for e in kernel_add]
            
            # 3. If file exists but not in config, add it (SYNC)
            unsynced = [f for f in actual_files if f not in config_bundles]
            if unsynced:
                for f in unsynced:
                    self._add_to_plist(f, save=False) # Batch add
                self._write_plist() # Save once
                # Reload data to reflect changes
                with open(self.config_path, 'rb') as f:
                    self.plist_data = plistlib.load(f)
            # -----------------------

            kexts = self.plist_data.get('Kernel', {}).get('Add', [])
            for k in kexts:
                path = k.get('BundlePath', 'Unknown')
                enabled = k.get('Enabled', False)
                
                # Check file existence
                full = os.path.join(self.kexts_dir, path)
                exists = os.path.exists(full)
                
                icon = "🟢" if (enabled and exists) else "⚪"
                if not exists: icon = "❌" # Alert user
                
                item = QListWidgetItem(f"{icon}  {path}")
                self.kext_list.addItem(item)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to parse plist: {e}")

    def _on_selection_change(self, row):
        if row < 0: 
            self.toggle_editor(False)
            return
            
        self.toggle_editor(True)
        self.current_kext_idx = row
        
        kext_entry = self.plist_data['Kernel']['Add'][row]
        bundle = kext_entry.get('BundlePath', 'Unknown')
        
        self.lbl_selected_title.setText(bundle)
        
        # Check if file exists
        full = os.path.join(self.kexts_dir, bundle)
        if os.path.exists(full):
            self.lbl_status.setText("✅  Installed and Ready")
            self.lbl_status.setStyleSheet("color: #4ade80;")
        else:
            self.lbl_status.setText("❌  File Missing from Disk")
            self.lbl_status.setStyleSheet("color: #ef4444;")
            
        # Block signals to prevent auto-save trigger
        self.chk_enabled.blockSignals(True)
        self.chk_enabled.setChecked(kext_entry.get('Enabled', False))
        self.chk_enabled.blockSignals(False)

    def save_state(self):
        if self.current_kext_idx < 0: return
        
        entry = self.plist_data['Kernel']['Add'][self.current_kext_idx]
        entry['Enabled'] = self.chk_enabled.isChecked()
        self._write_plist()
        
        # Refresh list icon
        self.load_data()
        self.kext_list.setCurrentRow(self.current_kext_idx)

    def delete_current(self):
        if self.current_kext_idx < 0: return
        
        confirm = QMessageBox.question(self, "Remove", "Uninstall this Kext completely?", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.No: return
        
        entry = self.plist_data['Kernel']['Add'][self.current_kext_idx]
        path = entry.get('BundlePath')
        
        # Delete from disk
        full_path = os.path.join(self.kexts_dir, path)
        if os.path.exists(full_path):
            try: shutil.rmtree(full_path)
            except: pass
            
        # Remove from plist
        del self.plist_data['Kernel']['Add'][self.current_kext_idx]
        self._write_plist()
        
        self.toggle_editor(False)
        self.load_data()

    def _write_plist(self):
        with open(self.config_path, 'wb') as f:
            plistlib.dump(self.plist_data, f)

    def open_store(self):
        dlg = RepoDialog(self.temp_dir, self)
        dlg.kext_downloaded.connect(self.install_new_kext)
        dlg.exec()

    def install_new_kext(self, source_path):
        name = os.path.basename(source_path)
        dest = os.path.join(self.kexts_dir, name)
        
        if os.path.isdir(source_path):
            if os.path.exists(dest): shutil.rmtree(dest)
            shutil.copytree(source_path, dest)
        
        self._add_to_plist(name)
        self.load_data()

    def _add_to_plist(self, name, save=True):
        # Scan for duplicate
        for x in self.plist_data['Kernel']['Add']:
            if x['BundlePath'] == name: return

        # Check binary
        exe = ""
        binary_check = os.path.join(self.kexts_dir, name, "Contents", "MacOS", name[:-5])
        if os.path.exists(binary_check):
            exe = f"Contents/MacOS/{name[:-5]}"
            
        new_entry = {
            'Arch': 'x86_64',
            'BundlePath': name,
            'Comment': '',
            'Enabled': True,
            'ExecutablePath': exe,
            'MaxKernel': '',
            'MinKernel': '',
            'PlistPath': 'Contents/Info.plist'
        }
        self.plist_data['Kernel']['Add'].append(new_entry)
        if save: self._write_plist()

    def apply_theme(self, t):
        self.setStyleSheet("font-family: 'Segoe UI'; color: #f1f5f9; background-color: #020617;")
