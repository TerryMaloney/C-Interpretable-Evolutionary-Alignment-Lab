import React from 'react';
import { useStore, MAP_VIEWS } from '../store/useStore.js';
import styles from './Header.module.css';

const VIEW_LABELS = {
  [MAP_VIEWS.RESIDUAL]: 'Residual Map',
  [MAP_VIEWS.HEATMAP]: 'Density Heatmap',
  [MAP_VIEWS.CONVERGENCE]: 'C-Score Grid',
  [MAP_VIEWS.LAYERS]: 'Layer Dots',
};

const ZONES = [
  { id: 'A', name: 'Zone A — Rocky Mountain Rift', center: [-107.5, 37.5], zoom: 7 },
  { id: 'B', name: 'Zone B — Southern CA Offshore', center: [-119.0, 33.5], zoom: 7 },
  { id: 'C', name: 'Zone C — Hessdalen', center: [11.2, 62.8], zoom: 10 },
  { id: 'D', name: 'Zone D — New Madrid', center: [-89.5, 36.5], zoom: 7 },
  { id: 'E', name: 'Zone E — Japan Trench', center: [143.0, 38.0], zoom: 6 },
];

export default function Header() {
  const { mapView, setMapView, setViewState, showCScoreOverlay, setShowCScoreOverlay } = useStore();

  const flyTo = (center, zoom) => {
    setViewState({ longitude: center[0], latitude: center[1], zoom, pitch: 0, bearing: 0 });
  };

  return (
    <header className={styles.header}>
      <div className={styles.brand}>
        <span className={styles.logo}>◈</span>
        <span className={styles.title}>Anomalous Phenomena Correlation Map</span>
      </div>

      <nav className={styles.views}>
        {Object.entries(VIEW_LABELS).map(([view, label]) => (
          <button
            key={view}
            className={`${styles.viewBtn} ${mapView === view ? styles.active : ''}`}
            onClick={() => setMapView(view)}
            title={view === MAP_VIEWS.RESIDUAL
              ? 'After population + military + solar + industrial masking — what remains is unexplained signal'
              : undefined}
          >
            {label}
          </button>
        ))}
      </nav>

      <div className={styles.zones}>
        {ZONES.map(z => (
          <button
            key={z.id}
            className={styles.zoneBtn}
            onClick={() => flyTo(z.center, z.zoom)}
            title={z.name}
          >
            {z.id}
          </button>
        ))}
      </div>

      <button
        className={`${styles.overlayToggle} ${showCScoreOverlay ? styles.active : ''}`}
        onClick={() => setShowCScoreOverlay(!showCScoreOverlay)}
        title="Toggle C-Score convergence grid overlay"
      >
        ⬡ C-Score
      </button>
    </header>
  );
}
