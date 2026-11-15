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


# ---------------------------------------------------------------- SPEC section 6 features
# scipy is imported inside the functions: these run only in the pipeline.
# The runtime gets their outputs precomputed in backend/artifacts/model.npz.

TEXTURE_COLS = ('vrm', 'acr', 'rms_short', 'rms_long', 'hurst')
TEXTURE_LOG = (False, False, True, True, False)   # log-transform skewed columns


def aligned_profile(z):
    """Mean cross-section (length 48) taken across the dominant gradient axis."""
    from scipy import ndimage as ndi
    z = z - np.median(z)
    gy, gx = np.gradient(z)
    th = 0.5 * np.arctan2(2 * (gx * gy).sum(), (gx ** 2 - gy ** 2).sum())   # dominant gradient axis
    r = ndi.rotate(z, np.degrees(th), reshape=False, order=1, mode='nearest')
    return r[8:-8, 8:-8].mean(axis=0)


def features(z):
    gy, gx = np.gradient(z, GRID_M)
    s = np.degrees(np.arctan(np.hypot(gx, gy))).ravel()

    def rms(k):
        d = np.concatenate([(z[:, k:] - z[:, :-k]).ravel(), (z[k:] - z[:-k]).ravel()])
        return np.sqrt(np.mean(d ** 2)) + 1e-6

    r1, r3, r10 = rms(1), rms(3), rms(10)
    h = np.polyfit(np.log([1, 3, 10]), np.log([r1, r3, r10]), 1)[0]
    return dict(slope_p50=np.percentile(s, 50), slope_p90=np.percentile(s, 90),
                relief=np.ptp(np.percentile(z, [5, 95])), rms_short=r1, rms_long=r10, hurst=h)


def texture(z):
    from scipy import ndimage as ndi
    gy, gx = np.gradient(z, GRID_M)
    nz = 1 / np.sqrt(1 + gx ** 2 + gy ** 2)
    nx, ny = -gx * nz, -gy * nz
    k = np.ones((3, 3))
    sx, sy, sz = (ndi.convolve(a, k, mode='nearest') for a in (nx, ny, nz))
    vrm = (1 - np.sqrt(sx ** 2 + sy ** 2 + sz ** 2) / 9).mean()
    acr = np.sqrt(1 + gx ** 2 + gy ** 2).mean()      # surface/planar area ratio, approximate
    f = features(z)
    return np.array([vrm, acr, f['rms_short'], f['rms_long'], f['hurst']])


def patch_features(z):
    """Everything the model needs from one patch: profile, texture vector, magnitude pair."""
    z = np.asarray(z, dtype=np.float64)
    f = features(z)
    return aligned_profile(z), texture(z), np.array([f['relief'], f['slope_p90']])
