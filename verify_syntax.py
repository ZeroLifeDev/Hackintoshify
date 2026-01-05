
import sys
import os
sys.path.append(os.getcwd())
try:
    from GUI_Screens.Functionality.FetchAppleImages import FetchAppleImages
    print("Module loaded successfully")
except Exception as e:
    print(f"Error loading module: {e}")
