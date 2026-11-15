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

## Decisions

- **2026-11-15: Mars targets are left out for now.** `jezero_delta` and `gale` are
  not built while the MOLA WMS layer is broken. v1 runs with the three Moon
  targets only. The Astropedia fallback stays documented above in case Mars
  comes back.
- **Copernicus sea is 0, not nodata.** Checked during M1 prep: a patch over
  the sea off Tenerife is 100% exactly 0.0 m with no NaN, and a Svalbard patch
  is 25% exactly 0.0 (fjords). M1 QC therefore counts exact-zero cells as
  nodata alongside NaN. Real land below sea level (Death Valley, Danakil) is
  negative, not zero, so it is unaffected.
- **Targets are read at 4x and block-averaged.** The WMS resampling method is
  unsettled (see above), so M1 requests 256 x 256 and averages 4 x 4 blocks
  down to 64 x 64. This matches the area average used for Copernicus.

# Corpus build (M1)

`python pipeline/build_corpus.py`, run 2026-11-15, about 1.5 min with 6
region threads. Seed 42, 25 patches per region, jitter +-0.4 deg.

| region | kind | kept | skipped | relief p5-p95, median (m) | status |
| --- | --- | --- | --- | --- | --- |
| atacama | arid | 25 | 0 | 1013 | ok |
| namib | dune | 21 | 4 | 286 | ok |
| gobi | arid | 25 | 0 | 270 | ok |
| lut | arid | 25 | 0 | 168 | ok |
| tibesti | volcanic | 25 | 0 | 868 | ok |
| death_valley | arid | 25 | 0 | 1502 | ok |
| askja | volcanic | 25 | 0 | 622 | ok |
| mauna_loa | volcanic | 16 | 9 | 2217 | ok |
| etna | volcanic | 11 | 14 | 1263 | dropped (<15) |
| craters_of_the_moon | volcanic | 25 | 0 | 244 | ok |
| tenerife | volcanic | 1 | 24 | 2226 | dropped (<15) |
| pinacate | volcanic | 22 | 3 | 207 | ok |
| devon | polar | 18 | 7 | 164 | ok |
| dry_valleys | polar | 24 | 1 | 1519 | ok |
| svalbard | polar | 6 | 19 | 746 | dropped (<15) |
| uyuni | flat | 25 | 0 | 0 | ok |
| bonneville | flat | 25 | 0 | 265 | ok |
| taklamakan | dune | 25 | 0 | 42 | ok |
| rub_al_khali | dune | 25 | 0 | 23 | ok |
| qaidam | arid | 25 | 0 | 38 | ok |
| danakil | volcanic | 25 | 0 | 428 | ok |
| altiplano_north | mountain | 25 | 0 | 875 | ok |

**Kept 451 patches from 19 regions.** No NaN remains; 17 kept patches had
some nodata filled (max 4.5%). Below-sea-level land survives the sea rule
(Danakil min -125 m, Death Valley min -86 m).

Notes:

- **Dropped regions are coastal or island sites.** Jittered patches land in the sea.
  Etna, Tenerife and Svalbard could be kept by moving the centre inland or
  shrinking the jitter. That's a curation choice for the region table.
- **Uyuni is near-perfectly flat.** p5-p95 relief is 0 m in most patches, per-patch
  std about 6 m. This is real (salt flat), but M2 must guard `log(relief)`
  and `slope_p90` against zero.
- **Vegetation:** Etna's and Mauna Loa's lower flanks carry vegetation, which a
  surface model includes. Not filtered.
- **Targets:** marius_hills relief 423 m, taurus_littrow 1982 m,
  tycho_rim 988 m. The `tycho_rim` coordinate (-43.3, -11.4) is Tycho's
  centre. The 32 km patch shows the central peak and floor, not the rim.
  Either rename it or move it about 0.7 deg off-centre onto the rim.
