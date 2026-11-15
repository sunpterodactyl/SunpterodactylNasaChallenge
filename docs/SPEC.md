# Terrain Mapper: Spec

## 1. Goal

A researcher picks a Moon or Mars terrain patch (the **target**), says what they want to test and at what development stage (the **Test Brief**), and gets ranked Earth terrain patches whose **3D shape** matches the target. Results show four scores (fidelity, accessibility, repeatability, affordability), a side-by-side 3D view, and a confidence flag.

## 2. Non-goals (v1)

- No LLM, RAG, Neo4j, accounts or server-side sessions.
- No thermal, ice, mineralogy, gravity or regolith modelling. Fidelity is terrain shape only.
- No polar targets (simple-cylindrical WMS breaks near poles).
- No learned deep model (GEAR's MSG-Net needs 305 expert-labelled pairs and a GPU). Listed as future work.

## 3. Repo layout

```
terrain-mapper/
  CLAUDE.md
  docs/SPEC.md  docs/DATA_NOTES.md (written in M0)
  pipeline/
    verify_sources.py  build_corpus.py  fit_model.py  common.py
    data/regions.csv  data/airports.csv  out/            (out/ is gitignored)
  backend/
    model.py  scoring.py  search.py  artifacts/model.npz  artifacts/targets.json
  api/index.py                                           (FastAPI app, 2 routes)
  src/                                                   (React app)
  requirements.txt  requirements-dev.txt  vercel.json  package.json
```

`common.py` holds shared code (`bbox`, `features`, `texture`, `aligned_profile`) imported by both pipeline and backend, so training and serving use identical feature code.

## 4. Data sources (max three)

| Source | Access | Field | Used for |
| --- | --- | --- | --- |
| Copernicus DEM GLO-30 | Planetary Computer STAC, collection `cop-dem-glo-30`, read with rasterio | elevation (m), 30 m | Earth patches |
| USGS Astrogeology WMS | `http://wms.wr.usgs.gov/cgi-bin/mapserv?map=/maps/earth/moon_simp_cyl_elev.map` layer `LOLA_elev`; `.../maps/mars/mars_simp_cyl_elev.map` layer `MOLA_elev`; request `image/tiff`, Int16 | elevation | Moon/Mars targets |
| OurAirports CSV (static file) | download once to `pipeline/data/airports.csv` (check license) | lat, lon, type | accessibility |

Plus a hand-curated `regions.csv` (section 13).

**UNVERIFIED until M0:** WMS Int16 units are meters; WMS resampling method when requesting fewer pixels than native; Mars longitude convention (-180..180 vs 0..360); whether the http endpoint works from the build machine (try https://planetarymaps.usgs.gov/... if not); Copernicus asset key is `data`; Copernicus is a surface model (includes canopy), so Earth regions must be bare terrain.

**Fallback if WMS fails:** download one small regional DEM per target from USGS Astropedia, cache as GeoTIFF in `pipeline/data/`, read locally. Report the failure; do not silently switch.

## 5. Definitions

- **Patch:** 64x64 elevation grid at 500 m spacing (32 km square). 500 m is chosen because MOLA's global grid is about 463 m, so it is the coarsest common scale.
- **Relative elevation:** always subtract the patch median. Absolute elevation is never compared across bodies.
- **Body radii:** earth 6371008.8 m, moon 1737400 m, mars 3396190 m. Convert degrees to metres with these. Pixel width shrinks with cos(latitude).
- **Target:** a Moon/Mars patch. Use mid-latitude targets only: marius\_hills (moon, 14.1, -56.7), taurus\_littrow (moon, 20.2, 30.8), tycho\_rim (moon, -43.3, -11.4), jezero\_delta (mars, 18.4, 77.5), gale (mars, -5.4, 137.8). Coordinates are approximate; verify. **Mars targets deferred (M0: MOLA WMS layer broken, see DATA_NOTES.md); v1 builds the three Moon targets only.**
- **Earth corpus:** about 22 bare-terrain regions x 25 random patches each (jitter +-0.4 deg around the region centre). Skip patches with more than 5 percent nodata.

## 6. Fidelity algorithm

Three components, each a distance from target to every Earth patch.

**6.1 Profile (shape of relief across the dominant structure; GEAR TWC idea)**

```python
import numpy as np
from scipy import ndimage as ndi

def aligned_profile(z):
    z = z - np.median(z)
    gy, gx = np.gradient(z)
    th = 0.5 * np.arctan2(2 * (gx * gy).sum(), (gx**2 - gy**2).sum())   # dominant gradient axis
    r = ndi.rotate(z, -np.degrees(th), reshape=False, order=1, mode='nearest')
    return r[8:-8, 8:-8].mean(axis=0)          # mean cross-section, length 48

def deriv(x):                                  # Keogh and Pazzani derivative estimate
    d = ((x[1:-1] - x[:-2]) + (x[2:] - x[:-2]) / 2) / 2
    return np.r_[d[0], d, d[-1]]

def ddtw(a, b):
    a, b = deriv(a), deriv(b); n, m = len(a), len(b)
    D = np.full((n + 1, m + 1), np.inf); D[0, 0] = 0
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            D[i, j] = abs(a[i-1] - b[j-1]) + min(D[i-1, j], D[i, j-1], D[i-1, j-1])
    return D[n, m] / (n + m)

def profile_dist(p, t):                        # shape only; bidirectional
    p, t = p / (np.ptp(p) + 1e-9), t / (np.ptp(t) + 1e-9)
    return min(ddtw(p, t), ddtw(p, t[::-1]))
```

Test the rotation sign on a synthetic ridge first: the profile must cut ACROSS the ridge. **(M2: with scipy the sign must be `+np.degrees(th)`; `-` fails at 45 deg. See DATA_NOTES.md.)** If DDTW is slow, use numba `@njit` or `dtaidistance` (pipeline only; runtime stays numpy, so precompute Earth profiles in pipeline and keep the DP in numpy).

**6.2 Texture (VRM, ACR and roughness; Mahalanobis on Earth covariance)**

```python
GRID_M, N = 500, 64

def texture(z):
    gy, gx = np.gradient(z, GRID_M)
    nz = 1 / np.sqrt(1 + gx**2 + gy**2); nx, ny = -gx * nz, -gy * nz
    k = np.ones((3, 3))
    sx, sy, sz = (ndi.convolve(a, k, mode='nearest') for a in (nx, ny, nz))
    vrm = (1 - np.sqrt(sx**2 + sy**2 + sz**2) / 9).mean()
    acr = np.sqrt(1 + gx**2 + gy**2).mean()      # surface/planar area ratio, approximate
    f = features(z)                               # rms_short, rms_long, hurst
    return np.array([vrm, acr, f['rms_short'], f['rms_long'], f['hurst']])

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
```

Log-transform skewed columns (rms, relief), z-score using Earth mean/std only, add ridge 1e-2 to the covariance, distance = Mahalanobis.

**6.3 Magnitude (only when mode is shape\_magnitude)**

`d_mag = abs(log(relief_c / relief_t)) + abs(log(slope_p90_c / slope_p90_t))`

**6.4 Calibration and combination (no weights)**

```python
def pct(d_all, d):                             # share of Earth patches farther than this one
    return float((d_all > d).mean())

F = float(np.exp(np.mean(np.log([max(comp[c], 1e-3) for c in active]))))   # geometric mean
```

`active` comes from the objective table (section 7). Show `comp` per component so the researcher sees which one is weakest.

**6.5 Absolute confidence check**

Percentiles alone mislead when every candidate is poor. Compute, for each Earth patch, its nearest-neighbour texture distance to a patch in a DIFFERENT region. Let lo = median and hi = 95th percentile of those. Target best texture distance <= lo: `known`; <= hi: `edge`; otherwise `novel`. Return this flag with every result.

## 7. Test Brief, scores, ranking

```python
class Brief(BaseModel):
    target_id: str
    objective: Literal['mobility', 'navigation', 'comms_los', 'eva_traverse']
    stage: Literal['early', 'late']
    mode: Literal['shape', 'shape_magnitude'] = 'shape_magnitude'
    max_cost_tier: int = 4
    max_airport_km: float = 1000
    min_field_months: int = 0
    k: int = 10

OBJECTIVES = {   # PLACEHOLDERS: researcher edits these
  'mobility':     ('texture', 'magnitude', 'profile'),
  'navigation':   ('profile', 'texture'),
  'comms_los':    ('profile', 'magnitude'),
  'eva_traverse': ('magnitude', 'texture'),
}
STAGES = {       # PLACEHOLDERS: stage changes the rule (gate, sort key), not weights
  'early': dict(gate=0.5, sort='C'),
  'late':  dict(gate=0.8, sort='F'),
}
```

In shape-only mode remove `magnitude` from `active`.

Four scores per match, each 0 to 1:

- **F fidelity:** section 6.
- **A accessibility:** `(1 - min(airport_km, 1000)/1000) * (0.5 if permit else 1)`. The 0.5 is a placeholder.
- **R repeatability:** `field_months/12 * stability` (stability in 0..1, curated).
- **C affordability:** `(5 - cost_tier)/4` (curated tier 1 to 4).

A, R and C are region level; every patch inherits its region's values. They are curated estimates, not measurements: show sources in the UI.

```python
def rank(ms, stage, brief):
    st = STAGES[stage]
    for m in ms:
        m['pareto'] = not any(all(o[k] >= m[k] for k in 'FARC') and any(o[k] > m[k] for k in 'FARC') for o in ms)
    ok = [m for m in ms if m['F'] >= st['gate'] and m['cost_tier'] <= brief.max_cost_tier
          and m['airport_km'] <= brief.max_airport_km and m['field_months'] >= brief.min_field_months]
    return sorted(ok, key=lambda m: (-m[st['sort']], -m['F']))[:brief.k]
```

If nothing passes the gate, return an empty list plus a message naming the best fidelity reached. That is a valid result.

## 8. API contract (two routes only)

`GET /api/catalog` returns:

```python
{'targets': [{'id', 'name', 'body', 'lat', 'lon', 'grid': [[...64x64 ints (metres, relative)...]]}],
 'objectives': ['mobility', ...], 'stages': ['early', 'late'], 'regions': ['atacama', ...]}
```

`POST /api/search` takes a `Brief` and returns:

```python
{'target_id': str, 'novelty': 'known' | 'edge' | 'novel', 'best_fidelity': float, 'message': str | None,
 'matches': [{'patch_id', 'region', 'lat', 'lon', 'kind',
              'F', 'A', 'R', 'C', 'components': {'profile', 'texture', 'magnitude'},
              'weakest': str, 'pareto': bool,
              'airport_km', 'field_months', 'cost_tier', 'permit', 'source',
              'grid': [[...64x64 ints...]]}]}
```

Round grids to integer metres. Runtime loads `backend/artifacts/model.npz` and `targets.json` once at import. Add CORS only if the frontend is served from a different origin in dev.

## 9. Frontend

- **Left sidebar (Test Brief):** target dropdown (grouped Moon/Mars), objective, stage, mode toggle, cost/airport/season filters, Run. Saved sessions list below (localStorage key `terrain.sessions`: name, brief, starred patch ids, notes).
- **Center:** two three.js terrain meshes side by side (target | selected match), `PlaneGeometry(10, 10, 63, 63)` with vertex heights from the grid, same vertical-exaggeration slider and same light for both, orbit controls with synced camera, colour by height.
- **Right:** ranked list. Each row: region, F/A/R/C bars, Pareto badge, novelty badge. Selected row shows an SVG radar chart of F, A, R, C, the weakest fidelity component, and the curated sources.
- **Empty and error states:** nothing passes gate (show best fidelity reached), novel target (say no Earth patch is close), API error (show message, keep form usable).
- Visual direction: survey-chart feel. Light paper-grey ground, dark ink text, one ochre accent for selection, glacier blue for the target. One sans family, tabular numerals for scores. Collapse to one column on mobile; visible focus states; respect reduced motion.

## 10. Milestones (do one at a time; stop and report after each)

**M0 Verify sources.** `pipeline/verify_sources.py` reads one Earth window (Atacama -24.5, -69.2), one LOLA window (Marius Hills), one MOLA window (Jezero), each 64x64 at 500 m, and prints min/max, units, timing, and saves a PNG hillshade of each. Write findings to `docs/DATA_NOTES.md`. *Acceptance:* three plausible arrays; every UNVERIFIED item in section 4 marked confirmed or failed.

**M1 Corpus.** `build_corpus.py` builds the Earth patches (about 22 regions x 25) and 5 targets, with QC (skip over 5 percent nodata, fill remaining with the patch mean). Saves `pipeline/out/earth_patches.npz` and `targets.npz`. *Acceptance:* at least 15 patches per kept region; printed count table; one failed region does not stop the run.

**M2 Fidelity model.** Implement section 6 in `backend/model.py`; `fit_model.py` precomputes Earth profiles, texture vectors, covariance, and the novelty thresholds into `backend/artifacts/model.npz`. Add CLI `python -m backend.search`. *Acceptance:* the CLI prints top 10 patches per target with component scores and novelty flag; validation (section 11) table printed.

**M3 Regions, A/R/C, ranking.** Load `regions.csv`, compute airport distance from `airports.csv` (haversine, large and medium airports only), implement section 7 ranking and Pareto. *Acceptance:* CLI output includes F, A, R, C and respects stage gate and filters.

**M4 API.** Implement the two routes. *Acceptance:* `curl` examples for catalog and search return the contract shape; response under 2 s locally.

**M5 Frontend.** Section 9. *Acceptance:* run a search, see both meshes, switch matches, radar updates, save and reload a session.

**M6 Deploy and README.** Vercel deploy; README with method summary, validation table, screenshots, limitations. *Acceptance:* the deployed URL returns the same results as local for one fixed brief.

## 11. Validation

- **Region-blocked landform check:** label each region with a coarse landform type (arid, volcanic, polar, flat, dune, mountain). For each region, refit the model WITHOUT it, query with its average features, and measure how often the top 5 regions share its type (precision at 5). Report random, Euclidean-on-z-scores baseline, texture only, profile only, and combined fidelity.
- **Synthetic tests (print, no test framework):** a ridge rotated by several angles must give nearly the same profile; identical patches must score near 1.0; a flat patch vs a rugged one must score low.
- **Stability:** bootstrap the corpus (resample patches within regions) and report how often the top 3 regions stay the same.
- Report honest negatives. If combined fidelity does not beat the baseline, say so.

## 12. Risks and limits

- Fidelity is regional 3D shape at 500 m. It says nothing about gravity, regolith, thermal or vacuum conditions, and does not capture rover-scale rocks.
- Copernicus is a surface model including vegetation; keep the corpus to bare terrain.
- Patches within a region are correlated, so the effective sample is small; evaluate region-blocked.
- Landform labels are coarse and hand-assigned; precision at 5 is a sanity check, not proof.
- A, R and C are curated estimates. Every value needs a source.
- WMS is an old endpoint and may be slow or down; see the fallback in section 4.
- Percentile scores depend on corpus diversity; the novelty flag is the absolute check.

## 13. Curated region table

`pipeline/data/regions.csv` columns:

```
region, lat, lon, kind, field_months, stability, cost_tier, permit, source
```

- `kind`: arid, volcanic, polar, flat, dune, mountain.
- `field_months` 0 to 12; `stability` 0 to 1 (1 = stable ground, lower for glacial, dynamic or hazardous); `cost_tier` 1 (cheap, day trip) to 4 (expedition); `permit` 0 or 1.
- Seed regions (approximate coordinates, verify): atacama (-24.5, -69.2), namib (-24.7, 15.2), gobi (42.5, 105.0), lut (30.5, 58.5), tibesti (21.0, 17.5), death\_valley (36.3, -116.9), askja (65.0, -16.8), mauna\_loa (19.5, -155.6), etna (37.75, 15.0), craters\_of\_the\_moon (43.4, -113.5), tenerife (28.27, -16.6), pinacate (31.8, -113.5), devon (75.4, -89.7), dry\_valleys (-77.5, 162.5), svalbard (78.2, 15.6), uyuni (-20.1, -67.5), bonneville (40.8, -113.9), taklamakan (39.0, 83.0), rub\_al\_khali (20.0, 51.0), qaidam (37.0, 94.5), danakil (14.2, 40.3), altiplano\_north (-18.0, -69.0).
- Dry Valleys example: cost\_tier 4, permit 1, source: ESA Catalogue of Planetary Analogues (cost very high; Antarctic Treaty and Madrid Protocol apply).
- Leave unknown values blank and flag them; do not invent numbers. The researcher fills them from the ESA catalogue and their own judgement.

## 14. Reference reading

- GEAR: Geography-knowledge Enhanced Analog Recognition (arXiv 2603.18626). Source of the DDTW profile idea and the VRM/ACR texture metrics. Small labelled set (305 pairs), preprint; use as inspiration.
- ESA Catalogue of Planetary Analogues (accessibility, permissions, cost, scheduling per site).
- NASA NTRS: Salient Characteristics for Terrestrial Analog Engineering Test Sites.
