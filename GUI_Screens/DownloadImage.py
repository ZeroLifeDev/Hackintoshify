# GUI_Screens/DownloadImage.py

import sys
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QComboBox, QFrame, QMessageBox, 
    QProgressBar, QScrollArea, QSizePolicy, QGraphicsOpacityEffect
)
from PySide6.QtGui import QFont, QColor, QIcon, QCursor
from PySide6.QtCore import Qt, QSize, QThread, Signal, Slot, Property, QPropertyAnimation, QEasingCurve

# Import our backend
from .Functionality.FetchAppleImages import FetchAppleImages
from .Functionality.DownloadManager import DownloadManager, DownloadWorker

class LoadingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents) # Blocking? No, we want to block interaction
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        
        # Background
        self.bg = QFrame(self)
        self.bg.setStyleSheet("background-color: rgba(0, 0, 0, 180); border-radius: 8px;")
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        # Spinner / Text
        container = QWidget()
        c_layout = QVBoxLayout(container)
        
        self.lbl_loading = QLabel("Loading macOS Versions...")
        self.lbl_loading.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.lbl_loading.setStyleSheet("color: white; background: transparent;")
        self.lbl_loading.setAlignment(Qt.AlignCenter)
        
        self.lbl_details = QLabel("Initializing...")
        self.lbl_details.setFont(QFont("Consolas", 10))
        self.lbl_details.setStyleSheet("color: #cbd5e1; background: transparent;")
        self.lbl_details.setAlignment(Qt.AlignCenter)
        
        self.pbar = QProgressBar()
        self.pbar.setFixedSize(200, 6)
        self.pbar.setTextVisible(False)
        self.pbar.setStyleSheet("QProgressBar { background: #334155; border-radius: 3px; } QProgressBar::chunk { background: #38bdf8; border-radius: 3px; }")
        self.pbar.setRange(0, 0) # Infinite mode
        
        c_layout.addWidget(self.lbl_loading)
        c_layout.addWidget(self.pbar, 0, Qt.AlignCenter)
        c_layout.addWidget(self.lbl_details)
        layout.addWidget(container)
        
        self.hide()

    def resizeEvent(self, event):
        self.bg.setGeometry(self.rect())
        super().resizeEvent(event)

    def set_status(self, text):
        self.lbl_details.setText(text)

class FetchWorker(QThread):
    data_ready = Signal(list)
    status_update = Signal(str)
    
    def run(self):
        try:
            # We pass self.emit_status as the callback
            fetcher = FetchAppleImages(verbose=True, use_cache=True, status_callback=self.emit_status)
            self.data_ready.emit(fetcher.apple_images)
        except Exception as e:
            self.status_update.emit(f"Error: {e}")
            self.data_ready.emit([]) # Return empty on error
            
    def emit_status(self, text):
        self.status_update.emit(str(text))

# ... (DownloadItemWidget remains mostly same, including it here for completeness)
class DownloadItemWidget(QFrame):
    selected = Signal(str, str) # name, path

    def __init__(self, name, worker: DownloadWorker, parent=None):
        super().__init__(parent)
        self.worker = worker # This can be None if restored from disk initially
        self.setFixedHeight(100)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFrameShape(QFrame.StyledPanel)
        self.setObjectName("DownloadItem")
        
        self.download_name = name # Store name
        self.download_path = "" # Store path
        
        layout = QVBoxLayout(self)
        
        # Top Row: Name and Status
        top_row = QHBoxLayout()
        self.lbl_name = QLabel(name)
        self.lbl_name.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.lbl_name.setStyleSheet("background: transparent; border: none;")
        self.lbl_status = QLabel("Starting...")
        self.lbl_status.setFont(QFont("Segoe UI", 10))
        self.lbl_status.setStyleSheet("color: #94a3b8; background: transparent; border: none;")
        
        top_row.addWidget(self.lbl_name)
        top_row.addStretch()
        top_row.addWidget(self.lbl_status)
        layout.addLayout(top_row)
        
        # Progress Bar
        self.pbar = QProgressBar()
        self.pbar.setTextVisible(False)
        self.pbar.setFixedHeight(8)
        self.pbar.setObjectName("pbar")
        layout.addWidget(self.pbar)
        
        # Bottom Row: Speed and Controls
        bot_row = QHBoxLayout()
        self.lbl_speed = QLabel("0 KB/s")
        self.lbl_speed.setFont(QFont("Consolas", 9))
        self.lbl_speed.setStyleSheet("color: #64748b; background: transparent; border: none;")
        
        bot_row.addWidget(self.lbl_speed)
        bot_row.addStretch()
        
        self.btn_pause = QPushButton("⏸")
        self.btn_pause.setFixedSize(30, 30)
        self.btn_pause.setCursor(Qt.PointingHandCursor)
        self.btn_pause.setToolTip("Pause/Resume")
        self.btn_pause.clicked.connect(self.toggle_pause)
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setFixedSize(80, 30)
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setToolTip("Cancel and Delete")
        self.btn_cancel.clicked.connect(self.cancel_download)
        
        self.btn_select = QPushButton("Select")
        self.btn_select.setFixedSize(80, 30)
        self.btn_select.setCursor(Qt.PointingHandCursor)
        self.btn_select.setStyleSheet("background-color: #38bdf8; color: white; border-radius: 4px; font-weight: bold;")
        self.btn_select.setVisible(False)
        self.btn_select.clicked.connect(self.select_download)

        bot_row.addWidget(self.btn_pause)
        bot_row.addWidget(self.btn_cancel)
        bot_row.addWidget(self.btn_select)
        layout.addLayout(bot_row)
        
        # Connect Signals
        # Connect Signals
        if self.worker:
            self._connect_signals()
        else:
            # If restored from disk, we start in Paused state
            self.lbl_status.setText("Paused")
            self.btn_pause.setText("▶")
            self.is_paused = True
            
            # Setup Animation
            self.anim_effect = QGraphicsOpacityEffect(self)
            self.anim_effect.setOpacity(1.0)
            self.setGraphicsEffect(self.anim_effect)
            
            self.anim = QPropertyAnimation(self.anim_effect, b"opacity")
            self.anim.setDuration(1000)
            self.anim.setEasingCurve(QEasingCurve.OutQuad)
            
            # Try to get saved progress
            # We can't get it easily without worker, but we can display "Resumable"
            self.lbl_speed.setText("Ready to Resume")
        
        self.is_paused = (self.lbl_status.text() == "Paused")
        
        self.is_paused = False

    def on_progress(self, pct, speed, dl, total):
        self.pbar.setValue(pct)
        self.lbl_speed.setText(f"{speed} • {dl//(1024*1024)}MB / {total//(1024*1024)}MB")
    
    def on_status(self, status):
        self.lbl_status.setText(status)
        if status == "Paused":
            self.btn_pause.setText("▶")
            self.btn_pause.setToolTip("Resume Download")
            self.is_paused = True
        elif status == "Downloading":
            self.btn_pause.setText("⏸")
            self.btn_pause.setToolTip("Pause Download")
            self.is_paused = False
        if status == "Finished":
            self.pbar.setVisible(False) # Hide bar
            self.btn_pause.setVisible(False)
            self.btn_cancel.setVisible(True)
            self.btn_select.setVisible(True) # Show Select
            self.btn_cancel.setText("Delete")
            self.btn_cancel.setToolTip("Delete File")
            self.lbl_speed.setText("Download Complete")
            self.lbl_speed.setStyleSheet("color: #22c55e; background: transparent;") # Green
            
            # Success Animation (Fade out slightly then in)
            self.anim.setStartValue(1.0)
            self.anim.setEndValue(0.5)
            self.anim.setLoopCount(2)
            self.anim.start()
            
            self.setStyleSheet("""
                #DownloadItem {
                    border: 1px solid #22c55e;
                    background-color: rgba(34, 197, 94, 0.1);
                    border-radius: 8px;
                }
            """)
        else:
            self.pbar.setVisible(True)
            self.lbl_speed.setStyleSheet("color: #64748b; background: transparent;")
            # Reset style (assuming dark mode default for simplicity or we need a improved reset)
            self.setStyleSheet("""
                #DownloadItem {
                    border: 1px solid #334155; 
                    background-color: #1e293b;
                    border-radius: 8px;
                }
            """)
            
            self.btn_pause.setVisible(True)
            self.btn_select.setVisible(False)
            self.btn_cancel.setText("Cancel")
            self.btn_cancel.setToolTip("Cancel and Delete")
        if status == "Pending":
            self.lbl_status.setText("Pending...")

    def on_finished(self):
        self.lbl_status.setText("Success")
        self.pbar.setValue(100)
    
    def on_error(self, err):
        self.lbl_status.setText(f"Error: {err}")
        self.lbl_status.setToolTip(str(err)) 
        self.lbl_status.setStyleSheet("color: #ef4444; background: transparent;")
        print(f"Dataset UI Error: {err}") 
        
        self.btn_pause.setText("▶")
        self.btn_pause.setToolTip("Retry")
        self.is_paused = True 

    def toggle_pause(self):
        # We need to find the task in manager to resume it property
        # Since Widget has ref to worker, check if worker is running
        parent_screen = self.window()
        if hasattr(parent_screen, 'manager'):
             # Find task by worker/url path
             task = None
             for t in parent_screen.manager.downloads:
                 # If worker is None (loaded from disk), match by name/path?
                 # Or if worker matches
                 if t['worker'] == self.worker:
                     task = t
                     break
                 # Fallback for restored tasks where self.worker is None initially?
                 # Actually we pass a worker to this widget.
                 # If restored, we might pass a Dummy worker or None? 
                 # We need to handle restored task -> Widget binding better.
             
             if not task: 
                 # Maybe matched by name?
                 for t in parent_screen.manager.downloads:
                     if t['name'] == self.lbl_name.text():
                         task = t
                         break
            
             if task:
                 if self.is_paused:
                     # Resume
                     new_worker = parent_screen.manager.resume_download(task)
                     # We must re-bind signals to the new worker!
                     self.worker = new_worker
                     self._connect_signals()
                     self.worker.start_download() # Should be auto-started by thread generally but explicit is fine
                 else:
                     parent_screen.manager.pause_download(task)

    def _connect_signals(self):
        if self.worker:
            self.worker.progress.connect(self.on_progress)
            self.worker.status_changed.connect(self.on_status)
            self.worker.finished.connect(self.on_finished)
            self.worker.error.connect(self.on_error)
    
    def cancel_download(self):
        # Find task
        parent_screen = self.window()
        if hasattr(parent_screen, 'manager'):
             task = None
             for t in parent_screen.manager.downloads:
                 if t['worker'] == self.worker or t['name'] == self.lbl_name.text():
                     task = t
                     break
                     
             if task:
                 if self.btn_cancel.text() == "Delete":
                      # It's a finished task, delete the final file
                      try: 
                          if os.path.exists(task['path']): os.remove(task['path'])
                      except: pass
                      parent_screen.manager.cancel_download(task) # Remove from list
                 else:
                      # It's running/paused, cancel it
                      parent_screen.manager.cancel_download(task)

        # UI Removal
        self.setParent(None)
        self.deleteLater()

    def select_download(self):
        # Find task to get path
        parent_screen = self.window()
        if hasattr(parent_screen, 'manager'):
             for t in parent_screen.manager.downloads:
                 if t['name'] == self.download_name: # Match by name is safest if worker is None
                     self.download_path = t['path']
                     break
        
        if self.download_path and os.path.exists(self.download_path):
            self.selected.emit(self.download_name, self.download_path)
        else:
            # Maybe path was not set or file moved
            print("Selection failed: Path not found")

class DownloadImageScreen(QWidget):
    image_selected = Signal(str, str) # name, path
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Download macOS")
        self.resize(800, 600)
        # We don't want to destroy on close, we just want to hide
        # But we also don't want the user to think the app is broken if they close the main app.
        # MainScreen owns us, so if MainScreen closes, we close.
        # Here we just override closeEvent to hide.
        self.setWindowFlags(Qt.Window) # Make it a standard window, not a Dialog to allow minimizing/hiding independently
        
        # Manager & Data
        self.manager = DownloadManager(self)
        self.images = []
        self.selected_image = None
        
        # Layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self._build_ui()
        
        # Loading Overlay (Added after UI build so it sits on top)
        self.loading_overlay = LoadingOverlay(self)
        self.loading_overlay.resize(self.size())
        
        # Trigger fetch
        self.start_fetch()
        
        # Restore existing downloads
        self.restore_downloads()
        
        self.apply_theme("Dark") 

    def restore_downloads(self):
        # Manager already loaded state in __init__
        # We just need to iterate logic
        count = 0
        for task in self.manager.downloads:
            # Create widget (worker is None)
            item = DownloadItemWidget(task['name'], None, self.list_container)
            item.on_status(task['status']) # Set initial UI state
            item.selected.connect(self.on_item_selected)
            self._apply_item_theme(item)
            self.list_layout.insertWidget(0, item)
            count += 1
        
        if count > 0:
            print(f"Restored {count} downloads.") 

    def closeEvent(self, event):
        # Instead of stopping, we just hide the window to allow "background" downloading
        # The MainScreen holds our reference, so we won't be GC'd.
        if hasattr(self, 'manager'):
            self.manager.save_state()
            
        self.hide()
        event.ignore() # Prevent actual close/destruction

    def resizeEvent(self, event):
        self.loading_overlay.resize(self.size())
        super().resizeEvent(event)

    def _build_ui(self):
        # --- Header ---
        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(70)
        h_layout = QHBoxLayout(header)
        title = QLabel("Download Manager")
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
        
        # --- Top Control Area ---
        top_area = QFrame()
        top_area.setObjectName("top_area")
        top_layout = QVBoxLayout(top_area)
        top_layout.setContentsMargins(30, 20, 30, 20)
        
        l1 = QLabel("Select Version:")
        l1.setObjectName("label_sub")
        self.combo = QComboBox()
        self.combo.setFixedHeight(40)
        self.combo.currentIndexChanged.connect(self.on_selection_change)
        
        self.btn_download = QPushButton("Add to Queue")
        self.btn_download.setFixedSize(140, 40)
        self.btn_download.clicked.connect(self.add_download)
        self.btn_download.setObjectName("btn_primary")
        self.btn_download.setEnabled(False) # Disabled until loaded
        
        row = QHBoxLayout()
        row.addWidget(self.combo, 4)
        row.addWidget(self.btn_download, 1)
        
        top_layout.addWidget(l1)
        top_layout.addLayout(row)
        self.layout.addWidget(top_area)
        
        # --- Downloads List ---
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setObjectName("scroll_area")
        
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setAlignment(Qt.AlignTop)
        self.list_layout.setSpacing(15)
        self.list_layout.setContentsMargins(30, 20, 30, 20)
        
        self.scroll.setWidget(self.list_container)
        self.layout.addWidget(self.scroll)

    def start_fetch(self):
        self.loading_overlay.show()
        self.loading_overlay.raise_()
        
        self.fetch_worker = FetchWorker(self)
        self.fetch_worker.data_ready.connect(self.on_data_loaded)
        self.fetch_worker.status_update.connect(self.loading_overlay.set_status)
        self.fetch_worker.start()

    def on_data_loaded(self, images):
        self.images = images
        self.loading_overlay.hide()
        
        self.combo.clear()
        if not self.images:
            self.combo.addItem("No images found (Error)", None)
            return

        for img in self.images:
            self.combo.addItem(img['name'], img)
            
        self.btn_download.setEnabled(True)
        self.on_selection_change(0)

    def on_selection_change(self, index):
        if index >= 0:
            self.selected_image = self.combo.itemData(index)

    def add_download(self):
        if not self.selected_image: return
        
        url = self.selected_image['url']
        
        # Get custom download path
        base_path = self.get_download_path()
        fname = f"{self.selected_image['id']}_BaseSystem.dmg"
        dest = os.path.join(base_path, fname)
        
        worker = self.manager.start_download(url, dest, self.selected_image['name'])
        
        item = DownloadItemWidget(self.selected_image['name'], worker, self.list_container)
        item.selected.connect(self.on_item_selected)
        self._apply_item_theme(item)
        self.list_layout.insertWidget(0, item)

    def on_item_selected(self, name, path):
         self.image_selected.emit(name, path)
         self.hide()

    def get_download_path(self):
        # reuse helper from Setup or duplicate logic
        import sys
        if sys.platform == "win32":
            config_dir = os.path.join(os.getenv("ProgramData"), "Hackintoshify")
        elif sys.platform == "darwin":
            config_dir = "/Library/Application Support/Hackintoshify"
        else:
            config_dir = os.path.join(os.path.expanduser("~"), ".config", "hackintoshify")
            
        setup_file = os.path.join(config_dir, "setup_details.json")
        default_dl = os.path.join(os.path.expanduser("~"), "Downloads")
        
        if os.path.exists(setup_file):
            try:
                import json
                with open(setup_file, 'r') as f:
                    data = json.load(f)
                    return data.get("download_path", default_dl)
            except:
                pass
        return default_dl

    def _apply_item_theme(self, item):
        is_dark = True # forced for safe default, ideally read from parent
        border = "#334155" if is_dark else "#cbd5e1"
        bg = "#1e293b" if is_dark else "#ffffff"
        item.setStyleSheet(f"""
            #DownloadItem {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 8px;
            }}
        """)

    def apply_theme(self, theme_name='Dark'):
        is_dark = theme_name.lower().startswith('dark')
        bg_color = "#0f172a" if is_dark else "#f8fafc"
        card_bg = "#1e293b" if is_dark else "#ffffff"
        text_p = "#f1f5f9" if is_dark else "#0f172a"
        border = "#334155" if is_dark else "#cbd5e1"
        accent = "#38bdf8" if is_dark else "#0284c7"
        
        self.setStyleSheet(f"""
            QWidget {{ background-color: {bg_color}; font-family: 'Segoe UI'; color: {text_p}; }}
            QFrame#header, QFrame#top_area {{ background-color: {bg_color}; border-bottom: 1px solid {border}; }}
            QScrollArea {{ border: none; background: transparent; }}
            QComboBox {{ background-color: {card_bg}; border: 1px solid {border}; padding: 5px; color: {text_p}; }}
            QPushButton#btn_primary {{ background-color: {accent}; color: white; border-radius: 6px; font-weight: bold; }}
            QPushButton#close_btn {{ background: transparent; border: none; color: {text_p}; font-size: 16px; }}
            QProgressBar {{ border: 1px solid {border}; border-radius: 4px; background: {bg_color}; text-align: center; }}
            QProgressBar::chunk {{ background-color: {accent}; border-radius: 4px; }}
        """)