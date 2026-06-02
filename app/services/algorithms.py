import logging

logger = logging.getLogger("WMS_Algorithms")

# Warehouse configuration (5 columns x 4 rows)
MAX_COLS = 5
MAX_ROWS = 4

def find_first_empty_slot_fifo(occupied_positions: list):
    """
    Finds the first available slot by rows using real DB data.
    occupied_positions: List of dicts [{"x": val, "y": val}, ...]
    """
    # Create a set for O(1) lookups
    occupied_set = {(p["x"], p["y"]) for p in occupied_positions}

    for y in range(MAX_ROWS):
        for x in range(MAX_COLS):
            if (x, y) not in occupied_set:
                logger.info(f"Position assigned: X={x}, Y={y}")
                return {"x": x, "y": y}
    
    logger.warning("Warehouse full. No FIFO slots available.")
    return None

def calculate_a_star_route(start: dict, end: dict):
    """
    A* Route calculation (Simplified).
    """
    logger.info(f"Calculating route from {start} to {end}")
    
    route = [
        {"x": start["x"], "y": start["y"]},
        {"x": end["x"], "y": start["y"]},
        {"x": end["x"], "y": end["y"]}
    ]
    
    return route