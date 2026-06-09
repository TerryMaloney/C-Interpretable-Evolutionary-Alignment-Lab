import React, { useMemo, useState } from 'react';
import { useStore } from '../store/useStore.js';
import { cScoreLabel } from '../analysis/convergenceScore.js';
import styles from './HotspotsList.module.css';

const NOISE_COLOR = { Low: '#50ff78', Medium: '#ffb400', High: '#ff5050' };

export default function HotspotsList() {
  const { convergenceData, setViewState, selectFeature, sortMode } = useStore();
  const [expanded, setExpanded] = useState(true);

  const hotspots = useMemo(() => {
    if (!convergenceData?.features?.length) return [];

    return [...convergenceData.features]
      .filter(f => f.properties?.cScore > 0)
      .sort((a, b) => {
        const ap = a.properties, bp = b.properties;
        if (sortMode === 'residual') {
          // Sort by cScore minus noise proxy
          const aR = ap.cScore * (ap.noiseLabel === 'Low' ? 1 : ap.noiseLabel === 'Medium' ? 0.6 : 0.3);
          const bR = bp.cScore * (bp.noiseLabel === 'Low' ? 1 : bp.noiseLabel === 'Medium' ? 0.6 : 0.3);
          return bR - aR;
        }
        return bp.cScore - ap.cScore;
      })
      .slice(0, 10);
  }, [convergenceData, sortMode]);

  const flyTo = (feature) => {
    const [lon, lat] = feature.geometry.coordinates;
    setViewState({ longitude: lon, latitude: lat, zoom: 8, pitch: 0, bearing: 0 });
    selectFeature(feature);
  };

  if (!convergenceData) {
    return (
      <div className={styles.section}>
        <div className={styles.sectionHeader}>
          <span className={styles.sectionTitle}>Top Hotspots</span>
        </div>
        <div className={styles.placeholder}>Run convergence_score.py to compute</div>
      </div>
    );
  }

  return (
    <div className={styles.section}>
      <button className={styles.sectionHeader} onClick={() => setExpanded(v => !v)}>
        <span className={styles.sectionTitle}>Top Hotspots</span>
        <span className={styles.count}>{hotspots.length}</span>
        <span className={styles.caret}>{expanded ? '▾' : '▸'}</span>
      </button>

      {expanded && (
        <div className={styles.list}>
          {hotspots.length === 0 && (
            <div className={styles.placeholder}>No hotspots computed yet</div>
          )}
          {hotspots.map((feature, i) => {
            const p = feature.properties || {};
            const [lon, lat] = feature.geometry?.coordinates || [0, 0];
            const label = cScoreLabel(p.cScore);
            const noiseColor = NOISE_COLOR[p.noiseLabel] || '#888';
            const zoneSlug = p.zone_slug;

            return (
              <button
                key={i}
                className={styles.hotspotRow}
                onClick={() => flyTo(feature)}
                title={`${lat.toFixed(3)}, ${lon.toFixed(3)} — C-Score ${p.cScore?.toFixed(2)}`}
              >
                <span className={styles.rank}>#{i + 1}</span>
                <div className={styles.hotspotInfo}>
                  <div className={styles.hotspotCoords}>
                    {lat.toFixed(2)}°{lat >= 0 ? 'N' : 'S'}, {Math.abs(lon).toFixed(2)}°{lon >= 0 ? 'E' : 'W'}
                    {zoneSlug && <span className={styles.zoneTag}>{zoneSlug}</span>}
                  </div>
                  <div className={styles.hotspotMeta}>
                    <span className={styles.layers}>{p.layerCount ?? '?'} layers</span>
                    {p.noiseLabel && (
                      <span className={styles.noise} style={{ color: noiseColor }}>
                        {p.noiseLabel} noise
                      </span>
                    )}
                  </div>
                </div>
                <div className={styles.scoreCol}>
                  <span
                    className={styles.cScore}
                    style={{ color: label?.color || '#fff' }}
                  >
                    {p.cScore?.toFixed(1)}
                  </span>
                  <span className={styles.scoreTag}>C</span>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
