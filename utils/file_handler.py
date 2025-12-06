# Manejo de archivos/CSVs

import os
from typing import Dict
import pandas as pd


class FileHandler:
    @staticmethod
    def read_csv(file_path: str) -> pd.DataFrame:
        """Lee CSV con manejo de errores"""
        try:
            return pd.read_csv(file_path)
        except Exception as e:
            raise Exception(f"Error leyendo CSV: {e}")
    
    @staticmethod
    def validate_file(file_path: str) -> bool:
        """Valida que archivo existe"""
        return os.path.exists(file_path)
    
    @staticmethod
    def get_csv_info(file_path: str) -> Dict:
        """Obtiene info básica del CSV"""
        if not FileHandler.validate_file(file_path):
            return {"error": "Archivo no encontrado"}
        
        try:
            df = pd.read_csv(file_path)
            return {
                "rows": len(df),
                "columns": list(df.columns),
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                "missing": df.isnull().sum().to_dict()
            }
        except Exception as e:
            return {"error": str(e)}
