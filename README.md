# Terrain Mapper

A researcher picks a Moon terrain patch (the **target**) and a Test Brief
(what they want to test and at what stage), and gets Earth terrain patches
ranked by how closely their **3D shape** matches. Each match shows fidelity,
accessibility, repeatability and affordability, a side-by-side 3D view and a
confidence flag.

Full spec: `docs/SPEC.md`. What the data sources actually returned, the
validation results and every deviation from the spec: `docs/DATA_NOTES.md`.

https://sunpterodactyl-nasa-challenge.vercel.app/

## Run locally

```bash
python3.11 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
npm install
```

Two terminals:

```bash
.venv/bin/python -m uvicorn api.index:app --reload --port 8000
```

```bash
npm run dev
```

Open http://localhost:5173. Vite proxies `/api` to port 8000.

Optional: for the CARTO Voyager basemap on the Map page, copy `.env.example`
to `.env.local` and set `VITE_CARTO_KEY`. Without a key the free CARTO light
basemap is used. The model
artifacts are committed in `backend/artifacts/`, so the app runs without
rebuilding the corpus.

Rebuild the data (needs network; about 2 minutes):

```bash
.venv/bin/python pipeline/verify_sources.py   # M0 source checks
.venv/bin/python pipeline/build_corpus.py     # Earth patches + Moon targets
.venv/bin/python pipeline/fit_model.py        # features, stats, regions -> backend/artifacts
.venv/bin/python pipeline/validate.py         # section 11 validation
.venv/bin/python -m backend.search --target marius_hills --objective mobility --stage early
```

`fit_model.py` needs `pipeline/data/airports.csv` (OurAirports, public domain):

```bash
curl -L -o pipeline/data/airports.csv https://davidmegginson.github.io/ourairports-data/airports.csv
```

## Method

- **Patches.** 64 × 64 elevation grids at 500 m (32 km square), relative to the
  patch median. Earth: Copernicus GLO-30, area-averaged; 25 jittered patches
  in each of 22 bare-terrain regions; 451 patches from 19 regions pass QC.
  Targets: LOLA via the USGS WMS (Marius Hills, Taurus-Littrow, Tycho).
- **Fidelity** has three components, each turned into a percentile against the
  Earth corpus and combined by geometric mean, with no weights:
  - **profile:** derivative DTW between cross-sections taken across the dominant structure.
  - **texture:** Mahalanobis distance over VRM, area ratio, short- and long-baseline roughness and Hurst exponent.
  - **magnitude:** log ratios of relief and 90th-percentile slope.
- **Novelty flag.** Compares the target's best texture distance with how close
  Earth patches are to other Earth regions: known, edge or novel.
- **A / R / C.** Accessibility from the measured distance to the nearest large
  or medium airport. Repeatability and affordability come from the curated
  `pipeline/data/regions.csv`, which is mostly blank, so those scores show as n/a.
- **Stage.** Changes the rule, not weights: early gates at F ≥ 0.5 and sorts
  by affordability; late gates at F ≥ 0.8 and sorts by fidelity.

## Finding new analogues

The Search page ranks only the 19 curated regions, so it returns known
analogue sites. **Search for new similar analogues** (or the Discover tab)
ranks 553 extra bare-terrain patches from across the globe that lie
outside those regions. ESA WorldCover picked them as at least 80% bare or
sparse ground. They're scored on the same scale as the known sites, and the
page says how many beat the best known analogue. New candidates are
unvetted: they have no field season, cost or permit data.

Rebuild them with `.venv/bin/python pipeline/explore_corpus.py` (about
8 minutes), then `fit_model.py`.

## Validation (region-blocked precision at 5)

| method | P@5 |
| --- | --- |
| random | 0.175 |
| Euclidean on z-scored features | 0.200 |
| texture only | 0.232 |
| profile only | **0.274** |
| combined fidelity | 0.253 |

Combined fidelity beats random and the Euclidean baseline, but not profile
alone. Synthetic checks pass: rotation-invariant ridge profile, self-match
F = 0.998, flat vs rugged F = 0.15. Details are in `docs/DATA_NOTES.md`.

## Limitations

- **Mars targets are paused.** The USGS MOLA WMS layer returns one constant value for the whole planet.
- **Shape only.** Fidelity covers regional 3D shape at 500 m. It ignores gravity, regolith, thermal and vacuum
  conditions, and rover-scale rocks.
- **Surface model.** Copernicus includes vegetation and buildings.
- **Correlated patches.** Patches within a region are correlated, and the landform labels are coarse,
  so precision at 5 is a sanity check, not proof.
- **Curated values.** Repeatability, affordability and permit values must be filled in from the ESA Catalogue of
  Planetary Analogues before the early-stage sort and those filters mean anything.
- **Tycho patch location.** `tycho_rim` is centred on Tycho's central peak, not its rim.

## Layout

```
pipeline/   offline data work (rasterio, pandas, requests)
backend/    runtime model, scoring, CLI and artifacts (numpy only)
api/        FastAPI app, served as a Vercel Python function
src/        Vite + React + three.js frontend
docs/       spec and data notes
```

## Deploy

`vercel.json` builds the frontend into `dist/` and serves `api/index.py` as a
Python function with `backend/` bundled. Vercel installs `requirements.txt`
(fastapi, pydantic, numpy only).
