import tkinter as tk
from tkinter import ttk, messagebox, Toplevel
from data.database import DatabaseManager

class ReservaMonitor(tk.Frame):
    def __init__(self, parent, main_controller):
        super().__init__(parent, bg="white", padx=15, pady=15)
        self.main_window = main_controller
        self._init_widgets()
        self.cargar_datos()

    def _init_widgets(self):
        tk.Label(self, text="Monitor de Reservas", font=("Arial", 14)).pack(anchor="w")
        cols = ("ID", "Cliente", "Pax", "Fecha", "Mesas", "Estado")
        self.tree = ttk.Treeview(self, columns=cols, show="headings")
        for col in cols: self.tree.heading(col, text=col)
        self.tree.column("ID", width=30); self.tree.column("Pax", width=30); self.tree.column("Mesas", width=120)
        self.tree.tag_configure("cancelada", background="#ffebee")
        self.tree.tag_configure("completada", background="#e8f5e9")
        self.tree.tag_configure("confirmada", background="#fff3cd")
        self.tree.pack(fill=tk.BOTH, expand=True, pady=5)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        
        f_btn = tk.Frame(self, bg="white"); f_btn.pack(fill=tk.X, pady=5)
        tk.Button(f_btn, text="🔍 Detalles", bg="#17a2b8", fg="white", command=self.ver_detalles).pack(side=tk.LEFT, padx=2)
        tk.Button(f_btn, text="✏ Editar", bg="#fd7e14", fg="white", command=self.main_window.cargar_edicion).pack(side=tk.LEFT, padx=2)
        tk.Button(f_btn, text="📞 Confirmar", bg="#ffc107", command=lambda: self.main_window.cambiar_estado(2)).pack(side=tk.LEFT, padx=2)
        tk.Button(f_btn, text="✅ Asistencia", bg="#28a745", fg="white", command=lambda: self.main_window.cambiar_estado(4)).pack(side=tk.LEFT, padx=2)
        tk.Button(f_btn, text="❌ Cancelar", bg="#dc3545", fg="white", command=lambda: self.main_window.cambiar_estado(3)).pack(side=tk.LEFT, padx=2)

        tk.Button(f_btn, text="🗑 Eliminar", bg="#343a40", fg="white", command=self.main_window.eliminar_reserva_fisica).pack(side=tk.RIGHT, padx=5)
    def cargar_datos(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        # NOMBRES NUEVOS EN QUERY
        query = """
        SELECT R.idReserva, C.nombre + ' ' + C.apellido, R.fechareserva, 
               R.Npersonas, E.Descripcion, R.idEstadoreserva
        FROM SGR_T_Reserva R
        JOIN SGR_M_Cliente C ON R.idCliente = C.idCliente
        JOIN SGR_P_Estadoreserva E ON R.idEstadoreserva = E.idEstadoreserva
        ORDER BY R.fechareserva DESC
        """
        reservas = DatabaseManager.run_query(query, fetchall=True)
        if reservas:
            for row in reservas:
                mesas = DatabaseManager.run_query(
                    "SELECT M.Nmesa FROM SGR_T_DetalleReserva DR JOIN SGR_M_Mesa M ON DR.idMesa=M.idMesa WHERE DR.idReserva=?", 
                    (row[0],), fetchall=True
                )
                mesas_str = ", ".join([m[0] for m in mesas]) if mesas else "-"
                tag = "normal"
                if row[5] == 3: tag = "cancelada"
                elif row[5] == 4: tag = "completada"
                elif row[5] == 2: tag = "confirmada"
                self.tree.insert("", "end", values=(row[0], row[1], row[3], row[2].strftime('%d/%m %H:%M'), mesas_str, row[4]), tags=(tag,))

    def on_select(self, event):
        item = self.tree.focus()
        if self.tree.item(item)['values']:
            self.main_window.id_reserva_seleccionada = self.tree.item(item)['values'][0]

    def ver_detalles(self):
        id_res = self.main_window.id_reserva_seleccionada
        if not id_res: return
        
        # NOMBRES NUEVOS EN QUERY DETALLES
        sql = """
        SELECT Rest.nombre, Rest.direccion, C.nombre + ' ' + C.apellido, C.cedula, C.telefono,
               ISNULL(P.Descripcion, 'Estándar'), ISNULL(P.Valor, 0), R.fechareserva, R.Npersonas, E.Descripcion,
               ISNULL(Emp.nombre, 'Sin asignar')
        FROM SGR_T_Reserva R
        JOIN SGR_M_Restaurante Rest ON R.idRestaurante = Rest.idRestaurante
        JOIN SGR_M_Cliente C ON R.idCliente = C.idCliente
        JOIN SGR_P_Estadoreserva E ON R.idEstadoreserva = E.idEstadoreserva
        LEFT JOIN SGR_P_Politica P ON R.idPolitica = P.idPolitica
        LEFT JOIN SGR_M_Empleado Emp ON R.idEmpleado = Emp.idEmpleado
        WHERE R.idReserva = ?
        """
        d = DatabaseManager.run_query(sql, (id_res,), fetchone=True)
        
        if d:
            top = Toplevel()
            top.geometry("500x600"); top.title("Ficha")
            tk.Label(top, text="FICHA DE RESERVA", font=("Arial", 16, "bold")).pack(pady=10)
            def mk_grp(t):
                f = tk.LabelFrame(top, text=t, padx=10, pady=5, font=("Arial", 9, "bold")); f.pack(fill=tk.X, padx=10, pady=5); return f
            
            g1 = mk_grp("Ubicación"); tk.Label(g1, text=f"Local: {d[0]}\nDir: {d[1]}", justify="left").pack(anchor="w")
            g2 = mk_grp("Cliente"); tk.Label(g2, text=f"Nombre: {d[2]}\nCI: {d[3]} | T: {d[4]}", justify="left").pack(anchor="w")
            g3 = mk_grp("Operación"); tk.Label(g3, text=f"Fecha: {d[7].strftime('%d/%m %H:%M')} | Pax: {d[8]}\nReg: {d[10]}\nEstado: {d[9]}", justify="left").pack(anchor="w")
            col = "red" if d[6] > 0 else "green"
            g4 = mk_grp("Financiero"); tk.Label(g4, text=f"Pol: {d[5]}\nCosto: ${d[6]:.2f}", fg=col, font=("Arial", 11, "bold")).pack(anchor="w")
            tk.Button(top, text="Cerrar", command=top.destroy).pack(pady=10)