from PySide6.QtWidgets import QApplication
from GUI_Screens.MainScreen import MainScreen


def main():
    app = QApplication([])
    window = MainScreen()
    window.show()
    app.exec()
    
if __name__ == "__main__":
    main()