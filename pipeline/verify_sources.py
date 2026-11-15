"""M0: check that each data source returns a plausible 64 x 64 patch at 500 m.

Run from the repo root:  python pipeline/verify_sources.py

Prints min/max/std, timing and a PASS/FAIL verdict per source, runs the
specific checks behind each UNVERIFIED item in SPEC section 4, and saves a
hillshade PNG of every patch to pipeline/out/. It never substitutes one
source for another: the Astropedia fallback is only probed and reported.
Findings are written up by hand in docs/DATA_NOTES.md.
"""

import time
import warnings
from pathlib import Path

import numpy as np
import rasterio
import requests
from rasterio.io import MemoryFile
from rasterio.transform import from_bounds
from rasterio.warp import Resampling, reproject

from common import N, bbox, hillshade

# WMS TIFFs and the hillshade PNGs carry no geotransform; that is expected here.
warnings.filterwarnings('ignore', category=rasterio.errors.NotGeoreferencedWarning)

OUT = Path(__file__).parent / 'out'

STAC = 'https://planetarycomputer.microsoft.com/api/stac/v1'
SAS = 'https://planetarycomputer.microsoft.com/api/sas/v1/token/cop-dem-glo-30'

WMS_HOSTS = ['http://wms.wr.usgs.gov', 'https://planetarymaps.usgs.gov']
WMS_MAPS = {
    'moon': ('/cgi-bin/mapserv?map=/maps/earth/moon_simp_cyl_elev.map', 'LOLA_elev'),
    'mars': ('/cgi-bin/mapserv?map=/maps/mars/mars_simp_cyl_elev.map', 'MOLA_elev'),
}
MOLA_ASTROPEDIA = ('https://planetarymaps.usgs.gov/mosaic/'
                   'Mars_MGS_MOLA_DEM_mosaic_global_463m.tif')

# Documented global elevation ranges (metres), used only as a sanity bound.
PLAUSIBLE = {'earth': (-450, 8900), 'moon': (-9200, 10800), 'mars': (-8300, 21300)}


# ---------------------------------------------------------------- helpers

def report(name, body, z, seconds, units):
    """Print stats and a verdict; save a hillshade. Returns True if plausible."""
    lo, hi = PLAUSIBLE[body]
    finite = z[np.isfinite(z)]
    problems = []
    if finite.size < z.size:
        problems.append(f'{z.size - finite.size} nodata cells')
    if finite.size == 0 or np.ptp(finite) == 0:
        problems.append('array is constant (no relief)')
    elif finite.min() < lo or finite.max() > hi:
        problems.append(f'values outside documented range {lo}..{hi}')
    ok = not any('constant' in p or 'outside' in p for p in problems)
    print(f'  {name}: shape={z.shape} min={np.nanmin(z):.0f} max={np.nanmax(z):.0f} '
          f'std={np.nanstd(z):.1f} units={units} time={seconds:.1f}s')
    print(f'  verdict: {"PASS" if ok else "FAIL"}' + (f' ({"; ".join(problems)})' if problems else ''))
    OUT.mkdir(exist_ok=True)
    png = OUT / f'm0_{name}.png'
    shade = hillshade(np.nan_to_num(z, nan=float(np.nanmean(z)) if finite.size else 0.0))
    with rasterio.open(png, 'w', driver='PNG', width=N, height=N, count=1, dtype='uint8') as d:
        d.write(shade, 1)
    print(f'  hillshade: {png.relative_to(Path.cwd()) if png.is_relative_to(Path.cwd()) else png}')
    return ok


def wms_get(host, body, box, w=N, h=N, layer=None):
    path, default_layer = WMS_MAPS[body]
    params = dict(SERVICE='WMS', VERSION='1.1.1', REQUEST='GetMap', LAYERS=layer or default_layer,
                  STYLES='', SRS='EPSG:4326', BBOX=','.join(f'{v:.6f}' for v in box),
                  WIDTH=w, HEIGHT=h, FORMAT='image/tiff')
    r = requests.get(host + path, params=params, timeout=60)
    r.raise_for_status()
    if 'tiff' not in r.headers.get('content-type', ''):
        raise RuntimeError(f'WMS returned {r.headers.get("content-type")}: {r.text[:200]}')
    with MemoryFile(r.content) as f, f.open() as d:
        return d.read(1).astype(np.float32), d.dtypes[0]


def pick_wms_host():
    print('\n[WMS endpoint reachability]')
    chosen = None
    for host in WMS_HOSTS:
        t = time.time()
        try:
            requests.get(host + WMS_MAPS['moon'][0], params=dict(SERVICE='WMS', REQUEST='GetCapabilities'),
                         timeout=20).raise_for_status()
            print(f'  {host}: OK ({time.time() - t:.1f}s)')
            chosen = chosen or host
        except Exception as e:
            print(f'  {host}: FAILED ({type(e).__name__})')
    return chosen


# ---------------------------------------------------------------- sources

def copernicus(lat, lon, name):
    print(f'\n[Copernicus GLO-30] {name} ({lat}, {lon})')
    box = bbox(lat, lon, 'earth')
    t = time.time()
    items = requests.post(f'{STAC}/search', json=dict(collections=['cop-dem-glo-30'], bbox=list(box)),
                          timeout=60).json()['features']
    token = requests.get(SAS, timeout=30).json()['token']
    keys = sorted({k for it in items for k in it['assets']})
    print(f'  {len(items)} tile(s): {[it["id"] for it in items]}  asset keys: {keys}')
    z = np.full((N, N), np.nan, np.float32)
    dst_transform = from_bounds(*box, N, N)
    for it in items:
        with rasterio.open(f'{it["assets"]["data"]["href"]}?{token}') as src:
            units = src.units[0] or '(not set in file)'
            reproject(rasterio.band(src, 1), z, src_nodata=src.nodata, dst_nodata=np.nan,
                      dst_transform=dst_transform, dst_crs=src.crs, resampling=Resampling.average,
                      init_dest_nodata=False)
            print(f'  tile crs={src.crs} res={src.res} nodata={src.nodata} dtype={src.dtypes[0]}')
    return report(name, 'earth', z, time.time() - t, units)


def wms_target(host, body, lat, lon, name):
    print(f'\n[USGS WMS {WMS_MAPS[body][1]}] {name} ({lat}, {lon}) via {host}')
    t = time.time()
    z, dtype = wms_get(host, body, bbox(lat, lon, body))
    print(f'  dtype={dtype}')
    return report(name, body, z, time.time() - t, 'm (see unit check)'), z


def check_wms_units(host):
    """LOLA_elev_uint16 is documented as metres + 9130. If Int16 is metres the difference is ~9130."""
    print('\n[Check] WMS Int16 units = metres (LOLA_elev_uint16 - LOLA_elev should be ~9130)')
    box = bbox(14.1, -56.7, 'moon')
    a, _ = wms_get(host, 'moon', box)
    b, _ = wms_get(host, 'moon', box, layer='LOLA_elev_uint16')
    d = b - a
    print(f'  difference: median={np.median(d):.0f} min={d.min():.0f} max={d.max():.0f}')


def check_wms_resampling(host):
    """Ask for 64 px and 256 px of the same box; compare the 64 px reply with 4x4 means vs samples."""
    print('\n[Check] WMS resampling when requesting fewer pixels than native (LOLA, Marius Hills)')
    box = bbox(14.1, -56.7, 'moon')
    lo, _ = wms_get(host, 'moon', box)
    hi, _ = wms_get(host, 'moon', box, w=4 * N, h=4 * N)
    blocks = hi.reshape(N, 4, N, 4)
    cands = {'block mean': blocks.mean((1, 3))}
    for i in range(4):
        cands[f'nearest (offset {i})'] = hi[i::4, i::4]
    for k, v in cands.items():
        print(f'  mean |64px - {k}| = {np.abs(lo - v).mean():.2f} m')


def check_lon_convention(host, body, lat, lon):
    other = lon + 360 if lon < 0 else lon - 360
    print(f'\n[Check] {body} longitude convention: lon {lon} vs {other}')
    a, _ = wms_get(host, body, bbox(lat, lon, body))
    b, _ = wms_get(host, body, bbox(lat, other, body))
    for l, z in ((lon, a), (other, b)):
        print(f'  lon {l:7.1f}: min={z.min():.0f} max={z.max():.0f} std={z.std():.1f}')
    if np.ptp(a) == 0 and np.ptp(b) == 0:
        print('  inconclusive: both replies are constant')


def check_mola_global(host):
    print('\n[Check] MOLA_elev over the whole planet (is the layer serving real data?)')
    z, _ = wms_get(host, 'mars', (-180, -90, 180, 90), w=360, h=180)
    print(f'  global 360x180: min={z.min():.0f} max={z.max():.0f} unique values={len(np.unique(z))}')


def probe_astropedia_mola(lat, lon, name):
    """Fallback probe only. Reports what the Astropedia mosaic returns; nothing downstream uses it."""
    print(f'\n[Fallback probe, NOT used] Astropedia MOLA 463 m mosaic, {name} ({lat}, {lon})')
    t = time.time()
    with rasterio.open('/vsicurl/' + MOLA_ASTROPEDIA) as src:
        print(f'  file: shape={src.shape} dtype={src.dtypes[0]} nodata={src.nodata} '
              f'x range={src.bounds.left:.0f}..{src.bounds.right:.0f} m')
        # Projected equirectangular metres on the Mars sphere, centred on lon 0 -> -180..180 convention.
        w, s, e, n = bbox(lat, lon, 'mars')
        k = np.radians(1) * src.crs.to_dict().get('R', 3396190.0)
        box = (w * k, s * k, e * k, n * k)
        z = np.full((N, N), np.nan, np.float32)
        reproject(rasterio.band(src, 1), z, src_nodata=src.nodata, dst_nodata=np.nan,
                  dst_transform=from_bounds(*box, N, N), dst_crs=src.crs, resampling=Resampling.average)
    report(f'{name}_astropedia', 'mars', z, time.time() - t, 'm')


# ---------------------------------------------------------------- main

def main():
    results = {}
    try:
        results['earth atacama'] = copernicus(-24.5, -69.2, 'atacama')
    except Exception as e:
        print(f'  FAILED: {type(e).__name__}: {e}')
        results['earth atacama'] = False

    host = pick_wms_host()
    if host is None:
        print('\nNo WMS endpoint reachable. Stop: see SPEC section 4 fallback.')
        return
    for body, lat, lon, name in (('moon', 14.1, -56.7, 'marius_hills'), ('mars', 18.4, 77.5, 'jezero_delta')):
        try:
            results[f'{body} {name}'], _ = wms_target(host, body, lat, lon, name)
        except Exception as e:
            print(f'  FAILED: {type(e).__name__}: {e}')
            results[f'{body} {name}'] = False

    for check in (lambda: check_wms_units(host),
                  lambda: check_wms_resampling(host),
                  lambda: check_lon_convention(host, 'moon', 14.1, -56.7),
                  lambda: check_lon_convention(host, 'mars', 18.4, 77.5),
                  lambda: check_mola_global(host),
                  lambda: probe_astropedia_mola(18.4, 77.5, 'jezero_delta')):
        try:
            check()
        except Exception as e:
            print(f'  FAILED: {type(e).__name__}: {e}')

    print('\n[Summary]')
    for k, ok in results.items():
        print(f'  {"PASS" if ok else "FAIL"}  {k}')
    if not all(results.values()):
        print('\nAt least one source failed. Stop and report; do not substitute data silently.')


if __name__ == '__main__':
    main()
