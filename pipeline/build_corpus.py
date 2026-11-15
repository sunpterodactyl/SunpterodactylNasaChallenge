"""M1: build the Earth patch corpus and the Moon target patches.

Run from the repo root:  python pipeline/build_corpus.py

Earth: for every region in pipeline/data/regions.csv, draw 25 patch centres
jittered +-0.4 deg around the region centre (fixed seed) and read a 64 x 64,
500 m patch from Copernicus GLO-30 (area average). QC: cells that are NaN
(no tile) or exactly 0.0 (Copernicus sea) count as nodata; a patch with more
than 5 percent nodata is skipped, otherwise nodata cells get the patch mean.
A region keeps its patches only if at least 15 pass. One failed region never
stops the run.

Targets: Moon only (Mars deferred, see docs/DATA_NOTES.md). Read from the USGS
WMS at 256 x 256 and block-averaged 4 x 4 down to 64 x 64.

Writes pipeline/out/earth_patches.npz and pipeline/out/targets.npz.
"""

import csv
import time
import warnings
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import rasterio
import requests
from rasterio.io import MemoryFile
from rasterio.transform import from_bounds
from rasterio.warp import Resampling, reproject

from common import N, bbox

warnings.filterwarnings('ignore', category=rasterio.errors.NotGeoreferencedWarning)

HERE = Path(__file__).parent
OUT = HERE / 'out'
REGIONS_CSV = HERE / 'data' / 'regions.csv'

PATCHES_PER_REGION = 25
JITTER_DEG = 0.4
MAX_NODATA = 0.05
MIN_KEPT = 15
SEED = 42

STAC = 'https://planetarycomputer.microsoft.com/api/stac/v1'
SAS = 'https://planetarycomputer.microsoft.com/api/sas/v1/token/cop-dem-glo-30'
WMS = 'https://planetarymaps.usgs.gov/cgi-bin/mapserv?map=/maps/earth/moon_simp_cyl_elev.map'

TARGETS = [  # (id, name, body, lat, lon). Mars targets deferred: MOLA WMS layer is broken.
    ('marius_hills', 'Marius Hills', 'moon', 14.1, -56.7),
    ('taurus_littrow', 'Taurus-Littrow valley', 'moon', 20.2, 30.8),
    ('tycho_rim', 'Tycho crater', 'moon', -43.3, -11.4),
]


def retry(fn, tries=3, wait=3.0):
    for i in range(tries):
        try:
            return fn()
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(wait * (i + 1))


# ---------------------------------------------------------------- Earth

def region_patches(region, token, rng_seed):
    """Read and QC all patches for one region. Returns a dict; never raises."""
    name, lat0, lon0 = region['region'], float(region['lat']), float(region['lon'])
    t0 = time.time()
    rng = np.random.default_rng(rng_seed)
    centres = np.c_[lat0 + rng.uniform(-JITTER_DEG, JITTER_DEG, PATCHES_PER_REGION),
                    lon0 + rng.uniform(-JITTER_DEG, JITTER_DEG, PATCHES_PER_REGION)]
    boxes = [bbox(la, lo, 'earth') for la, lo in centres]
    union = [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]
    res = dict(region=name, kind=region['kind'], kept=[], skipped=0, error=None)
    try:
        items = retry(lambda: requests.post(f'{STAC}/search', timeout=60, json=dict(
            collections=['cop-dem-glo-30'], bbox=union, limit=100)).json()['features'])
        tiles = [rasterio.open(f'{it["assets"]["data"]["href"]}?{token}') for it in items]
        try:
            for i, ((la, lo), box) in enumerate(zip(centres, boxes)):
                z = np.full((N, N), np.nan, np.float32)
                for src in tiles:
                    b = src.bounds
                    if b.right <= box[0] or b.left >= box[2] or b.top <= box[1] or b.bottom >= box[3]:
                        continue
                    retry(lambda: reproject(rasterio.band(src, 1), z, src_nodata=src.nodata, dst_nodata=np.nan,
                                            dst_transform=from_bounds(*box, N, N), dst_crs=src.crs,
                                            resampling=Resampling.average, init_dest_nodata=False))
                bad = np.isnan(z) | (z == 0.0)
                frac = float(bad.mean())
                if frac > MAX_NODATA:
                    res['skipped'] += 1
                    continue
                if frac:
                    z[bad] = z[~bad].mean()
                res['kept'].append(dict(patch_id=f'{name}_{i:02d}', lat=float(la), lon=float(lo),
                                        nodata_frac=frac, z=z))
        finally:
            for src in tiles:
                src.close()
    except Exception as e:
        res['error'] = f'{type(e).__name__}: {e}'[:120]
    res['seconds'] = time.time() - t0
    return res


def build_earth():
    regions = list(csv.DictReader(REGIONS_CSV.open()))
    token = requests.get(SAS, timeout=30).json()['token']
    print(f'Earth: {len(regions)} regions x {PATCHES_PER_REGION} patches')
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda ir: region_patches(ir[1], token, SEED + ir[0]), enumerate(regions)))

    print(f'\n{"region":<22}{"kind":<10}{"kept":>5}{"skip":>5}{"relief p50 (m)":>16}{"time":>8}  status')
    patches, n_regions = [], 0
    for r in results:
        k = len(r['kept'])
        relief = np.median([np.ptp(np.percentile(p['z'], [5, 95])) for p in r['kept']]) if k else float('nan')
        if r['error']:
            status = f'FAILED {r["error"]}'
        elif k < MIN_KEPT:
            status = f'DROPPED (<{MIN_KEPT} patches)'
        else:
            status = 'ok'
            patches += r['kept']
            n_regions += 1
        print(f'{r["region"]:<22}{r["kind"]:<10}{k:>5}{r["skipped"]:>5}{relief:>16.0f}{r["seconds"]:>7.0f}s  {status}')
    print(f'\nKept {len(patches)} patches from {n_regions} regions.')
    if not patches:
        raise SystemExit('No Earth patches kept; nothing saved.')

    region_of = {r['region']: r['kind'] for r in results}
    np.savez_compressed(
        OUT / 'earth_patches.npz',
        z=np.stack([p['z'] for p in patches]).astype(np.float32),
        patch_id=np.array([p['patch_id'] for p in patches]),
        region=np.array([p['patch_id'].rsplit('_', 1)[0] for p in patches]),
        kind=np.array([region_of[p['patch_id'].rsplit('_', 1)[0]] for p in patches]),
        lat=np.array([p['lat'] for p in patches]),
        lon=np.array([p['lon'] for p in patches]),
        nodata_frac=np.array([p['nodata_frac'] for p in patches]),
        source=np.array('Copernicus DEM GLO-30 (Planetary Computer cop-dem-glo-30), area average to 500 m'),
    )
    print(f'Saved {OUT / "earth_patches.npz"}')


# ---------------------------------------------------------------- targets

def wms_patch(lat, lon, body):
    box = bbox(lat, lon, body)
    params = dict(SERVICE='WMS', VERSION='1.1.1', REQUEST='GetMap', LAYERS='LOLA_elev', STYLES='',
                  SRS='EPSG:4326', BBOX=','.join(f'{v:.6f}' for v in box),
                  WIDTH=4 * N, HEIGHT=4 * N, FORMAT='image/tiff')
    r = requests.get(WMS, params=params, timeout=90)
    r.raise_for_status()
    if 'tiff' not in r.headers.get('content-type', ''):
        raise RuntimeError(f'WMS returned {r.headers.get("content-type")}: {r.text[:200]}')
    with MemoryFile(r.content) as f, f.open() as d:
        hi = d.read(1).astype(np.float32)
    return hi.reshape(N, 4, N, 4).mean((1, 3))


def build_targets():
    print(f'\nTargets: {len(TARGETS)} (Moon only; Mars deferred)')
    rows = []
    for tid, name, body, lat, lon in TARGETS:
        t0 = time.time()
        try:
            z = retry(lambda: wms_patch(lat, lon, body))
        except Exception as e:
            print(f'  {tid:<16} FAILED {type(e).__name__}: {e}'[:160])
            continue
        if np.ptp(z) == 0:
            print(f'  {tid:<16} FAILED constant array ({z.flat[0]:.0f} m); not saved')
            continue
        print(f'  {tid:<16} min={z.min():.0f} max={z.max():.0f} relief p5-p95='
              f'{np.ptp(np.percentile(z, [5, 95])):.0f} m  {time.time() - t0:.1f}s')
        rows.append((tid, name, body, lat, lon, z))
    if not rows:
        raise SystemExit('No targets built; nothing saved.')
    np.savez_compressed(
        OUT / 'targets.npz',
        z=np.stack([r[5] for r in rows]).astype(np.float32),
        id=np.array([r[0] for r in rows]), name=np.array([r[1] for r in rows]),
        body=np.array([r[2] for r in rows]),
        lat=np.array([r[3] for r in rows]), lon=np.array([r[4] for r in rows]),
        source=np.array('USGS Astrogeology WMS LOLA_elev (planetarymaps.usgs.gov), 4x request block-averaged'),
    )
    print(f'Saved {OUT / "targets.npz"}')


if __name__ == '__main__':
    OUT.mkdir(exist_ok=True)
    build_targets()
    build_earth()
