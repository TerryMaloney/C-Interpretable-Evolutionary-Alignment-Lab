import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';

// Layer group definitions — mirrors layer_registry.json layer_groups
const LAYER_GROUPS = {
  geophysical_baselines: {
    label: 'Geophysical Baselines',
    layers: ['usgs_seismic', 'usgs_magnetic', 'usgs_radon', 'grace_gravity', 'usgs_mines', 'water_wells'],
    defaultVisible: true,
    color: '#4488ff',
  },
  anomaly_reports: {
    label: 'Anomaly Reports',
    layers: ['nuforc', 'noaa_ume', 'cattle_mutilations', 'uso_incidents', 'bfro_sightings',
             'foia_documents', 'maritime_anomalies', 'bluebook_unknowns', 'geipan_cat_d',
             'belgian_triangle_wave', 'cefaa_cases', 'aatip_physiological',
             'foo_fighters_wwii', 'operation_prato'],
    defaultVisible: true,
    color: '#ff4455',
  },
  physics_detection: {
    label: 'Physics-Based Detection',
    layers: ['firms_thermal', 'dart_buoys', 'gps_tec', 'sentinel5p_atmos',
             'ctbto_infrasound', 'vlf_elf', 'goes_gravity_waves', 'schumann_resonance'],
    defaultVisible: false,
    color: '#9966ff',
  },
  biological_sensors: {
    label: 'Biological Sensors',
    layers: ['noaa_ume', 'movebank_animals', 'faa_wildlife_strikes', 'nav_disruption'],
    defaultVisible: false,
    color: '#44cc88',
  },
  infrastructure_context: {
    label: 'Infrastructure Context',
    layers: ['doe_grid', 'epa_radnet', 'nuclear_facilities', 'black_budget_sites', 'aerospace_facilities'],
    defaultVisible: false,
    color: '#ff8844',
  },
  computed_derived: {
    label: 'Computed / Derived',
    layers: ['uap_behavioral_taxonomy', 'uap_flap_centroids', 'vasco_observatories'],
    defaultVisible: false,
    color: '#cc88ff',
  },
  controls_masks: {
    label: 'Controls & Masks',
    layers: ['space_weather', 'adsb_traffic', 'nighttime_lights', 'faa_airspace',
             'solar_cycle_correlation', 'atmospheric_nuclear_tests'],
    defaultVisible: false,
    color: '#606078',
  },
};

// Investigation presets — curated layer + filter combinations for specific research modes
export const INVESTIGATION_PRESETS = {
  clean_signal: {
    id: 'clean_signal',
    label: 'Clean Signal Hunt',
    icon: '🔬',
    description: 'Tier 1 physics layers only. No self-report data. Highest signal:noise.',
    visibleLayers: new Set([
      'usgs_seismic', 'usgs_magnetic', 'usgs_radon', 'grace_gravity',
      'firms_thermal', 'dart_buoys', 'gps_tec', 'sentinel5p_atmos',
      'ctbto_infrasound', 'doe_grid', 'epa_radnet',
    ]),
    filters: {
      minConfidence: 4,
      hideMilitary: true,
      hideSolar: true,
      hideIndustrial: true,
    },
    mapView: 'convergence',
    sortMode: 'residual',
    convergenceRadius: 50,
  },
  skeptic: {
    id: 'skeptic',
    label: 'Skeptic Mode',
    icon: '⚖',
    description: 'All confound layers ON. Shows what disappears after controls applied.',
    visibleLayers: new Set([
      'usgs_seismic', 'usgs_magnetic', 'usgs_radon',
      'nuforc', 'noaa_ume', 'bfro_sightings',
      'faa_airspace', 'nighttime_lights', 'adsb_traffic',
      'space_weather', 'solar_cycle_correlation', 'atmospheric_nuclear_tests',
      'nuclear_facilities', 'doe_grid',
    ]),
    filters: {
      minConfidence: 1,
      hideMilitary: false,
      hideSolar: false,
      hideIndustrial: false,
    },
    mapView: 'heatmap',
    sortMode: 'confounded',
    convergenceRadius: 100,
  },
  physical_effects: {
    id: 'physical_effects',
    label: 'Physical Effects',
    icon: '⚡',
    description: 'Cases with documented physical traces: radar, FLIR, physiological, material.',
    visibleLayers: new Set([
      'bluebook_unknowns', 'geipan_cat_d', 'belgian_triangle_wave',
      'cefaa_cases', 'aatip_physiological', 'foia_documents',
      'usgs_seismic', 'usgs_magnetic', 'usgs_radon',
      'epa_radnet', 'doe_grid',
    ]),
    filters: {
      minConfidence: 3,
      hideMilitary: false,
      hideSolar: true,
      hideIndustrial: false,
    },
    mapView: 'layers',
    sortMode: 'convergence',
    convergenceRadius: 75,
  },
  low_report_weirdness: {
    id: 'low_report_weirdness',
    label: 'Low-Report Weirdness',
    icon: '🌐',
    description: 'Physical instrument anomalies in low-population areas. No self-report bias.',
    visibleLayers: new Set([
      'dart_buoys', 'gps_tec', 'ctbto_infrasound', 'schumann_resonance',
      'usgs_seismic', 'usgs_magnetic', 'vlf_elf', 'goes_gravity_waves',
      'movebank_animals', 'faa_wildlife_strikes',
    ]),
    filters: {
      minConfidence: 3,
      hideMilitary: true,
      hideSolar: true,
      hideIndustrial: true,
    },
    mapView: 'convergence',
    sortMode: 'low_report',
    convergenceRadius: 50,
  },
};

// High-N layers that would visually swamp the map if on by default (still toggleable).
const NEVER_DEFAULT_VISIBLE = new Set(['water_wells']);

// Build initial visible-layers set from defaults
const buildDefaultVisible = () => {
  const visible = new Set();
  for (const [, group] of Object.entries(LAYER_GROUPS)) {
    if (group.defaultVisible) {
      group.layers.forEach(l => { if (!NEVER_DEFAULT_VISIBLE.has(l)) visible.add(l); });
    }
  }
  return visible;
};

export const MAP_VIEWS = {
  RESIDUAL: 'residual',    // Default: after population + military + solar + industrial masking
  HEATMAP: 'heatmap',      // Raw density heatmap
  CONVERGENCE: 'convergence', // C-Score grid overlay
  LAYERS: 'layers',        // Individual layer dots
};

export const useStore = create(
  subscribeWithSelector((set, get) => ({
    // ── Map state ─────────────────────────────────────────────────────────────
    mapView: MAP_VIEWS.RESIDUAL,
    viewState: {
      longitude: -106.5,
      latitude: 37.5,
      zoom: 5,
      pitch: 0,
      bearing: 0,
    },

    // ── Layer visibility ──────────────────────────────────────────────────────
    layerGroups: LAYER_GROUPS,
    visibleLayers: buildDefaultVisible(),

    // ── Data ──────────────────────────────────────────────────────────────────
    registry: null,
    layerData: {},         // { layerName: GeoJSON FeatureCollection }
    convergenceData: null, // convergence_scores.geojson
    dbReady: false,

    // ── UI state ──────────────────────────────────────────────────────────────
    selectedFeature: null,
    hoveredFeature: null,
    panelOpen: true,
    searchQuery: '',
    activeZone: null,
    showCScoreOverlay: false,
    convergenceRadius: 50,  // km
    isLoading: false,
    loadingMessage: '',
    error: null,
    sortMode: 'convergence',  // convergence | residual | confounded | low_report | physical
    activePreset: null,        // id of active investigation preset, or null

    // ── Alignment overlay (spatial "ley line" detection + null test) ───────────
    showAlignments: false,
    showAlignmentControl: false,  // negative-control overlay (random null realization)
    alignmentData: null,          // alignments.geojson
    alignmentControlData: null,   // alignments_control.geojson
    bearingData: null,            // alignment_bearings.json (orientation rose)

    // ── Time-slider animation ──────────────────────────────────────────────────
    timeFilter: { enabled: false, current: null, window: 5 },  // window = trailing years

    // ── Filters ───────────────────────────────────────────────────────────────
    filters: {
      minConfidence: 1,
      dateRange: [null, null],
      categories: new Set(),
      hideMilitary: false,
      hideSolar: false,
      hideIndustrial: false,
    },

    // ── Actions ───────────────────────────────────────────────────────────────
    setMapView: (view) => set({ mapView: view }),

    setViewState: (viewState) => set({ viewState }),

    toggleLayer: (layerName) => set(state => {
      const next = new Set(state.visibleLayers);
      if (next.has(layerName)) next.delete(layerName);
      else next.add(layerName);
      return { visibleLayers: next };
    }),

    toggleLayerGroup: (groupKey) => set(state => {
      const group = state.layerGroups[groupKey];
      if (!group) return {};
      const allVisible = group.layers.every(l => state.visibleLayers.has(l));
      const next = new Set(state.visibleLayers);
      if (allVisible) {
        group.layers.forEach(l => next.delete(l));
      } else {
        group.layers.forEach(l => next.add(l));
      }
      return { visibleLayers: next };
    }),

    setRegistry: (registry) => set({ registry }),

    setLayerData: (layerName, data) => set(state => ({
      layerData: { ...state.layerData, [layerName]: data },
    })),

    setConvergenceData: (data) => set({ convergenceData: data }),

    setShowAlignments: (show) => set({ showAlignments: show }),
    setShowAlignmentControl: (show) => set({ showAlignmentControl: show }),
    setAlignmentData: (data) => set({ alignmentData: data }),
    setAlignmentControlData: (data) => set({ alignmentControlData: data }),
    setBearingData: (data) => set({ bearingData: data }),

    setTimeFilter: (patch) => set(state => ({ timeFilter: { ...state.timeFilter, ...patch } })),

    setDbReady: (ready) => set({ dbReady: ready }),

    selectFeature: (feature) => set({ selectedFeature: feature }),

    hoverFeature: (feature) => set({ hoveredFeature: feature }),

    setPanelOpen: (open) => set({ panelOpen: open }),

    setSearchQuery: (q) => set({ searchQuery: q }),

    setActiveZone: (zoneId) => set({ activeZone: zoneId }),

    setShowCScoreOverlay: (show) => set({ showCScoreOverlay: show }),

    setConvergenceRadius: (r) => set({ convergenceRadius: r }),

    setLoading: (isLoading, message = '') => set({ isLoading, loadingMessage: message }),

    setError: (error) => set({ error }),

    setSortMode: (mode) => set({ sortMode: mode }),

    applyPreset: (presetId) => {
      const preset = INVESTIGATION_PRESETS[presetId];
      if (!preset) {
        set({ activePreset: null });
        return;
      }
      set(state => ({
        activePreset: presetId,
        visibleLayers: new Set(preset.visibleLayers),
        mapView: preset.mapView || state.mapView,
        sortMode: preset.sortMode || state.sortMode,
        convergenceRadius: preset.convergenceRadius || state.convergenceRadius,
        filters: { ...state.filters, ...preset.filters },
      }));
    },

    clearPreset: () => set({ activePreset: null }),

    // Used by URL sync to restore layer state from URL params
    setVisibleLayersFromUrl: (layerSet) => set({ visibleLayers: layerSet }),

    updateFilter: (key, value) => set(state => ({
      filters: { ...state.filters, [key]: value },
    })),

    // Navigate map to a zone
    flyToZone: (zoneId, zones) => {
      const zone = zones?.[zoneId];
      if (!zone) return;
      const bbox = zone.bbox;
      const centerLat = (bbox.min_lat + bbox.max_lat) / 2;
      const centerLon = (bbox.min_lon + bbox.max_lon) / 2;
      const latSpan = bbox.max_lat - bbox.min_lat;
      const lonSpan = bbox.max_lon - bbox.min_lon;
      const zoom = Math.min(8, Math.log2(360 / Math.max(latSpan, lonSpan)) + 1);
      set({
        viewState: { longitude: centerLon, latitude: centerLat, zoom, pitch: 0, bearing: 0 },
        activeZone: zoneId,
      });
    },

    // Get all visible features across loaded layers
    getVisibleFeatures: () => {
      const { visibleLayers, layerData, filters } = get();
      const features = [];
      for (const layerName of visibleLayers) {
        const data = layerData[layerName];
        if (!data?.features) continue;
        for (const f of data.features) {
          const conf = f.properties?.confidence ?? 0;
          if (conf < filters.minConfidence) continue;
          features.push({ ...f, _layer: layerName });
        }
      }
      return features;
    },
  }))
);
