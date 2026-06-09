# Anomalous Phenomena Correlation Map

Multi-layer geospatial analysis tool that overlays independently sourced anomalous phenomena datasets against geophysical baseline data to identify non-random geographic clustering.

**Core hypothesis:** UAP sightings, marine mammal strandings, cattle mutilations, earth lights, electromagnetic disturbances, and seismic geology may share underlying geophysical drivers. If clustering persists after controlling for population density, that's a signal worth investigating.

**What makes this novel:** No published work has simultaneously cross-referenced UAP density, seismic geology, magnetic anomalies, radon potential, marine stranding events, cattle mutilation geography, and classified facility locations against each other.

---

## Phase Status

- [x] **Phase 1:** Data acquisition + correlation analysis — *in progress*
- [ ] **Phase 2:** Interactive map with toggleable layers, confidence weighting, time slider — *after Phase 1 confirms signal*
- [ ] **Phase 3:** Drill into specific geographic zones — *if strong signal found*

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env

# Run full Phase 1 pipeline
python scripts/run_phase1.py

# Or run steps individually
python scripts/run_phase1.py --fetch    # Download all data sources
python scripts/run_phase1.py --process  # Normalize + merge layers
python scripts/run_phase1.py --analyze  # Clustering + correlation
python scripts/run_phase1.py --viz      # Generate Folium map

# Open the map
open output/anomaly_map.html
```

---

## Adding New Datasets

**The system is designed for zero-friction dataset addition:**

1. Create a CSV in `data/manual/` with these columns:
   ```
   lat, lon, datetime (optional), source, notes
   ```
2. Optionally add layer metadata to `data/layer_registry.json`
3. Run:
   ```bash
   python scripts/process/geocode_manual.py <your_layer_name>
   python scripts/process/normalize_all.py
   python scripts/process/merge_layers.py
   ```

No other code changes required. The analysis and visualization scripts pick up new layers automatically.

**If your CSV has addresses instead of coordinates**, include an `address` column and the geocoder will convert them via Nominatim (free, rate-limited at 1 req/sec).

---

## Project Structure

```
anomaly_map/
├── README.md
├── requirements.txt
├── .env.example
├── data/
│   ├── layer_registry.json     ← Master layer config + zone definitions
│   ├── raw/                    ← Downloaded source files, never modified
│   ├── processed/              ← Cleaned, normalized per-layer GeoJSON
│   └── manual/                 ← Hand-curated CSV datasets (drop-in)
├── scripts/
│   ├── common.py               ← Shared schema, I/O, retry utilities
│   ├── run_phase1.py           ← Full pipeline orchestrator
│   ├── fetch/                  ← One script per automated data source
│   ├── process/                ← normalize_all, geocode_manual, merge_layers
│   ├── analyze/                ← clustering, correlation, population_control
│   └── viz/                    ← generate_map (Folium output)
└── output/
    ├── layers/                 ← Validated per-layer GeoJSON
    ├── combined.geojson        ← All layers merged
    ├── layer_manifest.json     ← Layer index with record counts
    ├── anomaly_map.html        ← Interactive Folium map
    └── analysis/               ← Statistical output JSON files
```

---

## Data Layers

### Tier 1 — High Confidence (Automated, geocoded, large N)

| Layer | Source | Records | Key Fields |
|-------|--------|---------|------------|
| NUFORC UAP Sightings | National UFO Reporting Center | ~170,000 | datetime, shape, city/state, lat/lon |
| NOAA Marine UMEs | NOAA Fisheries ArcGIS | 72+ UMEs | species, event_date, cause |
| DOE Grid Disturbances | OE-417 Annual Reports | 2,000+ | nerc_region, event_type, cause |
| USGS Seismic Catalog | USGS FDSN API | Continuous | magnitude, depth, datetime |
| USGS Magnetic Anomaly | NAMAG GeoTIFF | Continental raster | anomaly_nt |
| USGS Radon Potential | OFR 93-292 Shapefile | County-level | radon_class |
| EPA RadNet | Envirofacts API | 140+ stations | station coordinates |
| Nuclear Facilities | NRC + DOE + manual | ~30 | facility_type, uap_documented |

### Tier 2 — Medium Confidence (Manual geocoding, smaller N)

| Layer | Source | Records |
|-------|--------|---------|
| Cattle Mutilations | Howe/O'Brien/FBI Vault | ~15 key cases |
| Earthquake Lights (EQL) | Thériault et al. 2014 | 15 documented |
| Persistent Earth Lights | Project Hessdalen + research | 10 locations |
| Black Budget Sites | FOIA/Congressional/Public | 14 sites |
| USO Incidents | Navy FOIA + NUFORC | 11 key cases |
| Skyquakes | USGS + press | 10 clusters |
| Indigenous Sacred Sites | UNESCO/NPS | 10 sites |

---

## Standard Record Schema

All records across all layers conform to this schema:

```json
{
  "id": "uuid",
  "layer": "layer_name",
  "lat": 37.5,
  "lon": -106.0,
  "datetime": "ISO8601 or null",
  "confidence": 1,
  "category": "uap|marine|geophysical|em_disturbance|...",
  "source": "string",
  "notes": "string"
}
```

---

## Zones of Interest

Pre-defined geographic zones for focused analysis:

| Zone | Name | Key Convergence |
|------|------|-----------------|
| A | Rocky Mountain Rift Corridor | Rio Grande Rift + San Luis Valley + Skinwalker Ranch + Los Alamos/Sandia |
| B | Southern California Offshore | Santa Catalina Channel + submarine faults + USO hotspot + China Lake/Vandenberg |
| C | Hessdalen Valley (Control) | Best-studied EQL analog — solved geophysical mechanism |
| D | New Madrid Seismic Zone | Intraplate faults + published EQL/UAP correlation |

---

## Analysis Pipeline

1. **fetch/** — Download raw data per source, save to `data/raw/`
2. **process/geocode_manual.py** — Convert manual CSVs to standard GeoJSON
3. **process/normalize_all.py** — Enforce schema, reject invalid records
4. **process/merge_layers.py** — Combine into `output/combined.geojson`
5. **analyze/population_control.py** — Correct for population density bias
6. **analyze/clustering.py** — DBSCAN per layer + cross-layer convergence
7. **analyze/correlation.py** — Temporal co-occurrence + K-index correlation
8. **viz/generate_map.py** — Interactive Folium map for visual inspection

---

## Epistemic Framework

1. **No predetermined conclusion.** If nothing clusters non-randomly after population correction, that's a valid finding.
2. **Geophysical hypothesis first.** Earthquake lights, infrasound, radon effects, and EM phenomena from crustal stress are more parsimonious than exotic explanations.
3. **Confidence tiers enforced.** Tier 1 data drives the analysis. Tier 3 findings are contextual only.
4. **Population density is the primary confound.** Any clustering that doesn't survive population correction is not signal.
5. **The goal is novel cross-layer correlation** — if magnetic anomaly + UAP + UME all cluster in the same zone after population correction, that's the finding.

---

## Key References

- Thériault et al. (2014) — "Prevalence of earthquake lights associated with rift environments" — *Seismological Research Letters* — DOI: 10.1785/0220130059
- Freund (2003) — "Earthquake lights and stress-activation of positive hole charge carriers" — *Physics and Chemistry of the Earth*
- Vickery et al. (2023) — "Geomagnetic disturbance associated with increased vagrancy in migratory landbirds" — *Scientific Reports*
- Medina et al. (2022) — "An environmental analysis of public UAP sightings" — seismicity/UAP correlation
- Teodorani (2004) — "A long-term scientific survey of the Hessdalen phenomenon" — *Journal of Scientific Exploration*

---

*Phase 1 — Data Acquisition & Correlation Analysis*
*Next action: Run fetch scripts → clustering.py → evaluate signal before Phase 2*
