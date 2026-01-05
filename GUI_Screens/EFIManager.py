import os
import shutil
import plistlib
import requests
import zipfile
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, 
    QListWidgetItem, QPushButton, QFileDialog, QMessageBox, 
    QCheckBox, QFrame, QGroupBox, QSplitter, QProgressBar
)
from PySide6.QtGui import QFont, QIcon, QColor
from PySide6.QtCore import Qt, QThread, Signal

# Common Kexts Catalogue
KEXT_REPO = {
    "Lilu": {
        "url": "https://github.com/acidanthera/Lilu/releases/download/1.6.7/Lilu-1.6.7-RELEASE.zip",
        "desc": "Required for all Hackintoshes. Arbitrary kext patcher."
    },
    "VirtualSMC": {
        "url": "https://github.com/acidanthera/VirtualSMC/releases/download/1.3.2/VirtualSMC-1.3.2-RELEASE.zip",
        "desc": "Emulates the SMC chip. Required."
    },
    "WhateverGreen": {
        "url": "https://github.com/acidanthera/WhateverGreen/releases/download/1.6.6/WhateverGreen-1.6.6-RELEASE.zip",
        "desc": "Graphics patching for Intel/AMD/NVIDIA."
    },
    "AppleALC": {
        "url": "https://github.com/acidanthera/AppleALC/releases/download/1.8.7/AppleALC-1.8.7-RELEASE.zip",
        "desc": "Native macOS audio for non-Apple codecs."
    },
    "IntelMausi": {
        "url": "https://github.com/acidanthera/IntelMausi/releases/download/1.0.7/IntelMausi-1.0.7-RELEASE.zip",
        "desc": "Intel Ethernet LAN driver."
    },
    "RealtekRTL8111": {
        "url": "https://github.com/Mieze/RTL8111_driver_for_OS_X/releases/download/2.4.2/RealtekRTL8111-V2.4.2.zip",
        "desc": "Realtek Ethernet LAN driver."
    },
    "VoodooPS2Controller": {
        "url": "https://github.com/acidanthera/VoodooPS2/releases/download/2.3.5/VoodooPS2Controller-2.3.5-RELEASE.zip",
        "desc": "PS/2 keyboard/mouse/trackpad support."
    },
    "USBToolBox": {
        "url": "https://github.com/USBToolBox/kext/releases/download/1.1.1/USBToolBox-1.1.1-RELEASE.zip",
        "desc": "USB mapping helper (requires UTBMap)."
    },
    "NVMeFix": {
        "url": "https://github.com/acidanthera/NVMeFix/releases/download/1.1.1/NVMeFix-1.1.1-RELEASE.zip",
        "desc": "Fixes power management for non-Apple NVMe SSDs."
    }
}

class KextDownloader(QThread):
    progress = Signal(int)
    finished = Signal(str) # Path to extracted kext
    error = Signal(str)
    
    def __init__(self, url, name, temp_dir):
        super().__init__()
        self.url = url
        self.name = name
        self.temp_dir = temp_dir
        
    def run(self):
        try:
            # 1. Download
            zip_path = os.path.join(self.temp_dir, f"{self.name}.zip")
            response = requests.get(self.url, stream=True, timeout=60)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    downloaded += len(chunk)
                    f.write(chunk)
                    if total_size > 0:
                        self.progress.emit(int((downloaded / total_size) * 50))
                        
            # 2. Extract
            extract_path = os.path.join(self.temp_dir, f"ext_{self.name}")
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(extract_path)
            
            self.progress.emit(80)
            
            # 3. Find .kext
            found_kext = None
            for root, dirs, files in os.walk(extract_path):
                for d in dirs:
                    if d.endswith(".kext") and not d.startswith("._"):
                        found_kext = os.path.join(root, d)
                        break
                if found_kext: break
                
            if found_kext:
                self.progress.emit(100)
                self.finished.emit(found_kext)
            else:
                self.error.emit(f"No .kext found in {self.name} zip archive.")
                
        except Exception as e:
            self.error.emit(str(e))

class EFIManager(QWidget):
    def __init__(self, efi_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("EFI Kext Manager")
        self.resize(900, 600)
        self.setWindowFlags(Qt.Window)
        
        self.efi_path = efi_path
        self.config_path = os.path.join(efi_path, "OC", "config.plist")
        self.kexts_dir = os.path.join(efi_path, "OC", "Kexts")
        self.temp_dir = os.path.join(efi_path, "temp_kexts")
        if not os.path.exists(self.temp_dir): os.makedirs(self.temp_dir)
        
        self.plist_data = None
        self.worker = None
        
        self._build_ui()
        self.load_efi()
        self.apply_theme("Dark")

    def closeEvent(self, event):
        try:
            shutil.rmtree(self.temp_dir)
        except: pass
        super().closeEvent(event)

    def _build_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        header = QFrame()
        header.setStyleSheet("background-color: #1e293b; border-bottom: 1px solid #334155;")
        header_layout = QHBoxLayout(header)
        
        title = QLabel("Kext Manager")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: white;")
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        self.layout.addWidget(header)
        
        # Splitter for Left (Installed) and Right (Repo)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background-color: #334155; }")
        
        # --- LEFT PANEL: Installed Kexts ---
        left_panel = QFrame()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(15, 15, 15, 15)
        
        left_layout.addWidget(QLabel("Installed Kexts"))
        
        self.list_kexts = QListWidget()
        self.list_kexts.setStyleSheet("""
            QListWidget {
                background-color: #0f172a; border: 1px solid #334155; border-radius: 6px; color: #e2e8f0; font-size: 14px;
            }
            QListWidget::item { padding: 8px; }
            QListWidget::item:selected { background-color: #334155; }
        """)
        left_layout.addWidget(self.list_kexts)
        
        # Start of button row
        l_btn_row = QHBoxLayout()
        
        self.btn_add_local = QPushButton("Add Local Kext...")
        self.btn_add_local.clicked.connect(self.add_local_kext)
        self._style_btn(self.btn_add_local)
        
        self.btn_remove = QPushButton("Remove")
        self.btn_remove.clicked.connect(self.remove_kext)
        self._style_btn(self.btn_remove, danger=True)
        
        l_btn_row.addWidget(self.btn_add_local)
        l_btn_row.addWidget(self.btn_remove)
        left_layout.addLayout(l_btn_row)
        
        splitter.addWidget(left_panel)
        
        # --- RIGHT PANEL: Kext Repository ---
        right_panel = QFrame()
        # Slightly lighter background for "Store" feel?
        right_panel.setStyleSheet("background-color: #1a202c;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(15, 15, 15, 15)
        
        right_layout.addWidget(QLabel("Available Kexts (Online Repo)"))
        
        self.list_repo = QListWidget()
        self.list_repo.setStyleSheet("""
            QListWidget {
                background-color: #1a202c; border: 1px solid #334155; border-radius: 6px; color: #e2e8f0;
            }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #2d3748; }
            QListWidget::item:hover { background-color: #2d3748; }
        """)
        self._populate_repo()
        right_layout.addWidget(self.list_repo)
        
        self.lbl_repo_status = QLabel("")
        self.lbl_repo_status.setStyleSheet("color: #38bdf8; font-style: italic;")
        right_layout.addWidget(self.lbl_repo_status)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar { height: 6px; border-radius: 3px; background: #334155; } QProgressBar::chunk { background: #38bdf8; border-radius: 3px; }")
        right_layout.addWidget(self.progress_bar)

        splitter.addWidget(right_panel)
        splitter.setSizes([400, 500])
        
        self.layout.addWidget(splitter)

    def _populate_repo(self):
        self.list_repo.clear()
        for name, data in KEXT_REPO.items():
            item = QListWidgetItem()
            
            # Custom Widget for Repo Item
            wid = QWidget()
            h = QHBoxLayout(wid)
            h.setContentsMargins(10, 5, 10, 5)
            
            v = QVBoxLayout()
            lbl_name = QLabel(name)
            lbl_name.setStyleSheet("font-weight: bold; font-size: 14px; color: white;")
            lbl_desc = QLabel(data['desc'])
            lbl_desc.setStyleSheet("color: #94a3b8; font-size: 12px;")
            v.addWidget(lbl_name)
            v.addWidget(lbl_desc)
            
            btn_dl = QPushButton("Download")
            self._style_btn(btn_dl, accent=True)
            btn_dl.setFixedSize(90, 30)
            btn_dl.clicked.connect(lambda _, n=name, u=data['url']: self.download_kext(n, u))
            
            h.addLayout(v)
            h.addWidget(btn_dl)
            
            item.setSizeHint(wid.sizeHint())
            self.list_repo.addItem(item)
            self.list_repo.setItemWidget(item, wid)

    def download_kext(self, name, url):
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "Busy", "Please wait for the current download to finish.")
            return

        self.lbl_repo_status.setText(f"Downloading {name}...")
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        
        self.worker = KextDownloader(url, name, self.temp_dir)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(lambda path: self.install_downloaded_kext(name, path))
        self.worker.error.connect(self.on_download_error)
        self.worker.start()

    def install_downloaded_kext(self, name, kext_path):
        self.lbl_repo_status.setText(f"Installing {name}...")
        self.progress_bar.setVisible(False)
        
        dest_path = os.path.join(self.kexts_dir, os.path.basename(kext_path))
        
        try:
            if os.path.exists(dest_path):
                shutil.rmtree(dest_path)
            shutil.copytree(kext_path, dest_path)
            
            # Add to Config
            self._add_entry_to_plist(os.path.basename(kext_path))
            self.load_efi()
            self.lbl_repo_status.setText(f"Successfully installed {name}!")
            
        except Exception as e:
            QMessageBox.critical(self, "Install Error", f"Failed to install kext: {e}")

    def on_download_error(self, err):
        self.progress_bar.setVisible(False)
        self.lbl_repo_status.setText("Download failed.")
        QMessageBox.critical(self, "Download Error", f"Error downloading kext:\n{err}")

    def _style_btn(self, btn, accent=False, danger=False):
        base = "padding: 6px 12px; border-radius: 6px; font-weight: bold;"
        if accent:
            bg = "#38bdf8"
            hover = "#0ea5e9"
            text = "white"
        elif danger:
            bg = "#ef4444"
            hover = "#dc2626"
            text = "white"
        else:
            bg = "transparent"
            hover = "#334155"
            text = "#f1f5f9"
            base += "border: 1px solid #475569;"
            
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{ background-color: {bg}; color: {text}; {base} }}
            QPushButton:hover {{ background-color: {hover}; }}
        """)

    def load_efi(self):
        self.list_kexts.clear()
        
        if not os.path.exists(self.config_path):
            QMessageBox.critical(self, "Error", "config.plist not found in EFI/OC!")
            return

        try:
            with open(self.config_path, 'rb') as f:
                self.plist_data = plistlib.load(f)
            
            kernel_add = self.plist_data.get('Kernel', {}).get('Add', [])
            
            for entry in kernel_add:
                path = entry.get('BundlePath', 'Unknown')
                enabled = entry.get('Enabled', False)
                
                item = QListWidgetItem()
                widget = QWidget()
                w_layout = QHBoxLayout(widget)
                w_layout.setContentsMargins(5, 0, 5, 0)
                
                chk = QCheckBox(path)
                chk.setChecked(enabled)
                chk.stateChanged.connect(lambda state, p=path: self.toggle_kext(p, state))
                chk.setStyleSheet("color: white;")
                
                w_layout.addWidget(chk)
                w_layout.addStretch()
                
                # Check if file exists
                if not os.path.exists(os.path.join(self.kexts_dir, path)):
                    lbl_missing = QLabel("(Disk Missing)")
                    lbl_missing.setStyleSheet("color: #ef4444; font-size: 11px;")
                    w_layout.addWidget(lbl_missing)

                item.setSizeHint(widget.sizeHint())
                self.list_kexts.addItem(item)
                self.list_kexts.setItemWidget(item, widget)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load plist: {e}")

    def toggle_kext(self, bundle_path, state):
        if not self.plist_data: return
        
        kernel_add = self.plist_data.get('Kernel', {}).get('Add', [])
        for entry in kernel_add:
            if entry.get('BundlePath') == bundle_path:
                entry['Enabled'] = (state == Qt.Checked.value) or (state == 2)
                break
        
        self._save_plist()

    def add_local_kext(self):
        fpath, _ = QFileDialog.getOpenFileName(self, "Select Kext", "", "Kext (*.kext)")
        if not fpath: return
        
        kext_name = os.path.basename(fpath)
        dest_path = os.path.join(self.kexts_dir, kext_name)
        
        try:
            if os.path.isdir(fpath):
                if os.path.exists(dest_path):
                    shutil.rmtree(dest_path)
                shutil.copytree(fpath, dest_path)
            else:
                 pass
        except Exception as e:
            QMessageBox.critical(self, "Copy Error", f"Failed to copy kext: {e}")
            return

        self._add_entry_to_plist(kext_name)
        self.load_efi()

    def _add_entry_to_plist(self, kext_name):
        # Prevent Duplicate
        current_add = self.plist_data['Kernel']['Add']
        for x in current_add:
            if x['BundlePath'] == kext_name:
                return # Already exists
        
        entry = {
            'Arch': 'x86_64',
            'BundlePath': kext_name,
            'Comment': 'Added via Hackintoshify',
            'Enabled': True,
            'ExecutablePath': f'Contents/MacOS/{kext_name[:-5]}',
            'MaxKernel': '',
            'MinKernel': '',
            'PlistPath': 'Contents/Info.plist'
        }
        
        # Check Executable existence
        full_path = os.path.join(self.kexts_dir, kext_name)
        if not os.path.exists(os.path.join(full_path, "Contents", "MacOS", kext_name[:-5])):
            entry['ExecutablePath'] = ''
            
        self.plist_data['Kernel']['Add'].append(entry)
        self._save_plist()

    def remove_kext(self):
        row = self.list_kexts.currentRow()
        if row < 0: return
        
        item = self.list_kexts.item(row)
        widget = self.list_kexts.itemWidget(item)
        chk = widget.findChild(QCheckBox)
        bundle_path = chk.text()
        
        # Remove from Plist
        kernel_add = self.plist_data['Kernel']['Add']
        self.plist_data['Kernel']['Add'] = [x for x in kernel_add if x['BundlePath'] != bundle_path]
        
        # Remove File
        full_path = os.path.join(self.kexts_dir, bundle_path)
        if os.path.exists(full_path):
            try:
                shutil.rmtree(full_path)
            except: pass
            
        self._save_plist()
        self.load_efi()

    def _save_plist(self):
        try:
            with open(self.config_path, 'wb') as f:
                plistlib.dump(self.plist_data, f)
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save config.plist: {e}")

    def apply_theme(self, theme_name='Dark'):
        is_dark = theme_name.lower().startswith('dark')
        bg_color = "#0f172a" if is_dark else "#f8fafc"
        text_color = "#f1f5f9" if is_dark else "#0f172a"
        self.setStyleSheet(f"background-color: {bg_color}; color: {text_color}; font-family: 'Segoe UI';")
