# GUI-Screens/MainScreen.py

"""
Main Screen for hackintoshify GUI tool
Author: PanCakeeYT (Abdelrahman)
Date: December 2025s
"""


from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel


# Main Screen Class
class MainScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hackintoshify")
        self.setGeometry(100, 100, 800, 600)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        label = QLabel("Welcome to Hackintoshify!")
        layout.addWidget(label)
        