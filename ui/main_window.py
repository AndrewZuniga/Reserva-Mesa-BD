import tkinter as tk
from tkinter import messagebox
from datetime import datetime
from ui.reserva_form import ReservaForm
from ui.reserva_monitor import ReservaMonitor
from data.database import DatabaseManager
from logic.reserva_controller import ReservaController
from config.settings import ID_RESTAURANTE_ACTUAL

class MainWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Gestión Reservas Modular v8.0 (SGR)")
        self.root.geometry("1250x700")
        self.id_reserva_seleccionada = None
        self.modo_edicion = False
        self.form = ReservaForm(self.root, self)
        self.form.pack(side=tk.LEFT, fill=tk.Y)
        self.monitor = ReservaMonitor(self.root, self)
        self.monitor.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    def run(self): self.root.mainloop()

    def procesar_guardado(self, nombre_cli, n_personas, fecha, hora, minuto, indices_mesa, nombre_emp):
        if not nombre_cli or not indices_mesa: return messagebox.showerror("Error", "Faltan datos")
        try:
            dt = datetime(fecha.year, fecha.month, fecha.day, int(hora), int(minuto))
            if not self.modo_edicion and dt < datetime.now(): return messagebox.showerror("Error", "Fecha pasada")
        except: return messagebox.showerror("Error", "Fecha inválida")

        pax = int(n_personas)
        cap_total = sum([self.form.mesas_actuales[i]['capacidad'] for i in indices_mesa])
        ids_mesas = [self.form.mesas_actuales[i]['id'] for i in indices_mesa]

        if cap_total < pax: return messagebox.showerror("Capacidad", "Mesas insuficientes")

        id_cli = self.form.clientes_map[nombre_cli]
        id_emp = self.form.empleados_map.get(nombre_emp)
        id_pol = ReservaController.calcular_politica(pax, 1)

        # NOMBRES NUEVOS EN QUERIES
        if self.modo_edicion:
            sql = "UPDATE SGR_T_Reserva SET fechareserva=?, Npersonas=?, idCliente=?, idEmpleado=?, idPolitica=?, idEstadoreserva=1 WHERE idReserva=?"
            DatabaseManager.run_query(sql, (dt, pax, id_cli, id_emp, id_pol, self.id_reserva_seleccionada), commit=True)
            DatabaseManager.run_query("DELETE FROM SGR_T_DetalleReserva WHERE idReserva=?", (self.id_reserva_seleccionada,), commit=True)
            id_res = self.id_reserva_seleccionada
        else:
            sql = """SET NOCOUNT ON; INSERT INTO SGR_T_Reserva (fechareserva, Npersonas, idCliente, idEmpleado, idEstadoreserva, idPolitica, idRestaurante)
                     VALUES (?, ?, ?, ?, 1, ?, ?); SELECT SCOPE_IDENTITY();"""
            id_res = DatabaseManager.run_query(sql, (dt, pax, id_cli, id_emp, id_pol, ID_RESTAURANTE_ACTUAL), commit=True)

        for m_id in ids_mesas:
            DatabaseManager.run_query("INSERT INTO SGR_T_DetalleReserva VALUES (?, ?, 0)", (id_res, m_id), commit=True)

        messagebox.showinfo("Éxito", "Guardado correctamente")
        self.form.limpiar()
        self.monitor.cargar_datos()

    def cargar_edicion(self):
        if not self.id_reserva_seleccionada: return
        # NOMBRES NUEVOS
        sql = "SELECT idCliente, Npersonas, fechareserva, idEmpleado FROM SGR_T_Reserva WHERE idReserva=?"
        d = DatabaseManager.run_query(sql, (self.id_reserva_seleccionada,), fetchone=True)
        if d:
            self.modo_edicion = True
            self.form.lbl_titulo.config(text=f"EDITANDO #{self.id_reserva_seleccionada}", fg="orange")
            self.form.btn_guardar.config(text="GUARDAR CAMBIOS", bg="orange")
            try:
                nombre = [k for k, v in self.form.clientes_map.items() if v == d[0]][0]
                self.form.combo_cliente.set(nombre)
            except: pass
            self.form.spin_personas.delete(0, tk.END); self.form.spin_personas.insert(0, d[1])
            self.form.entry_fecha.set_date(d[2])
            self.form.spin_hora.delete(0, tk.END); self.form.spin_hora.insert(0, d[2].hour)
            self.form.spin_min.delete(0, tk.END); self.form.spin_min.insert(0, d[2].minute)
            self.form.verificar_disponibilidad()

    def cambiar_estado(self, nuevo_estado):
        if not self.id_reserva_seleccionada: return
        pax = DatabaseManager.run_query("SELECT Npersonas FROM SGR_T_Reserva WHERE idReserva=?", (self.id_reserva_seleccionada,), fetchone=True)[0]
        pol = ReservaController.calcular_politica(pax, nuevo_estado)
        # NOMBRES NUEVOS
        sql = "UPDATE SGR_T_Reserva SET idEstadoreserva=?, idPolitica=? WHERE idReserva=?"
        DatabaseManager.run_query(sql, (nuevo_estado, pol, self.id_reserva_seleccionada), commit=True)
        self.monitor.cargar_datos()
        self.form.verificar_disponibilidad()