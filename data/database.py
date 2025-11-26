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
            
            if commit:
                conn.commit()
                if "SCOPE_IDENTITY" in query:
                    try: result = cursor.fetchone()[0]
                    except: result = True
                else:
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