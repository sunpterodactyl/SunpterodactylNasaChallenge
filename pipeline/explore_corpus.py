"""Exploration corpus: bare-terrain Earth patches OUTSIDE the curated regions.

Run from the repo root:  python pipeline/explore_corpus.py [--refresh-mask]

Stage 1 (cached in pipeline/out/bare_cells.npz): read every ESA WorldCover
2021 (v200) tile at its coarsest overview (~500 m samples) and compute, for
each 0.25 deg cell, the share of land that is "bare / sparse vegetation"
(class 60) or "moss and lichen" (class 100). WorldCover covers 60S-83N, so
Antarctica is not explored.

Stage 2: keep cells that are >= 95% land and >= 80% bare, drop cells within
1 deg of a curated region centre, spread the sample (at most 2 cells per 5 deg
block, seed 7, cap 1500), and read a 64 x 64, 500 m Copernicus patch at each
cell centre with the same QC as build_corpus.py.

Writes pipeline/out/explore_patches.npz.
"""

import csv
import sys
import time
import warnings
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import rasterio
import requests
from rasterio.enums import Resampling

from build_corpus import REGIONS_CSV, SAS, STAC
from common import N, bbox

warnings.filterwarnings('ignore', category=rasterio.errors.NotGeoreferencedWarning)

HERE = Path(__file__).parent
OUT = HERE / 'out'
MASK = OUT / 'bare_cells.npz'

WC_SAS = 'https://planetarycomputer.microsoft.com/api/sas/v1/token/esa-worldcover'
CELL = 0.25           # deg
TILE = 3.0            # WorldCover tile size, deg
READ_PX = 600         # samples per tile side (uses the 1/64 overview)
BARE = (60, 100)
MIN_LAND, MIN_BARE = 0.95, 0.80
KNOWN_RADIUS_DEG = 1.0
PER_BLOCK, BLOCK_DEG, CAP, SEED = 2, 5.0, 1500, 7
MAX_NODATA = 0.05


def retry(fn, tries=3, wait=3.0):
    for i in range(tries):
        try:
            return fn()
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(wait * (i + 1))


# ---------------------------------------------------------------- stage 1

def worldcover_items():
    body = dict(collections=['esa-worldcover'], limit=1000,
                query={'esa_worldcover:product_version': {'eq': '2.0.0'}})
    items, url = [], f'{STAC}/search'
    while url:
        page = retry(lambda: requests.post(url, json=body, timeout=120).json())
        items += page['features']
        nxt = next((ln for ln in page.get('links', []) if ln.get('rel') == 'next'), None)
        url, body = (nxt['href'], nxt.get('body', body)) if nxt else (None, None)
    return items


def tile_cells(item, token):
    """(lat_centres, lon_centres, land_frac, bare_frac) for the 12 x 12 cells of one tile."""
    with rasterio.open(f'{item["assets"]["map"]["href"]}?{token}') as d:
        a = d.read(1, out_shape=(READ_PX, READ_PX), resampling=Resampling.nearest)
        west, north = d.bounds.left, d.bounds.top
    k = int(TILE / CELL)
    b = a.reshape(k, READ_PX // k, k, READ_PX // k)
    valid = (b != 0).mean((1, 3))
    land = ((b != 0) & (b != 80)).mean((1, 3))
    bare = np.isin(b, BARE).mean((1, 3))
    land_frac = np.where(valid > 0, land, 0)
    bare_frac = np.where(land > 0, bare / np.maximum(land, 1e-9), 0)
    lat = north - (np.arange(k) + 0.5) * CELL
    lon = west + (np.arange(k) + 0.5) * CELL
    LA, LO = np.meshgrid(lat, lon, indexing='ij')
    return LA.ravel(), LO.ravel(), land_frac.ravel(), bare_frac.ravel()


def build_mask():
    items = worldcover_items()
    token = requests.get(WC_SAS, timeout=30).json()['token']
    print(f'Stage 1: {len(items)} WorldCover tiles at ~{TILE / READ_PX * 111:.1f} km sampling')
    t0, done, failed = time.time(), [0], []

    def work(it):
        try:
            r = retry(lambda: tile_cells(it, token))
        except Exception as e:
            failed.append((it['id'], f'{type(e).__name__}: {e}'[:100]))
            r = None
        done[0] += 1
        if done[0] % 250 == 0:
            print(f'  {done[0]}/{len(items)} tiles, {time.time() - t0:.0f}s')
        return r

    with ThreadPoolExecutor(max_workers=12) as pool:
        res = [r for r in pool.map(work, items) if r is not None]
    lat, lon, land, bare = (np.concatenate([r[i] for r in res]) for i in range(4))
    np.savez_compressed(MASK, lat=lat, lon=lon, land=land, bare=bare)
    print(f'  {len(res)} tiles read, {len(failed)} failed, {time.time() - t0:.0f}s')
    for fid, err in failed[:10]:
        print(f'    FAILED {fid}: {err}')
    if len(failed) > 0.02 * len(items):
        raise SystemExit('More than 2% of WorldCover tiles failed. Stop and report.')


# ---------------------------------------------------------------- stage 2

def pick_cells():
    m = np.load(MASK)
    ok = (m['land'] >= MIN_LAND) & (m['bare'] >= MIN_BARE)
    lat, lon, bare = m['lat'][ok], m['lon'][ok], m['bare'][ok]
    print(f'Stage 2: {ok.sum()} of {len(ok)} cells are >= {MIN_LAND:.0%} land and >= {MIN_BARE:.0%} bare')
    seeds = [(float(r['lat']), float(r['lon'])) for r in csv.DictReader(REGIONS_CSV.open())]
    near = np.zeros(len(lat), bool)
    for la, lo in seeds:
        dlon = (lon - lo + 180) % 360 - 180
        near |= np.hypot(lat - la, dlon * np.cos(np.radians(la))) < KNOWN_RADIUS_DEG
    lat, lon, bare = lat[~near], lon[~near], bare[~near]
    print(f'  {near.sum()} cells within {KNOWN_RADIUS_DEG} deg of a curated region removed; {len(lat)} remain')
    rng = np.random.default_rng(SEED)
    block = np.floor(lat / BLOCK_DEG) * 1000 + np.floor(lon / BLOCK_DEG)
    pick = []
    for b in np.unique(block):
        idx = np.where(block == b)[0]
        pick += list(rng.choice(idx, min(PER_BLOCK, len(idx)), replace=False))
    pick = np.array(pick)
    if len(pick) > CAP:
        pick = rng.choice(pick, CAP, replace=False)
    print(f'  {len(np.unique(block))} occupied {BLOCK_DEG:.0f} deg blocks -> {len(pick)} candidate cells')
    return lat[pick], lon[pick], bare[pick]


def read_patch(lat, lon, token):
    from rasterio.transform import from_bounds
    from rasterio.warp import reproject
    box = bbox(lat, lon, 'earth')
    items = retry(lambda: requests.post(f'{STAC}/search', timeout=60, json=dict(
        collections=['cop-dem-glo-30'], bbox=list(box))).json()['features'])
    z = np.full((N, N), np.nan, np.float32)
    for it in items:
        with rasterio.open(f'{it["assets"]["data"]["href"]}?{token}') as src:
            reproject(rasterio.band(src, 1), z, src_nodata=src.nodata, dst_nodata=np.nan,
                      dst_transform=from_bounds(*box, N, N), dst_crs=src.crs,
                      resampling=Resampling.average, init_dest_nodata=False)
    return z


def build_patches():
    lat, lon, bare = pick_cells()
    token = requests.get(SAS, timeout=30).json()['token']
    t0, out, skipped, failed = time.time(), [], [0], [0]

    def work(i):
        try:
            z = retry(lambda: read_patch(lat[i], lon[i], token))
        except Exception:
            failed[0] += 1
            return None
        bad = np.isnan(z) | (z == 0.0)
        if bad.mean() > MAX_NODATA:
            skipped[0] += 1
            return None
        if bad.any():
            z[bad] = z[~bad].mean()
        return i, z, float(bad.mean())

    with ThreadPoolExecutor(max_workers=8) as pool:
        for n, r in enumerate(pool.map(work, range(len(lat)))):
            if r:
                out.append(r)
            if (n + 1) % 250 == 0:
                print(f'  {n + 1}/{len(lat)} patches, {time.time() - t0:.0f}s')
    print(f'  kept {len(out)}, skipped {skipped[0]} (nodata/sea), failed {failed[0]}, {time.time() - t0:.0f}s')
    if failed[0] > 0.05 * len(lat):
        raise SystemExit('More than 5% of Copernicus reads failed. Stop and report.')
    idx = np.array([r[0] for r in out])
    np.savez_compressed(
        OUT / 'explore_patches.npz',
        z=np.stack([r[1] for r in out]).astype(np.float32),
        patch_id=np.array([f'new_{k:04d}' for k in range(len(out))]),
        lat=lat[idx], lon=lon[idx], bare_frac=bare[idx],
        nodata_frac=np.array([r[2] for r in out]),
        source=np.array('Copernicus DEM GLO-30 (area average to 500 m); cell chosen with ESA WorldCover 2021 '
                        'v200 bare/sparse + moss/lichen share'),
    )
    print(f'Saved {OUT / "explore_patches.npz"}')


if __name__ == '__main__':
    OUT.mkdir(exist_ok=True)
    if '--refresh-mask' in sys.argv or not MASK.exists():
        build_mask()
    build_patches()
