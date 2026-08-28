import streamlit as st
import pandas as pd
import random
import io
import sqlite3 # NUEVO: La base de datos integrada de Python

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Gestor de Turnos Estación", layout="wide")

# --- 1. MOTOR DE BASE DE DATOS (SQLite) ---
def inicializar_bd():
    # Crea el archivo 'estacion.db' si no existe y se conecta
    conexion = sqlite3.connect('estacion.db')
    cursor = conexion.cursor()
    # Crea la tabla de empleados
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS empleados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE,
            activo BOOLEAN NOT NULL CHECK (activo IN (0, 1))
        )
    ''')
    # Si la tabla está vacía, inserta los datos de prueba iniciales
    cursor.execute('SELECT COUNT(*) FROM empleados')
    if cursor.fetchone()[0] == 0:
        empleados_demo = [("Carlos", 1), ("Laura", 1), ("Miguel", 1), ("Andrea", 1), 
                          ("Juan", 1), ("Sofía", 1), ("Diego", 1), ("Ana", 1)]
        cursor.executemany('INSERT INTO empleados (nombre, activo) VALUES (?, ?)', empleados_demo)
    conexion.commit()
    conexion.close()

def obtener_empleados(solo_activos=True):
    conexion = sqlite3.connect('estacion.db')
    if solo_activos:
        df = pd.read_sql_query('SELECT nombre FROM empleados WHERE activo = 1', conexion)
        conexion.close()
        return df['nombre'].tolist()
    else:
        df = pd.read_sql_query('SELECT id, nombre, activo FROM empleados', conexion)
        conexion.close()
        return df

def agregar_empleado(nombre):
    conexion = sqlite3.connect('estacion.db')
    cursor = conexion.cursor()
    try:
        cursor.execute('INSERT INTO empleados (nombre, activo) VALUES (?, 1)', (nombre.strip(),))
        conexion.commit()
        exito = True
    except sqlite3.IntegrityError:
        exito = False # Falla si el nombre ya existe
    conexion.close()
    return exito

def cambiar_estado_empleado(id_emp, estado_actual):
    nuevo_estado = 0 if estado_actual == 1 else 1
    conexion = sqlite3.connect('estacion.db')
    cursor = conexion.cursor()
    cursor.execute('UPDATE empleados SET activo = ? WHERE id = ?', (nuevo_estado, id_emp))
    conexion.commit()
    conexion.close()

# Ejecutamos la inicialización al arrancar la app
inicializar_bd()

# --- 2. LÓGICA DEL ALGORITMO ---
def generar_turnos(excepciones_ui, lista_empleados):
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    turnos = ["Mañana", "Tarde", "Noche"]
    
    turnos_totales = {emp: 0 for emp in lista_empleados}
    turnos_noche = {emp: 0 for emp in lista_empleados}
    ultimo_turno = {emp: -99 for emp in lista_empleados} 
    
    datos_tabla = []
    indice_turno_actual = 0 

    for dia in dias:
        fila_dia = {"Día": dia}
        trabajaron_hoy = [] # Registro estricto del día
        
        for turno in turnos:
            asignados_este_turno = []
            
            # Separamos en dos grupos para priorizar
            candidatos_ideales = []
            candidatos_emergencia = [] 
            
            for emp in lista_empleados:
                # Reglas estrictas e inquebrantables de salud y novedades
                if (dia, emp) in excepciones_ui: continue
                if emp in trabajaron_hoy: continue
                if (indice_turno_actual - ultimo_turno[emp]) < 2: continue # Mínimo 8h descanso
                
                # Regla flexible (Límite de 2 noches)
                if turno == "Noche" and turnos_noche[emp] >= 2:
                    candidatos_emergencia.append(emp) # Pasan a la banca de reserva
                else:
                    candidatos_ideales.append(emp) # Cumplen todo perfecto

            # Ordenar ambos grupos priorizando a los que tienen menos horas
            random.shuffle(candidatos_ideales)
            candidatos_ideales.sort(key=lambda x: turnos_totales[x])
            
            random.shuffle(candidatos_emergencia)
            candidatos_emergencia.sort(key=lambda x: turnos_totales[x])

            # PLAN A: Intentar llenar con los ideales
            candidatos_viables = candidatos_ideales.copy()
            
            # PLAN B: Si no hay 2 ideales, sacamos de la banca de emergencia (rompen regla de noche)
            if len(candidatos_viables) < 2:
                faltantes = 2 - len(candidatos_viables)
                candidatos_viables.extend(candidatos_emergencia[:faltantes])

            # PLAN C: (Caso catastrófico) Si aún no hay 2 personas, alguien dobla turno (Mañana y Noche)
            if len(candidatos_viables) < 2:
                emergencia_extrema = [e for e in lista_empleados if e not in candidatos_viables 
                                      and (dia, e) not in excepciones_ui 
                                      and (indice_turno_actual - ultimo_turno[e]) >= 2] # Garantiza las 8h de descanso
                random.shuffle(emergencia_extrema)
                faltantes = 2 - len(candidatos_viables)
                candidatos_viables.extend(emergencia_extrema[:faltantes])

            # Asignación final en la base de datos temporal
            for emp in candidatos_viables[:2]: 
                asignados_este_turno.append(emp)
                turnos_totales[emp] += 1
                if turno == "Noche": turnos_noche[emp] += 1
                ultimo_turno[emp] = indice_turno_actual
                trabajaron_hoy.append(emp)

            # Evitar el fallo visual si ocurre un imposible matemático
            if len(asignados_este_turno) == 2:
                fila_dia[turno] = " y ".join(asignados_este_turno)
            elif len(asignados_este_turno) == 1:
                fila_dia[turno] = f"{asignados_este_turno[0]} (FALTA 1)"
            else:
                fila_dia[turno] = "TURNO VACÍO"
                
            indice_turno_actual += 1
            
        datos_tabla.append(fila_dia)
    return pd.DataFrame(datos_tabla), turnos_totales, turnos_noche
# ==========================================
# PESTAÑA 1: GENERACIÓN DE TURNOS
# ==========================================
with tab_turnos:
    st.markdown("Genera horarios equitativos utilizando la base de datos de empleados activos.")
    empleados_activos = obtener_empleados(solo_activos=True)
    
    col_izquierda, col_derecha = st.columns([1, 3])

    with col_izquierda:
        st.header("🛠️ Panel de Novedades")
        opciones_select = ["Ninguno"] + empleados_activos
        emp_excepcion = st.selectbox("Empleado con novedad:", opciones_select)
        dia_excepcion = st.selectbox("Día que no asiste:", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"])
        
        generar = st.button("Generar Semana 🚀", type="primary")

    with col_derecha:
        if generar:
            if len(empleados_activos) < 4:
                st.error("⚠️ No hay suficientes empleados activos en la base de datos para cubrir los turnos. Ve a Gestión de Personal.")
            else:
                excepciones_activas = []
                if emp_excepcion != "Ninguno":
                    excepciones_activas.append((dia_excepcion, emp_excepcion))
                    st.warning(f"Excepción: {emp_excepcion} no trabajará el {dia_excepcion}.")
                
                tabla_resultados, metricas_totales, metricas_noches = generar_turnos(excepciones_activas, empleados_activos)
                
                st.subheader("📅 Calendario Semanal Generado")
                st.dataframe(tabla_resultados, use_container_width=True, hide_index=True)
                
                # Botón de Excel
                buffer_excel = io.BytesIO()
                with pd.ExcelWriter(buffer_excel, engine='openpyxl') as writer:
                    tabla_resultados.to_excel(writer, index=False, sheet_name='Turnos')
                    for col in writer.sheets['Turnos'].columns:
                        col_letra = col[0].column_letter
                        max_len = max([len(str(c.value)) for c in col] + [5])
                        writer.sheets['Turnos'].column_dimensions[col_letra].width = max_len + 2

                st.download_button(label="📥 Exportar a Excel", data=buffer_excel.getvalue(),
                                   file_name="Turnos_Semana.xlsx", 
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                
                st.divider()
                st.subheader("📊 Auditoría de Carga (Equidad)")
                cols_metricas = st.columns(4)
                for i, emp in enumerate(empleados_activos):
                    cols_metricas[i % 4].metric(label=f"👷 {emp}", value=f"{metricas_totales[emp]} turnos", delta=f"{metricas_noches[emp]} noches", delta_color="off")
        else:
            st.info("👈 Configura las excepciones y presiona 'Generar Semana'.")

# ==========================================
# PESTAÑA 2: GESTIÓN DE PERSONAL
# ==========================================
with tab_personal:
    st.header("Base de Datos del Equipo")
    st.markdown("Agrega nuevos isleros o retira a los que ya no están.")
    
    col_add, col_list = st.columns([1, 2])
    
    with col_add:
        st.subheader("➕ Nuevo Empleado")
        nuevo_nombre = st.text_input("Nombre completo:")
        if st.button("Guardar Empleado"):
            if nuevo_nombre:
                if agregar_empleado(nuevo_nombre):
                    st.success(f"'{nuevo_nombre}' agregado a la base de datos.")
                    st.rerun() # Recarga la app para actualizar la tabla
                else:
                    st.error("Ese nombre ya existe en la base de datos.")
            else:
                st.warning("Debes escribir un nombre.")
                
    with col_list:
        st.subheader("📋 Plantilla Actual")
        df_personal = obtener_empleados(solo_activos=False)
        
        # Mostramos cada empleado con un botón para activar/desactivar
        for index, row in df_personal.iterrows():
            col_nombre, col_estado, col_accion = st.columns([3, 1, 1])
            col_nombre.write(f"👤 **{row['nombre']}**")
            
            if row['activo'] == 1:
                col_estado.success("Activo")
                if col_accion.button("Desactivar", key=f"btn_{row['id']}"):
                    cambiar_estado_empleado(row['id'], 1)
                    st.rerun()
            else:
                col_estado.error("Inactivo")
                if col_accion.button("Activar", key=f"btn_{row['id']}"):
                    cambiar_estado_empleado(row['id'], 0)
                    st.rerun()
