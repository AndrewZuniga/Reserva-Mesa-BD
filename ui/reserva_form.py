import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime
from data.database import DatabaseManager
from config.settings import ID_RESTAURANTE_ACTUAL
from logic.reserva_controller import ReservaController

class ReservaForm(tk.Frame):
    def __init__(self, parent, main_controller):
        super().__init__(parent, width=420, bg="#f4f4f4", padx=10, pady=10)
        self.pack_propagate(False)
        self.main_window = main_controller
        self.clientes_map = {}
        self.empleados_map = {}
        self.mesas_actuales = []
        self._init_widgets()
        self.cargar_catalogos()

    def _init_widgets(self):
        self.lbl_titulo = tk.Label(self, text="NUEVA RESERVA", font=("Arial", 14, "bold"), bg="#f4f4f4")
        self.lbl_titulo.pack(pady=5)

        tk.Label(self, text="Cliente:", bg="#f4f4f4", anchor="w").pack(fill=tk.X)
        self.combo_cliente = ttk.Combobox(self, state="readonly")
        self.combo_cliente.pack(fill=tk.X, pady=2)

        tk.Label(self, text="Personas:", bg="#f4f4f4", anchor="w").pack(fill=tk.X)
        self.spin_personas = tk.Spinbox(self, from_=1, to=50, font=("Arial", 11))
        self.spin_personas.pack(fill=tk.X, pady=2)

        tk.Label(self, text="Fecha y Hora:", bg="#f4f4f4", anchor="w").pack(fill=tk.X)
        f_hora = tk.Frame(self, bg="#f4f4f4"); f_hora.pack(fill=tk.X)
        self.entry_fecha = DateEntry(f_hora, width=12, date_pattern='yyyy-mm-dd',state="readonly")
        self.entry_fecha.pack(side=tk.LEFT)
        self.spin_hora = tk.Spinbox(f_hora, from_=8, to=22, width=3); self.spin_hora.pack(side=tk.LEFT)
        tk.Label(f_hora, text=":", bg="#f4f4f4").pack(side=tk.LEFT)
        self.spin_min = tk.Spinbox(f_hora, from_=0, to=59, width=3); self.spin_min.pack(side=tk.LEFT)
        tk.Button(f_hora, text="🔄 Verificar", bg="#eee", command=self.verificar_disponibilidad).pack(side=tk.LEFT, padx=5)

        tk.Label(self, text="Mesas:", bg="#f4f4f4", anchor="w").pack(fill=tk.X, pady=5)
        f_list = tk.Frame(self); f_list.pack(fill=tk.X, expand=True)
        sb = tk.Scrollbar(f_list); sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox_mesas = tk.Listbox(f_list, selectmode=tk.MULTIPLE, height=8, yscrollcommand=sb.set)
        self.listbox_mesas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.config(command=self.listbox_mesas.yview)

        tk.Label(self, text="Empleado:", bg="#f4f4f4", anchor="w").pack(fill=tk.X)
        self.combo_empleado = ttk.Combobox(self, state="readonly")
        self.combo_empleado.pack(fill=tk.X, pady=2)

        self.btn_guardar = tk.Button(self, text="CONFIRMAR", bg="#007bff", fg="white", font=("Arial", 11, "bold"), height=2, command=self.guardar)
        self.btn_guardar.pack(fill=tk.X, pady=15)
        tk.Button(self, text="Limpiar", command=self.limpiar).pack(fill=tk.X)

    def cargar_catalogos(self):
        # NOMBRES NUEVOS: SGR_M_Cliente, idCliente
        rows = DatabaseManager.run_query("SELECT idCliente, nombre + ' ' + apellido FROM SGR_M_Cliente", fetchall=True)
        if rows:
            self.clientes_map = {r[1]: r[0] for r in rows}
            self.combo_cliente['values'] = list(self.clientes_map.keys())
        
        # NOMBRES NUEVOS: SGR_M_Empleado, idEmpleado, idRestaurante
        rows = DatabaseManager.run_query("SELECT idEmpleado, nombre FROM SGR_M_Empleado WHERE idRestaurante=?", (ID_RESTAURANTE_ACTUAL,), fetchall=True)
        if rows:
            self.empleados_map = {r[1]: r[0] for r in rows}
            self.combo_empleado['values'] = list(self.empleados_map.keys())
        
        self.verificar_disponibilidad()

    def verificar_disponibilidad(self):
        try:
            fecha = self.entry_fecha.get_date()
            dt = datetime(fecha.year, fecha.month, fecha.day, int(self.spin_hora.get()), int(self.spin_min.get()))
            id_a_ignorar = self.main_window.id_reserva_seleccionada if self.main_window.modo_edicion else None
            self.mesas_actuales = ReservaController.obtener_mesas_disponibles(dt, id_a_ignorar)
            self.listbox_mesas.delete(0, tk.END)
            for i, m in enumerate(self.mesas_actuales):
                self.listbox_mesas.insert(tk.END, m['texto'])
                self.listbox_mesas.itemconfig(i, m['estilo'])
        except: pass

    def guardar(self):
        # 1. Recolectar datos visuales para el mensaje
        cli = self.combo_cliente.get()
        pax = self.spin_personas.get()
        fecha = self.entry_fecha.get_date()
        hora = f"{self.spin_hora.get()}:{self.spin_min.get()}"
        
        # Obtener nombres de mesas seleccionadas
        indices = self.listbox_mesas.curselection()
        if not indices: return messagebox.showerror("Error", "Seleccione mesas")
        mesas_txt = ", ".join([self.mesas_actuales[i]['texto'].split(" -")[0] for i in indices])

        # 2. Ventana de Confirmación
        mensaje = (
            f"¿Está seguro de registrar esta reserva?\n\n"
            f"👤 Cliente: {cli}\n"
            f"📅 Fecha: {fecha} a las {hora}\n"
            f"👥 Personas: {pax}\n"
            f"🪑 Mesas: {mesas_txt}"
        )
        
        confirmacion = messagebox.askyesno("Confirmar Transacción", mensaje)
        
        if confirmacion:
            # Si dice SÍ, procedemos a llamar al controlador principal
            self.main_window.procesar_guardado(
                self.combo_cliente.get(), self.spin_personas.get(), 
                self.entry_fecha.get_date(), self.spin_hora.get(), self.spin_min.get(),
                self.listbox_mesas.curselection(), self.combo_empleado.get()
            )

    def limpiar(self):
        self.main_window.modo_edicion = False
        self.main_window.id_reserva_seleccionada = None
        self.lbl_titulo.config(text="NUEVA RESERVA", fg="black")
        self.btn_guardar.config(text="CONFIRMAR", bg="#007bff")
        self.combo_cliente.set('')
        self.listbox_mesas.selection_clear(0, tk.END)
        self.entry_fecha.set_date(datetime.now())
        self.verificar_disponibilidad()