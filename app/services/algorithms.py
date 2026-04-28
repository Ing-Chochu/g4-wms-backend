import logging

logger = logging.getLogger("WMS_Algorithms")

# Matriz virtual del almacén (3x3 para pruebas rápidas)
# 0 = Vacío, 1 = Ocupado
warehouse_grid = [
    [0, 0, 0],
    [0, 1, 0],
    [0, 0, 0]
]

def find_first_empty_slot_fifo():
    """
    Simula la asignación FIFO buscando el primer hueco disponible 
    recorriendo la matriz por filas.
    """
    for y, row in enumerate(warehouse_grid):
        for x, status in enumerate(row):
            if status == 0:
                logger.info(f"📍 Posición FIFO asignada: X={x}, Y={y}")
                return {"x": x, "y": y}
    
    logger.warning("⚠️ Almacén lleno. No hay posiciones FIFO disponibles.")
    return None

def calculate_a_star_route(start: dict, end: dict):
    """
    Mock (simulación) del algoritmo A* para el entregable.
    En la vida real, aquí iría la heurística (Distancia Manhattan).
    """
    logger.info(f"🗺️ Calculando ruta A* desde {start} hasta {end}")
    
    # Ruta simulada: Avanza en X y luego en Y
    route = [
        {"x": start["x"], "y": start["y"]},
        {"x": end["x"], "y": start["y"]},
        {"x": end["x"], "y": end["y"]}
    ]
    
    return route