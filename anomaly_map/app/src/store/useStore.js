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
             'foia_documents', 'maritime_anomalies'],
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
    layers: ['doe_grid', 'epa_radnet', 'nuclear_facilities', 'black_budget_sites'],
    defaultVisible: false,
    color: '#ff8844',
  },
  controls_masks: {
    label: 'Controls & Masks',
    layers: ['space_weather', 'adsb_traffic', 'nighttime_lights', 'faa_airspace'],
    defaultVisible: false,
    color: '#606078',
  },
};

// Build initial visible-layers set from defaults
const buildDefaultVisible = () => {
  const visible = new Set();
  for (const [, group] of Object.entries(LAYER_GROUPS)) {
    if (group.defaultVisible) {
      group.layers.forEach(l => visible.add(l));
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
