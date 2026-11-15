"""Shared geometry and feature code, imported by both pipeline/ and backend/.

Keep this file numpy-only (scipy allowed only inside functions that the
runtime never calls) so training and serving use identical code.
"""

import numpy as np

GRID_M = 500   # patch spacing in metres (SPEC section 5)
N = 64         # patch is N x N samples -> 32 km square

RADIUS_M = {
    'earth': 6371008.8,
    'moon': 1737400.0,
    'mars': 3396190.0,
}


def bbox(lat, lon, body, n=N, grid_m=GRID_M):
    """(west, south, east, north) in degrees for an n x n patch centred on lat, lon.

    Degree size comes from the body radius; longitude width grows with
    1/cos(lat) so the patch stays square on the ground.
    """
    half_m = n * grid_m / 2
    dlat = np.degrees(half_m / RADIUS_M[body])
    dlon = dlat / np.cos(np.radians(lat))
    return (lon - dlon, lat - dlat, lon + dlon, lat + dlat)


def hillshade(z, grid_m=GRID_M, azimuth=315.0, altitude=45.0):
    """Lambertian hillshade in 0..255 (uint8), north-up array."""
    gy, gx = np.gradient(z.astype(float), grid_m)
    slope = np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(-gx, gy)
    az, alt = np.radians(azimuth), np.radians(altitude)
    shade = np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect)
    return (np.clip(shade, 0, 1) * 255).astype(np.uint8)
