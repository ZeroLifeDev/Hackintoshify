# GUI_Screens/buttonlogics/SelectFolderPath_EFI.py

from PySide6.QtWidgets import QFileDialog, QWidget
import os

class SelectFolderPath_EFI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_path = ""

    def select_folder(self):
        """
        Opens a dialog to select a folder, creates an 'EFI_MADE' subdirectory, 
        and stores the path to the subdirectory.
        """
        start_path = os.path.expanduser("~")
        
        dialog = QFileDialog(self, "Select Base Folder for EFI")
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.ShowDirsOnly, True)
        dialog.setDirectory(start_path)
        
        if dialog.exec():
            base_path = dialog.selectedFiles()[0]
            efi_path = os.path.join(base_path, "EFI_MADE")
            
            try:
                os.makedirs(efi_path, exist_ok=True)
                self.selected_path = efi_path
                print(f"Selected EFI path: {self.selected_path}")
            except OSError as e:
                print(f"Error creating directory: {e}")
                return ""
                
        return self.selected_path

    def get_selected_path(self):
        """
        Returns the stored selected path.
        """
        return self.selected_path

if __name__ == '__main__':
    from PySide6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QLabel
    import sys

    class TestWidget(QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Test EFI Folder Selection")
            self.layout = QVBoxLayout(self)
            self.btn = QPushButton("Select Folder for EFI")
            self.label = QLabel("Selected Path: None")
            self.layout.addWidget(self.btn)
            self.layout.addWidget(self.label)

            self.folder_selector = SelectFolderPath_EFI(self)
            self.btn.clicked.connect(self.do_selection)

        def do_selection(self):
            path = self.folder_selector.select_folder()
            if path:
                self.label.setText(f"Selected Path: {path}")

    app = QApplication(sys.argv)
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
    
    widget = TestWidget()
    widget.show()
    sys.exit(app.exec())