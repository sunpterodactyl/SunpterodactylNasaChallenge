# Data notes (M0)

Findings from `python pipeline/verify_sources.py`, run 2026-11-15. Each
patch is 64 x 64 at 500 m (32 km square). Hillshades are written to
`pipeline/out/m0_*.png` (gitignored).

## Results

| Source | Patch | min / max (m) | std (m) | time | Verdict |
| --- | --- | --- | --- | --- | --- |
| Copernicus GLO-30 (Planetary Computer) | atacama (-24.5, -69.2) | 2032 / 3876 | 390.8 | 5.3 s | PASS |
| USGS WMS `LOLA_elev` | marius_hills (14.1, -56.7) | -1811 / -950 | 127.3 | 6.5 s | PASS |
| USGS WMS `MOLA_elev` | jezero_delta (18.4, 77.5) | -1517 / -1517 | 0.0 | 5.4 s | **FAIL** |
| Astropedia MOLA 463 m mosaic (fallback probe only, not used) | jezero_delta | -2715 / -1586 | 274.5 | 14.3 s | PASS |

**The Mars WMS layer is broken.** `MOLA_elev` returns the single value
-1517 m everywhere: a 360 x 180 request over the whole planet has exactly one
unique value, and the PNG output is flat too. Per CLAUDE.md this is a stop
and report. No Mars data has been substituted. The SPEC section 4 fallback
(Astropedia) is reachable and returns believable relief for Jezero (the crater
rim is visible in the hillshade), but switching to it needs a decision.

## SPEC section 4 UNVERIFIED items

| Item | Status | Evidence |
| --- | --- | --- |
| `http://wms.wr.usgs.gov` endpoint works | **FAILED** | Connection times out. `https://planetarymaps.usgs.gov` serves the same map files and responds in about 5-7 s per request. |
| WMS Int16 units are metres | **CONFIRMED (Moon)** | `LOLA_elev_uint16` (documented as metres + 9130) minus `LOLA_elev` has median 9130, range 9126-9134. The few-metre spread comes from the two layers being resampled separately. Mars cannot be checked while `MOLA_elev` is broken. |
| WMS resampling when requesting fewer pixels | **NOT SETTLED** | Comparing a 64 px request with a 256 px request of the same box: mean difference vs 4x4 block mean is 3.43 m, vs centre-pixel nearest is 3.40 m. Both are equally close, so the method can't be told apart this way. MapServer defaults to nearest neighbour. If we keep using the WMS, request 4x pixels and block-average ourselves so we don't rely on the server's resampling. |
| Mars longitude convention | **INCONCLUSIVE via WMS / -180..180 via Astropedia** | WMS replies are constant at both 77.5 and -282.5. The Astropedia mosaic spans x = -10669675..10669675 m, i.e. -180..180 deg centred on 0. Moon WMS is also -180..180 (lon 303.3 returns all zeros). |
| Copernicus asset key is `data` | **CONFIRMED** | Item assets are `data`, `rendered_preview`, `tilejson`. Tile `Copernicus_DSM_COG_10_S25_00_W070_00_DEM`, EPSG:4326, 1 arcsec, float32. |
| Copernicus is a surface model (includes canopy) | **CONFIRMED (product docs)** | The tile id says `DSM`. The file has no units tag and `nodata=None`, so missing coverage only shows up as cells no tile covered (left as NaN by our reproject). M1's nodata QC must count NaNs, not a nodata value. Regions must be bare terrain. |

## Other notes

- Request the WMS with `VERSION=1.1.1`, `SRS=EPSG:4326` and `BBOX=minlon,minlat,maxlon,maxlat`. In 1.3.0 EPSG:4326 the axis order flips to lat,lon.
- `IAU_2015:49900` is advertised for Mars but returned all zeros in a quick test.
- Astropedia mosaic: `Mars_MGS_MOLA_DEM_mosaic_global_463m.tif`, 23040 x 46080 Int16, nodata -32768, equirectangular metres on a sphere. It is stored in strips (one row per block), so a 32 km window reads about 70 rows x 92 KB remotely. That's fine for 2 targets; for repeated runs, cache a regional crop in `pipeline/data/` as SPEC section 4 says.
- Copernicus reads use `Resampling.average` from 30 m to 500 m, which is a true area average.

## Decision needed before M1

How should Mars targets (jezero_delta, gale) be sourced?

1. Use the SPEC fallback: read the Astropedia MOLA mosaic, cache a GeoTIFF crop per Mars target in `pipeline/data/`, and record the source as Astropedia in provenance. (Recommended.)
2. Wait for or report the WMS issue to USGS and keep Mars targets out until it's fixed.
