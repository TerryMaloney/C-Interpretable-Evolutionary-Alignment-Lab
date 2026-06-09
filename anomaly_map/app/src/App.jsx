import React, { useEffect, useRef, useCallback } from 'react';
import { useStore } from './store/useStore.js';
import Map from './components/Map.jsx';
import LayerPanel from './components/LayerPanel.jsx';
import DetailPanel from './components/DetailPanel.jsx';
import Header from './components/Header.jsx';
import LoadingOverlay from './components/LoadingOverlay.jsx';
import styles from './App.module.css';

// Data paths — adjust to match your output/ directory or a static server
const DATA_BASE = '/data/processed';
const REGISTRY_PATH = '/data/layer_registry.json';
const CONVERGENCE_PATH = '/output/analysis/convergence_scores.geojson';

// Layers to eagerly load on startup (others loaded on demand)
const EAGER_LAYERS = [
  'nuforc', 'noaa_ume', 'usgs_seismic', 'usgs_magnetic',
  'faa_airspace', 'nighttime_lights',
];

export default function App() {
  const {
    setRegistry, setLayerData, setConvergenceData,
    setLoading, setError, visibleLayers, layerData,
  } = useStore();

  const loadedLayers = useRef(new Set());

  // Load registry on mount
  useEffect(() => {
    setLoading(true, 'Loading layer registry…');
    fetch(REGISTRY_PATH)
      .then(r => r.json())
      .then(registry => {
        setRegistry(registry);
        setLoading(false);
      })
      .catch(err => {
        console.error('Registry load failed:', err);
        setLoading(false);
        // Don't block on registry failure — app still works with curated data
      });
  }, [setRegistry, setLoading]);

  // Lazy-load layer GeoJSON when it becomes visible
  useEffect(() => {
    for (const layerName of visibleLayers) {
      if (loadedLayers.current.has(layerName)) continue;
      if (layerData[layerName]) continue;

      loadedLayers.current.add(layerName);
      const url = `${DATA_BASE}/${layerName}.geojson`;

      fetch(url)
        .then(r => {
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          return r.json();
        })
        .then(gj => {
          setLayerData(layerName, gj);
        })
        .catch(err => {
          console.warn(`Layer ${layerName} not loaded: ${err.message}`);
          // Silently skip missing layers
        });
    }
  }, [visibleLayers, layerData, setLayerData]);

  // Load convergence scores
  useEffect(() => {
    fetch(CONVERGENCE_PATH)
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(gj => setConvergenceData(gj))
      .catch(() => {
        // Not available until pipeline has run — silent
      });
  }, [setConvergenceData]);

  return (
    <div className={styles.app}>
      <Header />
      <div className={styles.body}>
        <LayerPanel />
        <Map />
        <DetailPanel />
      </div>
      <LoadingOverlay />
    </div>
  );
}
