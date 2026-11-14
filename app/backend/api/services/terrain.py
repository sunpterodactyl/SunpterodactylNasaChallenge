from backend.api.db import get_terrain_grid


def build_terrain(site_id: str) -> dict:
    return {'grid': get_terrain_grid(site_id)}
