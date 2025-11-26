from datetime import timedelta
from data.database import DatabaseManager
from config.settings import ID_RESTAURANTE_ACTUAL, COLOR_DISPONIBLE, COLOR_OCUPADA, COLOR_RESERVADA

class ReservaController:
    
    @staticmethod
    def calcular_politica(n_personas, id_estado):
        if id_estado == 3: return 1 # Multa
        if n_personas > 10: return 2 # Evento
        return 3 # Estándar

    @staticmethod
    def obtener_mesas_disponibles(fecha_filtro=None, id_reserva_ignorar=None):
        # 1. Traer mesas (NOMBRES NUEVOS: SGR_M_Mesa, idMesa, Nmesa)
        sql = """
        SELECT idMesa, Nmesa, capacidad, idEstadomesa 
        FROM SGR_M_Mesa 
        WHERE idRestaurante = ?
        ORDER BY Nmesa ASC
        """
        todas = DatabaseManager.run_query(sql, (ID_RESTAURANTE_ACTUAL,), fetchall=True)
        
        mapa_prioridad_visual = {} 

        if fecha_filtro:
            inicio = fecha_filtro - timedelta(hours=1, minutes=59)
            fin = fecha_filtro + timedelta(hours=1, minutes=59)
            
            # NOMBRES NUEVOS: SGR_T_DetalleReserva, SGR_T_Reserva
            sql_ocup = """
            SELECT DISTINCT DR.idMesa, R.idEstadoreserva
            FROM SGR_T_DetalleReserva DR
            JOIN SGR_T_Reserva R ON DR.idReserva = R.idReserva
            WHERE R.idEstadoreserva IN (1, 2, 4) 
            AND R.fechareserva BETWEEN ? AND ?
            """
            params = [inicio, fin]
            
            if id_reserva_ignorar:
                sql_ocup += " AND R.idReserva != ?"
                params.append(id_reserva_ignorar)

            ocupadas_raw = DatabaseManager.run_query(sql_ocup, tuple(params), fetchall=True)
            
            for row in ocupadas_raw:
                id_m = row[0]
                estado_bd = row[1]
                
                nivel_actual = mapa_prioridad_visual.get(id_m, 0)
                nivel_nuevo = 0
                if estado_bd in [1, 2]: nivel_nuevo = 1
                elif estado_bd == 4: nivel_nuevo = 2
                
                if nivel_nuevo > nivel_actual:
                    mapa_prioridad_visual[id_m] = nivel_nuevo

        resultado = []
        for m in todas:
            id_m, num, cap, _ = m
            nivel = mapa_prioridad_visual.get(id_m, 0)
            
            estilo = COLOR_DISPONIBLE
            txt = "(Disp)"

            if nivel == 2:
                estilo = COLOR_OCUPADA; txt = "(OCUPADA)"
            elif nivel == 1:
                estilo = COLOR_RESERVADA; txt = "(RESERVADA)"

            resultado.append({
                'id': id_m,
                'texto': f"{num} - Cap: {cap} p. {txt}",
                'capacidad': cap,
                'estilo': estilo
            })
        return resultado