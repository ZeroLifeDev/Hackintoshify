# GUI_Screens/Setup.py

"""
Setup Screen for hackintoshify GUI tool
Author: PanCakeeYT (Abdelrahman)
Date: December 2025s
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QMessageBox
)
from PySide6.QtGui import QFont, QColor
from PySide6.QtCore import Qt
import os
import sys
import json
from .buttonlogics.SelectFolderPath_DOWNLOADMAC import SelectFolderPath_DOWNLOADMAC
from .buttonlogics.SelectFolderPath_EFI import SelectFolderPath_EFI

def get_setup_details_path():
    """Returns the platform-specific path for setup_details.json."""
    if sys.platform == "win32":
        config_dir = os.path.join(os.getenv("ProgramData"), "Hackintoshify")
    elif sys.platform == "darwin":
        config_dir = "/Library/Application Support/Hackintoshify"
    else:  # Linux
        config_dir = os.path.join(os.path.expanduser("~"), ".config", "hackintoshify")
    return os.path.join(config_dir, "setup_details.json")

def get_hardware_info():
    """Gets basic hardware information, attempting to find the dedicated GPU."""
    if sys.platform != "win32":
        return {"CPU": "N/A", "GPU": "N/A", "RAM": "N/A (non-Windows)"}
    
    try:
        import wmi
        c = wmi.WMI()
        cpu = c.Win32_Processor()[0].Name
        
        gpus = c.Win32_VideoController()
        gpu_name = "N/A"
        
        if gpus:
            # Filter out virtual/mirror drivers
            bad_keywords = ["mirror", "virtual", "remote", "rdp", "dameware"]
            real_gpus = [gpu for gpu in gpus if not any(keyword in gpu.Name.lower() for keyword in bad_keywords)]

            if real_gpus:
                # Sort by AdapterRAM if available, to find the most powerful GPU
                try:
                    sorted_gpus = sorted(real_gpus, key=lambda x: int(x.AdapterRAM), reverse=True)
                    gpu_name = sorted_gpus[0].Name
                except (AttributeError, TypeError):
                    # Fallback if AdapterRAM is not a reliable property
                    gpu_name = real_gpus[0].Name
            else:
                # If all GPUs were filtered out, fallback to the first one found
                gpu_name = gpus[0].Name

        ram = f"{round(int(c.Win32_ComputerSystem()[0].TotalPhysicalMemory) / (1024**3))} GB"
        return {"CPU": cpu, "GPU": gpu_name, "RAM": ram}
    except ImportError:
        return {"CPU": "N/A", "GPU": "N/A", "RAM": "WMI module not found"}
    except Exception as e:
        return {"CPU": "N/A", "GPU": "N/A", "RAM": f"Error: {e}"}


class Setup(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Hackintoshify | Initial Setup")
        self.setFixedWidth(700)
        self.current_theme = 'Dark'
        
        self.download_path_selector = SelectFolderPath_DOWNLOADMAC(self)
        self.efi_path_selector = SelectFolderPath_EFI(self)
        
        self._build_ui()
        self.apply_theme(self.current_theme)

    def _build_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # --- Header ---
        header = QFrame()
        header.setObjectName("header")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(40, 30, 40, 20)
        header_layout.setSpacing(5)
        
        title = QLabel("Welcome to Hackintoshify")
        title.setObjectName("h1")
        subtitle = QLabel("Let's configure your environment for the best experience.")
        subtitle.setObjectName("subtitle")
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        self.main_layout.addWidget(header)
        
        # --- Content Area ---
        content_area = QFrame()
        content_area.setObjectName("content_area")
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(40, 10, 40, 30)
        content_layout.setSpacing(25)
        self.main_layout.addWidget(content_area)

        # Hardware Info Card
        self.hw_card = QFrame()
        self.hw_card.setObjectName("card")
        hw_layout = QVBoxLayout(self.hw_card)
        hw_layout.setContentsMargins(20, 20, 20, 20)
        hw_layout.setSpacing(15)
        
        hw_title = QLabel("System Hardware")
        hw_title.setObjectName("h2")
        hw_layout.addWidget(hw_title)
        
        hw_info_container = QFrame()
        hw_grid = QVBoxLayout(hw_info_container)
        hw_grid.setContentsMargins(0, 0, 0, 0)
        hw_grid.setSpacing(10)
        
        info = get_hardware_info()
        self._add_info_row(hw_grid, "Processor", info.get("CPU", "Unknown"))
        self._add_separator(hw_grid)
        self._add_info_row(hw_grid, "Graphics", info.get("GPU", "Unknown"))
        self._add_separator(hw_grid)
        self._add_info_row(hw_grid, "Memory", info.get("RAM", "Unknown"))
        
        hw_layout.addWidget(hw_info_container)
        content_layout.addWidget(self.hw_card)

        # Paths Configuration Card
        self.config_card = QFrame()
        self.config_card.setObjectName("card")
        config_layout = QVBoxLayout(self.config_card)
        config_layout.setContentsMargins(20, 20, 20, 20)
        config_layout.setSpacing(20)
        
        config_title = QLabel("Workspace Configuration")
        config_title.setObjectName("h2")
        config_layout.addWidget(config_title)

        # Download Path
        self.download_path_ui = self._create_path_selector(
            "macOS Download Location", 
            "Select folder...", 
            self.select_download_path
        )
        self.download_path_label = self.download_path_ui["label"]
        config_layout.addWidget(self.download_path_ui["container"])

        # EFI Path
        self.efi_path_ui = self._create_path_selector(
            "EFI Build Location", 
            "Select folder...", 
            self.select_efi_path
        )
        self.efi_path_label = self.efi_path_ui["label"]
        config_layout.addWidget(self.efi_path_ui["container"])
        
        content_layout.addWidget(self.config_card)
        content_layout.addStretch()

        # --- Footer ---
        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(15)
        
        self.exit_btn = QPushButton("Exit")
        self.exit_btn.setObjectName("secondary_btn")
        self.exit_btn.clicked.connect(self.reject)
        
        self.save_btn = QPushButton("Save & Continue")
        self.save_btn.setObjectName("primary_btn")
        self.save_btn.clicked.connect(self.save_configuration)
        
        footer_layout.addStretch()
        footer_layout.addWidget(self.exit_btn)
        footer_layout.addWidget(self.save_btn)
        content_layout.addLayout(footer_layout)

    def _add_info_row(self, layout, label_text, value_text):
        row = QHBoxLayout()
        label = QLabel(label_text)
        label.setObjectName("info_label")
        value = QLabel(value_text)
        value.setObjectName("info_value")
        value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        value.setWordWrap(True) # Just in case
        row.addWidget(label)
        row.addStretch()
        row.addWidget(value)
        layout.addLayout(row)

    def _add_separator(self, layout):
        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFixedHeight(1)
        layout.addWidget(sep)

    def _create_path_selector(self, title, placeholder, callback):
        container = QFrame()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        title_lbl = QLabel(title)
        title_lbl.setObjectName("field_label")
        
        input_container = QFrame()
        input_container.setObjectName("input_box")
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(15, 10, 15, 10)
        
        path_lbl = QLabel(placeholder)
        path_lbl.setObjectName("path_text")
        path_lbl.setWordWrap(True)
        
        btn = QPushButton("Browse")
        btn.setObjectName("browse_btn")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(callback)
        
        input_layout.addWidget(path_lbl)
        input_layout.addStretch()
        input_layout.addWidget(btn)
        
        layout.addWidget(title_lbl)
        layout.addWidget(input_container)
        
        return {"container": container, "label": path_lbl, "btn": btn}

    def select_download_path(self):
        path = self.download_path_selector.select_folder()
        if path:
            self.download_path_label.setText(path)
            self.download_path_label.setStyleSheet("color: #e2e8f0;") # Highlight when selected

    def select_efi_path(self):
        path = self.efi_path_selector.select_folder()
        if path:
            self.efi_path_label.setText(path)
            self.efi_path_label.setStyleSheet("color: #e2e8f0;")

    def save_configuration(self):
        download_path = self.download_path_selector.get_selected_path()
        efi_path = self.efi_path_selector.get_selected_path()
        # Initial placeholders might be interpreted as None by selectors depending on implementation
        # But selectors likely store state internally.
        
        if not download_path or not efi_path:
            QMessageBox.warning(self, "Incomplete Setup", "Please select both a download location and an EFI destination.")
            return

        setup_details = {
            "download_path": download_path,
            "efi_path": efi_path,
            "setup_complete": True
        }
        try:
            os.makedirs(os.path.dirname(get_setup_details_path()), exist_ok=True)
            with open(get_setup_details_path(), 'w') as f:
                json.dump(setup_details, f, indent=4)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Configuration Error", f"Could not save settings:\n{str(e)}")

    def apply_theme(self, theme_name):
        # Modern Dark Theme Palette
        bg_color = "#0f172a"      # Slate 900
        card_bg = "#1e293b"       # Slate 800
        text_primary = "#f1f5f9"  # Slate 100
        text_secondary = "#94a3b8"# Slate 400
        accent_color = "#38bdf8"  # Sky 400
        accent_hover = "#7dd3fc"  # Sky 300
        border_color = "#334155"  # Slate 700
        input_bg = "#020617"      # Slate 950
        
        self.setStyleSheet(f"""
            QDialog {{ background-color: {bg_color}; }}
            
            QLabel {{ font-family: 'Segoe UI', sans-serif; color: {text_primary}; }}
            QLabel#h1 {{ font-size: 24px; font-weight: 700; color: {text_primary}; }}
            QLabel#h2 {{ font-size: 14px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: {text_secondary}; margin-bottom: 5px; }}
            QLabel#subtitle {{ font-size: 14px; color: {text_secondary}; }}
            
            QFrame#card {{
                background-color: {card_bg};
                border: 1px solid {border_color};
                border-radius: 12px;
            }}
            
            QFrame#separator {{ background-color: {border_color}; }}
            
            QLabel#info_label {{ font-size: 13px; color: {text_secondary}; }}
            QLabel#info_value {{ font-size: 13px; font-weight: 600; color: {text_primary}; }}
            
            QLabel#field_label {{ font-size: 13px; font-weight: 600; color: {text_primary}; }}
            
            QFrame#input_box {{
                background-color: {input_bg};
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
            QLabel#path_text {{ color: {text_secondary}; font-style: italic; font-size: 12px; }}
            
            QPushButton#browse_btn {{
                background-color: {card_bg};
                color: {accent_color};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 5px 12px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton#browse_btn:hover {{
                border-color: {accent_color};
                background-color: {input_bg};
            }}
            
            QPushButton#primary_btn {{
                background-color: {accent_color};
                color: #0f172a;
                border: none;
                border-radius: 8px;
                padding: 10px 24px;
                font-size: 14px;
                font-weight: 700;
            }}
            QPushButton#primary_btn:hover {{ background-color: {accent_hover}; }}
            
            QPushButton#secondary_btn {{
                background-color: transparent;
                color: {text_secondary};
                border: none;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton#secondary_btn:hover {{ color: {text_primary}; }}
        """)

if __name__ == '__main__':
    from PySide6.QtWidgets import QApplication
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    app = QApplication(sys.argv)
    setup_window = Setup()
    setup_window.exec()