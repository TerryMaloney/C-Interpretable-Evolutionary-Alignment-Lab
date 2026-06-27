import React from 'react';
import { useStore, MAP_VIEWS } from '../store/useStore.js';
import { useNearMe } from '../hooks/useNearMe.js';
import styles from './MapHeader.module.css';

const VIEW_LABELS = {
  [MAP_VIEWS.RESIDUAL]:    'Residual Map',
  [MAP_VIEWS.HEATMAP]:     'Density',
  [MAP_VIEWS.CONVERGENCE]: 'C-Score Grid',
  [MAP_VIEWS.LAYERS]:      'Layer Dots',
};

const ZONES = [
  { id: 'A', name: 'Zone A — Rocky Mountain Rift',     center: [-107.5, 37.5], zoom: 7 },
  { id: 'B', name: 'Zone B — Southern CA Offshore',    center: [-119.0, 33.5], zoom: 7 },
  { id: 'C', name: 'Zone C — Hessdalen (control)',     center: [11.2, 62.8],   zoom: 10 },
  { id: 'D', name: 'Zone D — New Madrid',              center: [-89.5, 36.5],  zoom: 7 },
  { id: 'E', name: 'Zone E — Japan Trench (validation)', center: [143.0, 38.0], zoom: 6 },
];

const SORT_MODES = [
  { id: 'convergence',  label: 'Top Convergence' },
  { id: 'residual',     label: 'Cleanest Residuals' },
  { id: 'confounded',   label: 'Most Confounded' },
  { id: 'low_report',   label: 'Low-Report Weirdness' },
  { id: 'physical',     label: 'Physical Effects' },
];

export default function MapHeader() {
  const {
    mapView, setMapView, setViewState,
    showCScoreOverlay, setShowCScoreOverlay,
    showAlignments, setShowAlignments,
    showAlignmentControl, setShowAlignmentControl,
    sortMode, setSortMode,
  } = useStore();

  const { locate, position, loading: locating, error: locError } = useNearMe();

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
              ? 'Population + military + solar + industrial masks applied — shows unexplained residual'
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

      <select
        className={styles.sortSelect}
        value={sortMode || 'convergence'}
        onChange={e => setSortMode(e.target.value)}
        title="Sort hotspots by"
      >
        {SORT_MODES.map(s => (
          <option key={s.id} value={s.id}>{s.label}</option>
        ))}
      </select>

      <button
        className={`${styles.overlayToggle} ${showCScoreOverlay ? styles.active : ''}`}
        onClick={() => setShowCScoreOverlay(!showCScoreOverlay)}
        title="Toggle C-Score convergence grid overlay"
      >
        ⬡ C-Score
      </button>

      <button
        className={`${styles.overlayToggle} ${showAlignments ? styles.active : ''}`}
        onClick={() => setShowAlignments(!showAlignments)}
        title="Toggle spatial alignment detection. Bold/hot = survives the null test; faint = consistent with chance."
      >
        ⟋ Alignments
      </button>

      {showAlignments && (
        <button
          className={`${styles.overlayToggle} ${showAlignmentControl ? styles.active : ''}`}
          onClick={() => setShowAlignmentControl(!showAlignmentControl)}
          title="Negative control: 'alignments' found in randomized points. If these look just as convincing, the real ones aren't special."
        >
          🎲 Control
        </button>
      )}

      <button
        className={`${styles.nearMeBtn} ${position ? styles.active : ''}`}
        onClick={locate}
        disabled={locating}
        title={locError || (position ? `At ${position.lat.toFixed(3)}, ${position.lon.toFixed(3)}` : 'Jump to my location')}
      >
        {locating ? '…' : position ? '⊙ Near Me' : '◎ Near Me'}
      </button>
    </header>
  );
}
