import random

def generar_semana_demo():
    # 1. Configuración Inicial (Base de Datos simulada)
    empleados = ["Carlos", "Laura", "Miguel", "Andrea", "Juan", "Sofía", "Diego", "Ana"]
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    turnos = ["Mañana", "Tarde", "Noche"]
    
    # Excepciones ingresadas por el administrador para esta semana
    excepciones = {
        ("Miércoles", "Carlos"): "Enfermo",
        ("Viernes", "Laura"): "Día libre pedido"
    }

    # 2. Contadores de Estado (El "Cerebro" de la Equidad)
    # Rastrean cuántos turnos lleva cada quien para balancear la carga
    turnos_totales = {emp: 0 for emp in empleados}
    turnos_noche = {emp: 0 for emp in empleados}
    
    # Rastrear el índice absoluto del último turno trabajado (0 a 20)
    # Esto es crucial para calcular matemáticamente las 8 horas de descanso
    ultimo_turno = {emp: -99 for emp in empleados} 
    
    calendario = {}
    indice_turno_actual = 0 # Contador absoluto (Ej: Lunes Mañana = 0, Lunes Tarde = 1...)

    # 3. Motor de Asignación
    for dia in dias:
        calendario[dia] = {}
        for turno in turnos:
            necesarios = 2
            asignados_este_turno = []
            candidatos_viables = []

            # PASO A: Filtrar quién PUEDE trabajar este turno
            for emp in empleados:
                # Regla 1: Excepciones (Vacaciones, médicas)
                if (dia, emp) in excepciones:
                    continue
                
                # Regla 2: Descanso Mínimo (No turnos consecutivos)
                # Si el turno actual menos su último turno es menor a 2, significa que 
                # trabajó el turno inmediatamente anterior. No tiene 8h de descanso.
                if (indice_turno_actual - ultimo_turno[emp]) < 2:
                    continue
                
                # Regla 3: Equidad de Noches (Máximo 2 por semana)
                if turno == "Noche" and turnos_noche[emp] >= 2:
                    continue
                
                candidatos_viables.append(emp)

            # PASO B: Ordenar por Equidad (Quién DEBE trabajar)
            # Mezclamos aleatoriamente primero para que, en caso de empate, 
            # no siempre se asignen en el mismo orden alfabético.
            random.shuffle(candidatos_viables)
            
            # Ordenamos priorizando a los que tienen MENOS turnos totales
            candidatos_viables.sort(key=lambda x: turnos_totales[x])

            # PASO C: Asignar a los 2 mejores candidatos
            for emp in candidatos_viables[:necesarios]:
                asignados_este_turno.append(emp)
                
                # Actualizar contadores de estado
                turnos_totales[emp] += 1
                if turno == "Noche":
                    turnos_noche[emp] += 1
                ultimo_turno[emp] = indice_turno_actual

            # Guardar en el calendario final
            calendario[dia][turno] = asignados_este_turno
            indice_turno_actual += 1

    return calendario, turnos_totales, turnos_noche

# Ejecución de prueba
calendario_generado, total_turnos, total_noches = generar_semana_demo()

# Impresión de resultados en consola (Simulación de la vista)
print("=== CALENDARIO GENERADO ===")
for dia, turnos in calendario_generado.items():
    print(f"\n{dia.upper()}")
    for nombre_turno, empleados_asignados in turnos.items():
        print(f"  {nombre_turno}: {', '.join(empleados_asignados)}")

print("\n=== MÉTRICAS DE EQUIDAD ===")
for emp in total_turnos.keys():
    print(f"{emp}: {total_turnos[emp]} turnos en total | {total_noches[emp]} noches")