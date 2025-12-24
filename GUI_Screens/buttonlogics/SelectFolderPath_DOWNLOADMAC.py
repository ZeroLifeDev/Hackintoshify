# GUI_Screens/buttonlogics/SelectFolderPath_DOWNLOADMAC.py

from PySide6.QtWidgets import QFileDialog, QWidget, QVBoxLayout, QLabel
import os

class SelectFolderPath_DOWNLOADMAC(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_path = ""

    def select_folder(self):
        """
        Opens a dialog to select a folder and stores the path.
        """
        # Use the user's home directory as the starting point
        start_path = os.path.expanduser("~")
        
        dialog = QFileDialog(self, "Select Download Path")
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.ShowDirsOnly, True)
        dialog.setDirectory(start_path)
        
        if dialog.exec():
            base_path = dialog.selectedFiles()[0]
            images_path = os.path.join(base_path, "MacImages")
            
            try:
                os.makedirs(images_path, exist_ok=True)
                self.selected_path = images_path
                print(f"Selected download path: {self.selected_path}")
            except OSError as e:
                print(f"Error creating directory: {e}")
                # Optionally, show an error message to the user
                return ""
                
        return self.selected_path

    def get_selected_path(self):
        """
        Returns the stored selected path.
        """
        return self.selected_path

# Example of how to use this class (for testing purposes)
if __name__ == '__main__':
    from PySide6.QtWidgets import QApplication, QPushButton
    import sys

    class TestWidget(QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Test Folder Selection")
            self.layout = QVBoxLayout(self)
            self.btn = QPushButton("Select Folder")
            self.label = QLabel("Selected Path: None")
            self.layout.addWidget(self.btn)
            self.layout.addWidget(self.label)

            self.folder_selector = SelectFolderPath_DOWNLOADMAC(self)
            self.btn.clicked.connect(self.do_selection)

        def do_selection(self):
            path = self.folder_selector.select_folder()
            if path:
                self.label.setText(f"Selected Path: {path}")

    app = QApplication(sys.argv)
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
    from GUI_Screens.MainScreen import MainScreen
    from GUI_Screens.SettingsScreen import SettingsScreen
    from GUI_Screens.buttonlogics.SelectFolderPath_EFI import SelectFolderPath_EFI
    
    widget = TestWidget()
    widget.show()
    sys.exit(app.exec())