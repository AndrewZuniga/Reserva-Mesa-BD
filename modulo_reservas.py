import tkinter as tk
from tkinter import ttk, messagebox, Toplevel
from tkcalendar import DateEntry
import pyodbc
from datetime import datetime, timedelta

# =============================================================================
# 1. CAPA DE CONFIGURACIÓN Y CONSTANTES
# =============================================================================
DB_CONFIG = {
    'driver': '{SQL Server}',
    'server': 'DESKTOP-6FD699I\\SQLEXPRESS', # <--- TU SERVIDOR
    'database': 'ReservaRestaurante'
}

# Colores y Estilos
COLOR_OCUPADA = {'bg': '#ffcccc', 'fg': 'darkred'}   # Rojo
COLOR_RESERVADA = {'bg': '#fff3cd', 'fg': '#856404'} # Amarillo
COLOR_DISPONIBLE = {'bg': 'white', 'fg': 'black'}    # Blanco

# =============================================================================
# 2. CAPA DE ACCESO A DATOS (DATABASE MANAGER)
# =============================================================================
class DatabaseManager:
    @staticmethod
    def get_connection():
        try:
            conn = pyodbc.connect(
                f"DRIVER={DB_CONFIG['driver']};SERVER={DB_CONFIG['server']};DATABASE={DB_CONFIG['database']};Trusted_Connection=yes;"
            )
            return conn
        except pyodbc.Error as e:
            messagebox.showerror("Error de Base de Datos", f"No se pudo conectar:\n{e}")
            return None

    @staticmethod
    def run_query(query, params=(), fetchone=False, fetchall=False, commit=False):
        """Método universal para ejecutar consultas de forma segura."""
        conn = DatabaseManager.get_connection()
        if not conn: return None
        
        cursor = conn.cursor()
        result = None
        try:
            cursor.execute(query, params)
            
            if commit:
                conn.commit()
                # Si es un INSERT con SCOPE_IDENTITY, intentamos recuperar el ID
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
            messagebox.showerror("Error SQL", f"Falló la consulta:\n{e}")
        finally:
            cursor.close() # Cerramos cursor explícitamente
            conn.close()   # Cerramos conexión
            
        return result

# =============================================================================
# 3. CAPA DE LÓGICA DE NEGOCIO (CONTROLLER)
# =============================================================================
class ReservaController:
    ID_RESTAURANTE = 1

    @staticmethod
    def calcular_politica(n_personas, id_estado):
        """Regla de Negocio: Define qué política aplica."""
        if id_estado == 3: return 1 # Multa por Cancelación
        if n_personas > 10: return 2 # Evento Grande
        return 3 # Estándar

    @staticmethod
    def obtener_mesas_disponibles(fecha_filtro=None, id_reserva_ignorar=None):
        """Devuelve lista de mesas con su estado calculado según fecha."""
        # 1. Traer todas las mesas
        sql_mesas = "SELECT id_mesa, numero_mesa, capacidad, id_estado_mesa FROM Mesa WHERE id_restaurante = ?"
        todas = DatabaseManager.run_query(sql_mesas, (ReservaController.ID_RESTAURANTE,), fetchall=True)
        
        mesas_procesadas = []
        ids_ocupados = []

        # 2. Calcular ocupación si hay fecha
        if fecha_filtro:
            inicio = fecha_filtro - timedelta(hours=1, minutes=59)
            fin = fecha_filtro + timedelta(hours=1, minutes=59)
            
            sql_ocup = """
            SELECT DISTINCT DR.id_mesa, R.id_estado_reserva
            FROM Detalle_Reserva DR
            JOIN Reserva R ON DR.id_reserva = R.id_reserva
            WHERE R.id_estado_reserva IN (1, 2, 4) 
            AND R.fecha_reserva BETWEEN ? AND ?
            """
            params = [inicio, fin]
            
            if id_reserva_ignorar:
                sql_ocup += " AND R.id_reserva != ?"
                params.append(id_reserva_ignorar)

            ocupadas_raw = DatabaseManager.run_query(sql_ocup, tuple(params), fetchall=True)
            
            # Mapear ID_MESA -> ESTADO_RESERVA
            # Prioridad: Si hay varias reservas, la '4' (Completada) gana visualmente
            mapa_estados = {}
            for row in ocupadas_raw:
                id_m, estado = row[0], row[1]
                if id_m not in mapa_estados or estado == 4:
                    mapa_estados[id_m] = estado
            
            ids_ocupados = mapa_estados

        # 3. Construir objetos visuales
        for mesa in todas:
            id_m, num, cap, _ = mesa
            estado_res = ids_ocupados.get(id_m) if fecha_filtro else None
            
            estilo = COLOR_DISPONIBLE
            texto_estado = "(Disp)"

            if estado_res == 4:
                estilo = COLOR_OCUPADA
                texto_estado = "(OCUPADA)"
            elif estado_res in [1, 2]:
                estilo = COLOR_RESERVADA
                texto_estado = "(RESERVADA)"

            mesas_procesadas.append({
                'id': id_m,
                'texto': f"{num} - Cap: {cap} p. {texto_estado}",
                'capacidad': cap,
                'estilo': estilo
            })
            
        return mesas_procesadas

# =============================================================================
# 4. CAPA DE PRESENTACIÓN (UI)
# =============================================================================
class SistemaReservasUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Gestión POS Restaurante v7.0 (Refactorizado)")
        self.root.geometry("1250x700")
        
        # Variables de instancia (Estado de la UI)
        self.id_reserva_seleccionada = None
        self.modo_edicion = False
        self.clientes_map = {}
        self.empleados_map = {}
        self.mesas_actuales = [] # Lista de diccionarios con info de mesas

        self._init_components()
        self.cargar_datos_iniciales()
        self.verificar_disponibilidad() # Carga inicial de mesas
        self.cargar_monitor_reservas()
        
        self.root.mainloop()

    def _init_components(self):
        # --- PANEL IZQUIERDO (Formulario) ---
        p_izq = tk.Frame(self.root, width=420, bg="#f4f4f4", padx=10, pady=10)
        p_izq.pack(side=tk.LEFT, fill=tk.Y)
        p_izq.pack_propagate(False)

        self.lbl_titulo = tk.Label(p_izq, text="NUEVA RESERVA", font=("Arial", 14, "bold"), bg="#f4f4f4")
        self.lbl_titulo.pack(pady=5)

        # Campos
        tk.Label(p_izq, text="Cliente:", bg="#f4f4f4", anchor="w").pack(fill=tk.X)
        self.combo_cliente = ttk.Combobox(p_izq, state="readonly")
        self.combo_cliente.pack(fill=tk.X, pady=2)

        tk.Label(p_izq, text="Personas:", bg="#f4f4f4", anchor="w").pack(fill=tk.X)
        self.spin_personas = tk.Spinbox(p_izq, from_=1, to=50, font=("Arial", 11))
        self.spin_personas.pack(fill=tk.X, pady=2)

        tk.Label(p_izq, text="Fecha y Hora:", bg="#f4f4f4", anchor="w").pack(fill=tk.X)
        f_hora = tk.Frame(p_izq, bg="#f4f4f4"); f_hora.pack(fill=tk.X)
        self.entry_fecha = DateEntry(f_hora, width=12, date_pattern='yyyy-mm-dd')
        self.entry_fecha.pack(side=tk.LEFT)
        self.spin_hora = tk.Spinbox(f_hora, from_=8, to=22, width=3); self.spin_hora.pack(side=tk.LEFT)
        tk.Label(f_hora, text=":", bg="#f4f4f4").pack(side=tk.LEFT)
        self.spin_min = tk.Spinbox(f_hora, from_=0, to=59, width=3); self.spin_min.pack(side=tk.LEFT)
        tk.Button(f_hora, text="🔄 Verificar", bg="#eee", command=self.verificar_disponibilidad).pack(side=tk.LEFT, padx=5)

        tk.Label(p_izq, text="Mesas:", bg="#f4f4f4", anchor="w").pack(fill=tk.X, pady=(5,0))
        f_list = tk.Frame(p_izq); f_list.pack(fill=tk.X, expand=True)
        sb = tk.Scrollbar(f_list); sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox_mesas = tk.Listbox(f_list, selectmode=tk.MULTIPLE, height=8, yscrollcommand=sb.set)
        self.listbox_mesas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.config(command=self.listbox_mesas.yview)

        tk.Label(p_izq, text="Empleado:", bg="#f4f4f4", anchor="w").pack(fill=tk.X)
        self.combo_empleado = ttk.Combobox(p_izq, state="readonly")
        self.combo_empleado.pack(fill=tk.X, pady=2)

        self.btn_guardar = tk.Button(p_izq, text="CONFIRMAR", bg="#007bff", fg="white", font=("Arial", 11, "bold"), height=2, command=self.accion_guardar)
        self.btn_guardar.pack(fill=tk.X, pady=15)
        tk.Button(p_izq, text="Limpiar", command=self.limpiar_formulario).pack(fill=tk.X)

        # --- PANEL DERECHO (Monitor) ---
        p_der = tk.Frame(self.root, bg="white", padx=15, pady=15)
        p_der.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        tk.Label(p_der, text="Monitor de Reservas", font=("Arial", 14)).pack(anchor="w")

        cols = ("ID", "Cliente", "Pax", "Fecha", "Mesas", "Estado")
        self.tree = ttk.Treeview(p_der, columns=cols, show="headings")
        for col in cols: self.tree.heading(col, text=col)
        self.tree.column("ID", width=30); self.tree.column("Pax", width=30); self.tree.column("Mesas", width=120)
        
        # Tags de colores para filas
        self.tree.tag_configure("cancelada", background="#ffebee")
        self.tree.tag_configure("completada", background="#e8f5e9")
        self.tree.tag_configure("confirmada", background="#fff3cd")
        
        self.tree.pack(fill=tk.BOTH, expand=True, pady=5)
        self.tree.bind("<<TreeviewSelect>>", self.seleccionar_reserva)

        # Botonera
        f_btn = tk.Frame(p_der, bg="white"); f_btn.pack(fill=tk.X, pady=5)
        tk.Button(f_btn, text="🔍 Detalles", bg="#17a2b8", fg="white", command=self.ver_detalles).pack(side=tk.LEFT, padx=2)
        tk.Button(f_btn, text="✏ Editar", bg="#fd7e14", fg="white", command=self.preparar_edicion).pack(side=tk.LEFT, padx=2)
        tk.Button(f_btn, text="📞 Confirmar", bg="#ffc107", command=lambda: self.actualizar_estado(2)).pack(side=tk.LEFT, padx=2)
        tk.Button(f_btn, text="✅ Asistencia", bg="#28a745", fg="white", command=lambda: self.actualizar_estado(4)).pack(side=tk.LEFT, padx=2)
        tk.Button(f_btn, text="❌ Cancelar", bg="#dc3545", fg="white", command=lambda: self.actualizar_estado(3)).pack(side=tk.LEFT, padx=2)

    def cargar_datos_iniciales(self):
        # Clientes
        rows = DatabaseManager.run_query("SELECT id_cliente, nombre + ' ' + apellido FROM Cliente", fetchall=True)
        if rows:
            self.clientes_map = {r[1]: r[0] for r in rows}
            self.combo_cliente['values'] = list(self.clientes_map.keys())

        # Empleados
        rows = DatabaseManager.run_query("SELECT id_empleado, nombre FROM Empleado WHERE id_restaurante=?", (ReservaController.ID_RESTAURANTE,), fetchall=True)
        if rows:
            self.empleados_map = {r[1]: r[0] for r in rows}
            self.combo_empleado['values'] = list(self.empleados_map.keys())

    def verificar_disponibilidad(self):
        """Actualiza la lista de mesas según la fecha seleccionada en la UI."""
        try:
            fecha = self.entry_fecha.get_date()
            hora = int(self.spin_hora.get())
            minutos = int(self.spin_min.get())
            dt_seleccionada = datetime(fecha.year, fecha.month, fecha.day, hora, minutos)
            
            # Llamamos a la lógica
            self.mesas_actuales = ReservaController.obtener_mesas_disponibles(dt_seleccionada, self.id_reserva_seleccionada)
            
            # Actualizamos UI
            self.listbox_mesas.delete(0, tk.END)
            for i, m in enumerate(self.mesas_actuales):
                self.listbox_mesas.insert(tk.END, m['texto'])
                self.listbox_mesas.itemconfig(i, m['estilo'])
                
            self.lbl_titulo.config(text=f"Disp: {dt_seleccionada.strftime('%H:%M')}", fg="blue")
            
        except ValueError:
            messagebox.showerror("Error", "Formato de hora inválido")

    def cargar_monitor_reservas(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        
        query = """
        SELECT R.id_reserva, C.nombre + ' ' + C.apellido, R.fecha_reserva, 
               R.numero_personas, E.descripcion, R.id_estado_reserva
        FROM Reserva R
        JOIN Cliente C ON R.id_cliente = C.id_cliente
        JOIN Estado_Reserva E ON R.id_estado_reserva = E.id_estado_reserva
        ORDER BY R.fecha_reserva DESC
        """
        reservas = DatabaseManager.run_query(query, fetchall=True)
        
        if reservas:
            for row in reservas:
                # Obtener mesas concatenadas (Subquery pequeña)
                mesas = DatabaseManager.run_query(
                    "SELECT M.numero_mesa FROM Detalle_Reserva DR JOIN Mesa M ON DR.id_mesa=M.id_mesa WHERE DR.id_reserva=?", 
                    (row[0],), fetchall=True
                )
                mesas_str = ", ".join([m[0] for m in mesas]) if mesas else "Sin mesa"
                
                tag = "normal"
                if row[5] == 3: tag = "cancelada"
                elif row[5] == 4: tag = "completada"
                elif row[5] == 2: tag = "confirmada"
                
                self.tree.insert("", "end", values=(row[0], row[1], row[3], row[2].strftime('%d/%m %H:%M'), mesas_str, row[4]), tags=(tag,))

    def accion_guardar(self):
        # 1. Recolección y Validación Básica
        nombre_cli = self.combo_cliente.get()
        indices_mesa = self.listbox_mesas.curselection()
        
        if not nombre_cli: return messagebox.showerror("Error", "Falta Cliente")
        if not indices_mesa: return messagebox.showerror("Error", "Falta Mesa")
        
        try:
            fecha = self.entry_fecha.get_date()
            hora = int(self.spin_hora.get()); minuto = int(self.spin_min.get())
            dt = datetime(fecha.year, fecha.month, fecha.day, hora, minuto)
            
            if not self.modo_edicion and dt < datetime.now():
                return messagebox.showerror("Error", "Fecha en el pasado")
        except: return messagebox.showerror("Error", "Fecha/Hora inválida")

        n_personas = int(self.spin_personas.get())
        cap_total = sum([self.mesas_actuales[i]['capacidad'] for i in indices_mesa])
        ids_mesas = [self.mesas_actuales[i]['id'] for i in indices_mesa]

        if cap_total < n_personas:
            return messagebox.showerror("Capacidad", f"Mesas ({cap_total}) insuficientes para {n_personas}")

        # 2. Preparar Datos para DB
        id_cliente = self.clientes_map[nombre_cli]
        id_empleado = self.empleados_map.get(self.combo_empleado.get())
        
        # Lógica de Negocio: Política
        id_estado = 1 # Pendiente
        id_pol = ReservaController.calcular_politica(n_personas, id_estado)

        # 3. Ejecución SQL
        if self.modo_edicion:
            # UPDATE
            sql = "UPDATE Reserva SET fecha_reserva=?, numero_personas=?, id_cliente=?, id_empleado=?, id_politica=?, id_estado_reserva=1 WHERE id_reserva=?"
            DatabaseManager.run_query(sql, (dt, n_personas, id_cliente, id_empleado, id_pol, self.id_reserva_seleccionada), commit=True)
            
            # Reset Mesas
            DatabaseManager.run_query("DELETE FROM Detalle_Reserva WHERE id_reserva=?", (self.id_reserva_seleccionada,), commit=True)
            id_reserva = self.id_reserva_seleccionada
            msg = "Reserva Actualizada"
        else:
            # INSERT
            sql = """
            SET NOCOUNT ON;
            INSERT INTO Reserva (fecha_reserva, numero_personas, id_cliente, id_empleado, id_estado_reserva, id_politica, id_restaurante)
            VALUES (?, ?, ?, ?, 1, ?, ?);
            SELECT SCOPE_IDENTITY();
            """
            id_reserva = DatabaseManager.run_query(sql, (dt, n_personas, id_cliente, id_empleado, id_pol, ReservaController.ID_RESTAURANTE), commit=True)
            msg = f"Reserva #{id_reserva} Creada"

        # Insertar Detalles
        if id_reserva:
            for m_id in ids_mesas:
                DatabaseManager.run_query("INSERT INTO Detalle_Reserva VALUES (?, ?, 0)", (id_reserva, m_id), commit=True)
            
            messagebox.showinfo("Éxito", msg)
            self.limpiar_formulario()
            self.cargar_monitor_reservas()
            self.verificar_disponibilidad()

    def preparar_edicion(self):
        if not self.id_reserva_seleccionada: return
        
        # Cargar datos de BD
        sql = "SELECT id_cliente, numero_personas, fecha_reserva, id_empleado FROM Reserva WHERE id_reserva=?"
        datos = DatabaseManager.run_query(sql, (self.id_reserva_seleccionada,), fetchone=True)
        
        if datos:
            self.modo_edicion = True
            self.btn_guardar.config(text="GUARDAR CAMBIOS", bg="#fd7e14")
            self.lbl_titulo.config(text=f"EDITANDO #{self.id_reserva_seleccionada}", fg="#fd7e14")
            
            # Setear campos
            try:
                nombre = [k for k, v in self.clientes_map.items() if v == datos[0]][0]
                self.combo_cliente.set(nombre)
            except: pass
            
            self.spin_personas.delete(0, tk.END); self.spin_personas.insert(0, datos[1])
            self.entry_fecha.set_date(datos[2])
            self.spin_hora.delete(0, tk.END); self.spin_hora.insert(0, datos[2].hour)
            self.spin_min.delete(0, tk.END); self.spin_min.insert(0, datos[2].minute)
            
            # Refrescar mesas disponibles para esa fecha histórica
            self.verificar_disponibilidad()

    def actualizar_estado(self, nuevo_estado):
        if not self.id_reserva_seleccionada: return
        
        # Obtener pax para recalcular política
        pax = DatabaseManager.run_query("SELECT numero_personas FROM Reserva WHERE id_reserva=?", (self.id_reserva_seleccionada,), fetchone=True)[0]
        id_pol = ReservaController.calcular_politica(pax, nuevo_estado)
        
        sql = "UPDATE Reserva SET id_estado_reserva=?, id_politica=? WHERE id_reserva=?"
        if DatabaseManager.run_query(sql, (nuevo_estado, id_pol, self.id_reserva_seleccionada), commit=True):
            self.cargar_monitor_reservas()
            self.verificar_disponibilidad()
            messagebox.showinfo("Info", "Estado Actualizado")

    def ver_detalles(self):
        if not self.id_reserva_seleccionada: return
        
        sql = """
        SELECT Rest.nombre, Rest.direccion, C.nombre + ' ' + C.apellido, C.cedula, C.telefono,
               ISNULL(P.descripcion, 'Estándar'), ISNULL(P.valor, 0), R.fecha_reserva, R.numero_personas, E.descripcion,
               ISNULL(Emp.nombre, 'Sin asignar')
        FROM Reserva R
        JOIN Restaurante Rest ON R.id_restaurante = Rest.id_restaurante
        JOIN Cliente C ON R.id_cliente = C.id_cliente
        JOIN Estado_Reserva E ON R.id_estado_reserva = E.id_estado_reserva
        LEFT JOIN Politica P ON R.id_politica = P.id_politica
        LEFT JOIN Empleado Emp ON R.id_empleado = Emp.id_empleado
        WHERE R.id_reserva = ?
        """
        d = DatabaseManager.run_query(sql, (self.id_reserva_seleccionada,), fetchone=True)
        
        if d:
            top = Toplevel()
            top.geometry("500x550"); top.title("Ficha Técnica")
            tk.Label(top, text="FICHA DE RESERVA", font=("Arial", 16, "bold"), pady=10).pack()
            
            # Helper para frames
            def crear_grupo(titulo):
                f = tk.LabelFrame(top, text=titulo, padx=10, pady=5, font=("Arial", 9, "bold"))
                f.pack(fill=tk.X, padx=10, pady=5)
                return f
            
            g_loc = crear_grupo("Ubicación")
            tk.Label(g_loc, text=f"Local: {d[0]}\nDirección: {d[1]}", justify=tk.LEFT).pack(anchor="w")
            
            g_cli = crear_grupo("Cliente")
            tk.Label(g_cli, text=f"Nombre: {d[2]}\nCédula: {d[3]} | Telf: {d[4]}", justify=tk.LEFT).pack(anchor="w")
            
            g_ops = crear_grupo("Operación")
            tk.Label(g_ops, text=f"Fecha: {d[7].strftime('%d/%m %H:%M')} | Pax: {d[8]}").pack(anchor="w")
            tk.Label(g_ops, text=f"Atendido por: {d[10]}", fg="gray").pack(anchor="w")
            tk.Label(g_ops, text=f"Estado: {d[9]}", font=("Arial", 10, "bold")).pack(anchor="w")
            
            g_fin = crear_grupo("Políticas y Pagos")
            color = "red" if d[6] > 0 else "green"
            tk.Label(g_fin, text=f"Política: {d[5]}").pack(anchor="w")
            tk.Label(g_fin, text=f"Costo: ${d[6]:.2f}", fg=color, font=("Arial", 11, "bold")).pack(anchor="w")
            
            tk.Button(top, text="Cerrar", command=top.destroy).pack(pady=10)

    def seleccionar_reserva(self, event):
        item = self.tree.focus()
        if self.tree.item(item)['values']:
            self.id_reserva_seleccionada = self.tree.item(item)['values'][0]

    def limpiar_formulario(self):
        self.modo_edicion = False
        self.id_reserva_seleccionada = None
        self.btn_guardar.config(text="CONFIRMAR", bg="#007bff")
        self.lbl_titulo.config(text="NUEVA RESERVA", fg="black")
        self.combo_cliente.set('')
        self.verificar_disponibilidad()

# Ejecución
if __name__ == "__main__":
    SistemaReservasUI()