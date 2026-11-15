# Terrain Mapper

Finds Earth terrain patches whose 3D shape matches Moon and Mars terrain
patches, then ranks them by fidelity, accessibility, repeatability and
affordability.

Status: under construction, milestone by milestone. See `docs/SPEC.md`
(section 10) for the plan and `docs/DATA_NOTES.md` for what the data
sources actually return. The frontend in `src/` is the earlier prototype
and will be rebuilt in milestone M5.

## Layout

```
pipeline/   offline data work (rasterio, pandas, requests)
backend/    runtime model and scoring (numpy only)
api/        FastAPI app served as a Vercel function
src/        Vite + React + three.js frontend
docs/       spec and data notes
```

## Setup

```bash
python3.11 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt   # pipeline + runtime
npm install
```

`requirements.txt` is the runtime set (fastapi, pydantic, numpy) that
Vercel installs. `requirements-dev.txt` adds the pipeline-only packages.
