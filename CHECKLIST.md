# Anomaly Correlation Map — Project Checklist

> Last updated: Sprint 8 | Branch: `claude/project-setup-datasets-ins4du`

---

## Completed

### Infrastructure
- [x] `anomaly_map/scripts/common.py` — shared record schema, GeoJSON helpers, retry/logging utilities
- [x] `anomaly_map/data/layer_registry.json` — master layer config with tier weights, layer_groups UX categories
- [x] `anomaly_map/requirements.txt` — all Python dependencies including dataretrieval, astropy
- [x] `anomaly_map/scripts/run_phase1.py` — unified pipeline runner with `--sprint` flag (Sprints 1-8)
- [x] `.env.example` — all required API keys documented (FIRMS, NASA SEDAC, Copernicus)

### Manual Context Data (`data/manual/`)
- [x] `cattle_mutilations.csv`
- [x] `persistent_earth_lights.csv`
- [x] `earthquake_lights.csv`
- [x] `uso_incidents.csv`
- [x] `black_budget_sites.csv`
- [x] `skyquakes.csv`
- [x] `indigenous_sacred_sites.csv`

### Processing Scripts
- [x] `scripts/process/geocode_manual.py` — CSV drop-in → GeoJSON (zero other code changes)
- [x] `scripts/process/normalize_all.py` — standardize all layer outputs
- [x] `scripts/process/merge_layers.py` — combine into merged GeoJSON

### Analysis Scripts
- [x] `scripts/analyze/clustering.py` — DBSCAN spatial clustering, Haversine distance
- [x] `scripts/analyze/correlation.py` — layer-to-layer correlation
- [x] `scripts/analyze/population_control.py` — NASA SEDAC GPWV4 population bias correction
- [x] `scripts/analyze/convergence_score.py` — full Python C-Score grid (CONUS + Zone E), SUA masking, top_zones.json

### Visualization
- [x] `scripts/viz/generate_map.py` — static Folium map output

### Fetch Scripts — Tier 1 Geophysical Baselines (Layers 1-12)
- [x] Layer 01: `fetch_nuforc.py` — NUFORC UAP sightings (75-year archive, Lomb-Scargle periodogram)
- [x] Layer 02: `fetch_usgs_seismic.py` — USGS FDSN earthquake catalog
- [x] Layer 03: `fetch_usgs_magnetic.py` — USGS North American Magnetic Anomaly Grid
- [x] Layer 04: `fetch_usgs_radon.py` — USGS geologic radon potential
- [x] Layer 05: `fetch_firms.py` — NASA FIRMS thermal anomalies (FIRMS API)
- [x] Layer 06: `fetch_noaa_ume.py` — NOAA marine mammal unusual mortality events
- [x] Layer 07: `fetch_dart_buoys.py` — NOAA DART ocean pressure buoys
- [x] Layer 08: `fetch_gps_tec.py` — GPS-TEC ionospheric disturbance (IONEX)
- [x] Layer 09: `fetch_doe_grid.py` — DOE OE-417 power grid disturbance reports
- [x] Layer 10: `fetch_epa_radnet.py` — EPA RadNet radiation monitoring
- [x] Layer 11: `fetch_nuclear_facilities.py` — NRC + DOE nuclear facility locations
- [x] Layer 12: `fetch_grace_gravity.py` — NASA GRACE gravity anomaly

### Fetch Scripts — Tier 2 Infrastructure + Controls (Layers 13-25)
- [x] Layer 13: `fetch_faa_airspace.py` — FAA SUA/restricted airspace polygons (control mask)
- [x] Layer 14: `fetch_nighttime_lights.py` — NASA VIIRS nighttime lights (population proxy)
- [x] Layer 15: `fetch_sentinel5p.py` — ESA Sentinel-5P atmospheric chemistry
- [x] Layer 16: `fetch_ctbto_infrasound.py` — CTBTO IMS infrasound network
- [x] Layer 17: `fetch_vlf_elf.py` — VLF/ELF electromagnetic emissions
- [x] Layer 18: `fetch_goes_ir.py` — NOAA GOES IR atmospheric gravity waves
- [x] Layer 19: `fetch_nav_disruption.py` — marine/bird navigation disruption (via noaa_ume)
- [x] Layer 20: `fetch_doe_grid.py` — DOE grid (also covers infrastructure context)
- [x] Layer 21: `fetch_nuclear_facilities.py` — nuclear facilities (dual use)
- [x] Layer 22: `fetch_adsb.py` — OpenSky ADS-B traffic + coverage gap zones + military corridors

### Fetch Scripts — Sprint 7 Extended Datasets (Layers 26-35)
- [x] Layer 26: `fetch_movebank.py` — Movebank animal migration anomalies (8 curated behavioral events)
- [x] Layer 27: `fetch_bfro.py` — BFRO anomalous observation database (Class A elevated confidence)
- [x] Layer 28: `fetch_usgs_mines.py` — USGS MRDS mine database
- [x] Layer 29: `fetch_faa_wildlife.py` — FAA wildlife strike database (magnetoreceptive species elevated)
- [x] Layer 30: `fetch_water_wells.py` — USGS NWIS groundwater anomaly wells
- [x] Layer 31: `fetch_adsb.py` — ADS-B (see above, covers control layer)
- [x] Layer 32: `fetch_space_weather.py` — NOAA SWPC solar flares/geomagnetic storms (control mask)
- [x] Layer 33: `fetch_foia_docs.py` — FOIA-derived institutional UAP records (Nimitz, Gimbal, GoFast, AARO, Grusch)
- [x] Layer 34: `fetch_maritime.py` — maritime anomaly incidents (USO, nav blackouts, acoustic, NDBC buoys)
- [x] Layer 35: `fetch_schumann.py` — Schumann resonance / ELF monitoring (11 global stations)

### Phase 2 React App — Scaffold (`anomaly_map/app/`)
- [x] `package.json` — React 18, Deck.gl 9, MapLibre GL JS, DuckDB-WASM, Apache Arrow, Zustand, Vite
- [x] `vite.config.js` — COOP/COEP headers for SharedArrayBuffer, manual chunk splitting
- [x] `index.html` — app shell
- [x] `src/main.jsx` — React 18 createRoot entry
- [x] `src/styles/global.css` — CSS custom properties (dark theme, --accent-cyan, --panel-width)
- [x] `src/App.jsx` — root component, lazy layer loading, registry fetch
- [x] `src/store/useStore.js` — Zustand store with visibleLayers, viewState, filters, C-Score actions
- [x] `src/utils/layers.js` — CATEGORY_COLORS, CONFIDENCE_RADIUS, cScoreToColor, ZONE_COLORS
- [x] `src/analysis/convergenceScore.js` — client-side C-Score with DuckDB-WASM fallback
- [x] `src/components/Header.jsx` — view buttons, zone jump buttons
- [x] `src/components/Map.jsx` — DeckGL + MapLibre dark basemap, heatmap/scatter modes
- [x] `src/components/LayerPanel.jsx` — left panel, layer groups, confidence filter
- [x] `src/components/DetailPanel.jsx` — right panel, live C-Score, penalty indicators, layer breakdown
- [x] `src/components/LoadingOverlay.jsx` — spinner + error display

---

## Sprint 8 — In Progress

### New Fetch Scripts (Advanced Packet Layers)
- [x] Layer 40: `fetch_bluebook.py` — Project Blue Book Unknowns (701 vetted cases)
- [x] Layer 42: `fetch_geipan.py` — French GEIPAN Category D unexplained cases
- [x] Layer 52: `fetch_solar_cycle.py` — Solar cycle vs. UAP timeline (computed correlation layer)
- [x] Layer 53: `fetch_nuclear_tests.py` — Atmospheric nuclear test dates (528 tests, 1945-1980)
- [x] Layer 38/39: `fetch_aatip_medical.py` — AATIP medical cases + Vallée physiological database
- [x] Layer 44: `fetch_belgian_triangle.py` — Belgian triangle wave 1989-1990 (SOBEPS, ~2,600 reports, F-16 radar confirmed)
- [x] Layer 48: `fetch_cefaa.py` — Chilean CEFAA official UAP investigation cases

### App — Priority Features (Claude Packet)
- [x] React Router — routes: /, /map, /z/:zoneSlug, /about, /sources, /feedback
- [x] Shareable URL state (MANDATORY) — all map config serialized to query params
- [x] Permanent reality header — "Correlation ≠ causation..."
- [x] Rotating logic reminders
- [x] Claim Level badge (Level 1-6 ladder)
- [x] N-Score scaffolding — fields + display
- [x] R-Score scaffolding — fields + display
- [x] Reality Checks panel — 10 confound checks
- [x] Landing page (`/`)
- [x] About page (`/about`)
- [x] Sources page (`/sources`)
- [x] Feedback page (`/feedback`)
- [x] Public hotspot pages (`/z/:zoneSlug`) with OpenGraph meta
- [x] Investigation presets (Clean Signal Hunt, Skeptic Mode, Physical Effects, Low-Report Weirdness) — `PresetsPanel.jsx`
- [x] Event deduplication / incident grouping (`incident_group_id`, `report_count`) — `scripts/process/tag_events.py`
- [x] Keyword-derived tags (`secondary_effect_tags`, `physical_effect_score`) — `scripts/process/tag_events.py`
- [x] Bias/confound flags per event (`confound_flags`) — `scripts/process/tag_events.py`

### Architecture
- [x] `docs/FEEDBACK_TRIAGE_AGENT.md` — LLM triage agent design doc
- [x] `scripts/build/build_pmtiles.py` — PMTiles build script for large layer datasets
- [x] `layer_registry.json` — layers 38-53 metadata (44 total layers)
- [x] `run_phase1.py` — Sprint 8 steps (aatip, belgian_triangle, cefaa, bluebook, geipan, solar, nuclear)
- [x] `scripts/process/tag_events.py` — keyword tagging + deduplication pass

---

## Pending — Next Sprints

### Data Layers (Advanced Packet)
- [x] Layer 36: `fetch_periodicity.py` — UAP flap period centroids + Lomb-Scargle periodicity analysis
- [x] Layer 37: `fetch_behavioral_taxonomy.py` — UAP behavioral taxonomy (9 categories, 13 cluster records)
- [x] Layer 41: `fetch_foo_fighters.py` — WWII Foo Fighter reports (European + Pacific theater, 415th NFS)
- [ ] Layer 43: UK MOD UAP Files (National Archives NLP extraction, ~2,000 cases)
- [ ] Layer 45: Soviet SETKA Cases (Stonehill/Mantle, ~300 cases, translation required)
- [ ] Layer 46: Dalnegorsk Physical Evidence (Hill 611, Soviet Academy analysis)
- [x] Layer 47: `fetch_operation_prato.py` — Brazilian Operation Prato 1977 (FAB investigation, Colares Island)
- [ ] Layer 49: Witness Career Database (public record + FOIA, ~50 named witnesses)
- [ ] Layer 50: High-Strangeness Reports (NUFORC NLP classification, ~5,000 tagged)
- [ ] Layer 51: Pais Patent Filing Locations (USPTO, 4 patents)

### App — Second Pass
- [x] Investigation presets (Clean Signal Hunt, Skeptic Mode, Physical Effects, Low-Report Weirdness) — `PresetsPanel.jsx`
- [x] Event deduplication / incident grouping (incident_group_id, report_count, dedupe_confidence) — `tag_events.py`
- [x] Keyword-derived tags (secondary_effect_tags, physical_effect_score) — `tag_events.py`
- [x] Bias/confound flags per event (military_confound, coastal_confound, etc.) — `tag_events.py`
- [x] Top 10 hotspots list in sidebar — `HotspotsList.jsx` in LayerPanel
- [x] Sorting tabs (Top Convergence, Cleanest Residuals, Most Confounded, Physical Effects) — MapHeader sort select
- [x] "Near Me" locator feature — `useNearMe.js` hook + MapHeader button
- [ ] Custom share images for zone pages
- [ ] Obscured/Restricted Imagery layer (context layer, not anomaly evidence)
- [x] Feedback storage backend — `api/submit_feedback.py` (JSONL + Vercel serverless)

### Analysis
- [ ] Cross-national geological correlation test (GEIPAN + UK MOD + Soviet + Blue Book + CEFAA)
- [ ] Behavioral taxonomy spatial clustering (do behavior types cluster geographically?)
- [ ] High-strangeness vs. geology correlation (radon, infrasound, fault type)
- [ ] Hessdalen Zone C as solved analog/control validation
- [ ] Zone E (Japan Trench) validation run

### Architecture / Ops
- [ ] PMTiles serve path (Tippecanoe → static deploy, S3/Vercel)
- [ ] Progressive disclosure: boot with pre-calculated C-Score heatmap, raw data on hotspot click
- [ ] CI/CD pipeline for nightly data refresh
- [ ] Feedback storage backend
- [ ] OpenGraph share image generation

---

## Frozen Scope (Do Not Implement)
- Monetization, ads, paid tiers, user accounts
- AI map analyst
- Automatic community uploads into core map data
- New speculative data layers beyond packet spec
- Full report generator
- Custom public layer publishing
- Witness career tracking (personal/private data)
- Medical/private records
- Pais patents in app UI
- Undersea archaeology layer
- Automatic LLM ingestion into core layers

---

## Zone Reference
| Zone | Name | Coordinates | Notes |
|------|------|-------------|-------|
| A | Rocky Mountain Rift (San Luis Valley) | 37.5°N, 105.8°W | Primary US hotspot |
| B | Southern California Offshore / Santa Catalina Channel | 33.4°N, 118.5°W | High military + marine confound |
| C | Hessdalen, Norway | 62.8°N, 11.2°E | Solved analog / control site |
| D | New Madrid Seismic Zone | 36.5°N, 89.5°W | Seismic correlation test |
| E | Japan Trench | 38.1°N, 144.5°E | Validation zone (cross-national) |

---

## Scoring Model Reference
```
C-Score = Σ(layers within radius R) × tier_weight × population_correction × military_mask_penalty × solar_penalty × industrial_correction
N-Score = Noise/Confound Score (how likely is this explained by known confounds?)
R-Score = Residual Score = C-Score after full noise penalties

Tier weights: T1=1.0, T2=0.5, T3=0.25
Control layers (penalty-only, not summed): space_weather, adsb_traffic, nighttime_lights, faa_airspace
Military penalty: ×0.4 | Solar high-KP penalty: ×0.6 | Industrial penalty: ×0.7
```

---

## Claim Level Ladder
| Level | Requirement |
|-------|-------------|
| 1 | Visual cluster only |
| 2 | Survives population correction |
| 3 | Survives population + military/industrial masking |
| 4 | Multiple independent Tier 1 layers converge |
| 5 | Spatial AND temporal convergence confirmed |
| 6 | Survives negative controls |
