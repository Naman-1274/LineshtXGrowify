# helpers/file_handler.py - Simple file handling utility
import pandas as pd

class FileHandler:
    """Simple file loading utility"""
    
    @staticmethod
    def load_file(uploaded_file):
        """Load CSV or Excel file"""
        if uploaded_file.name.lower().endswith(".xlsx"):
            return pd.read_excel(uploaded_file)
        else:
            return pd.read_csv(uploaded_file)