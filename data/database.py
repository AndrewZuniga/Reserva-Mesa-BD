import pyodbc
from tkinter import messagebox
from config.settings import DB_CONFIG

class DatabaseManager:
    @staticmethod
    def get_connection():
        try:
            conn = pyodbc.connect(
                f"DRIVER={DB_CONFIG['driver']};SERVER={DB_CONFIG['server']};DATABASE={DB_CONFIG['database']};Trusted_Connection=yes;"
            )
            return conn
        except pyodbc.Error as e:
            messagebox.showerror("Error Crítico", f"No se pudo conectar a la BD:\n{e}")
            return None

    @staticmethod
    def run_query(query, params=(), fetchone=False, fetchall=False, commit=False):
        conn = DatabaseManager.get_connection()
        if not conn: return None
        
        cursor = conn.cursor()
        result = None
        try:
            cursor.execute(query, params)
            
            # --- CORRECCIÓN CRÍTICA AQUÍ ---
            if "SCOPE_IDENTITY" in query:
                # 1. Si pedimos un ID nuevo, lo leemos ANTES de hacer commit
                row = cursor.fetchone()
                if row:
                    result = int(row[0]) # Convertimos explícitamente a Entero
                
                # 2. Luego confirmamos la transacción
                if commit: conn.commit()
            
            elif commit:
                # Si es un INSERT/UPDATE/DELETE normal
                conn.commit()
                result = True
            
            elif fetchone:
                result = cursor.fetchone()
            
            elif fetchall:
                result = cursor.fetchall()
                
        except pyodbc.Error as e:
            if commit: conn.rollback()
            messagebox.showerror("Error SQL", f"Detalle del error:\n{e}")
        finally:
            cursor.close()
            conn.close()
            
        return result