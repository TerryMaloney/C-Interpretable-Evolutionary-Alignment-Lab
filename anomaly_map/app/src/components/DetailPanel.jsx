import React, { useMemo } from 'react';
import { useStore } from '../store/useStore.js';
import { computeCScore, cScoreLabel } from '../analysis/convergenceScore.js';
import { getCategoryColor } from '../utils/layers.js';
import styles from './DetailPanel.module.css';

export default function DetailPanel() {
  const {
    selectedFeature, selectFeature,
    layerData, registry, convergenceRadius,
    setConvergenceRadius,
  } = useStore();

  // Compute C-Score for selected feature location
  const cScoreResult = useMemo(() => {
    if (!selectedFeature) return null;
    const coords = selectedFeature.geometry?.coordinates || selectedFeature.position;
    if (!coords) return null;
    const [lon, lat] = coords;
    return computeCScore(lat, lon, layerData, registry, convergenceRadius);
  }, [selectedFeature, layerData, registry, convergenceRadius]);

  if (!selectedFeature) return null;

  const props = selectedFeature.properties || {};
  const coords = selectedFeature.geometry?.coordinates;
  const color = getCategoryColor(props.category);
  const colorStr = `rgb(${color.join(',')})`;

  const cLabel = cScoreResult ? cScoreLabel(cScoreResult.cScore) : null;

  return (
    <aside className={styles.panel}>
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <span className={styles.layerBadge} style={{ background: colorStr + '22', color: colorStr, borderColor: colorStr + '44' }}>
            {props.layer || 'Unknown'}
          </span>
          <span className={styles.category}>{props.category}</span>
        </div>
        <button className={styles.closeBtn} onClick={() => selectFeature(null)}>✕</button>
      </div>

      <div className={styles.body}>
        {/* Coordinates */}
        {coords && (
          <div className={styles.coords}>
            <span className={styles.coordLabel}>LAT</span>
            <span className={styles.coordValue}>{coords[1]?.toFixed(4)}</span>
            <span className={styles.coordLabel}>LON</span>
            <span className={styles.coordValue}>{coords[0]?.toFixed(4)}</span>
          </div>
        )}

        {/* C-Score */}
        {cScoreResult && (
          <div className={styles.cscore}>
            <div className={styles.cscoreHeader}>
              <span className={styles.cscoreLabel}>Convergence Score</span>
              <div className={styles.radiusControl}>
                <label>R=</label>
                <select
                  value={convergenceRadius}
                  onChange={e => setConvergenceRadius(Number(e.target.value))}
                  className={styles.radiusSelect}
                >
                  {[25, 50, 75, 100, 150].map(r => (
                    <option key={r} value={r}>{r}km</option>
                  ))}
                </select>
              </div>
            </div>
            <div className={styles.cscoreValue}>
              <span style={{ color: cLabel.color }}>{cScoreResult.cScore.toFixed(2)}</span>
              <span className={styles.cscoreMax}>/10</span>
              <span className={styles.cscoreBadge} style={{ background: cLabel.color + '22', color: cLabel.color }}>
                {cLabel.label}
              </span>
            </div>
            <div className={styles.cscoreMeta}>
              {cScoreResult.layerCount} independent layers converging
            </div>

            {/* Penalties */}
            {(cScoreResult.penalties.military || cScoreResult.penalties.solar || cScoreResult.penalties.industrial) && (
              <div className={styles.penalties}>
                {cScoreResult.penalties.military && (
                  <span className={styles.penalty}>⚠ Military zone (×{cScoreResult.penalties.militaryFactor.toFixed(1)})</span>
                )}
                {cScoreResult.penalties.solar && (
                  <span className={styles.penalty}>☀ High Kp (×{cScoreResult.penalties.solarFactor.toFixed(1)})</span>
                )}
                {cScoreResult.penalties.industrial && (
                  <span className={styles.penalty}>💡 Industrial zone (×{cScoreResult.penalties.industrialFactor.toFixed(1)})</span>
                )}
              </div>
            )}

            {/* Layer breakdown */}
            {cScoreResult.layers.length > 0 && (
              <div className={styles.breakdown}>
                <div className={styles.breakdownTitle}>Contributing layers</div>
                {cScoreResult.layers.slice(0, 8).map(l => {
                  const lColor = getCategoryColor(l.category);
                  const lColorStr = `rgb(${lColor.join(',')})`;
                  return (
                    <div key={l.name} className={styles.breakdownRow}>
                      <span className={styles.breakdownDot} style={{ background: lColorStr }} />
                      <span className={styles.breakdownName}>{l.label || l.name}</span>
                      <span className={styles.breakdownHits}>{l.hitCount}</span>
                      <span className={styles.breakdownTier}>T{l.tier}</span>
                    </div>
                  );
                })}
                {cScoreResult.layers.length > 8 && (
                  <div className={styles.breakdownMore}>+{cScoreResult.layers.length - 8} more</div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Source */}
        {props.source && (
          <div className={styles.field}>
            <span className={styles.fieldLabel}>SOURCE</span>
            <span className={styles.fieldValue}>{props.source}</span>
          </div>
        )}

        {/* Confidence */}
        {props.confidence != null && (
          <div className={styles.field}>
            <span className={styles.fieldLabel}>CONFIDENCE</span>
            <span className={styles.fieldValue}>
              {'★'.repeat(props.confidence)}{'☆'.repeat(5 - props.confidence)} ({props.confidence}/5)
            </span>
          </div>
        )}

        {/* Datetime */}
        {props.datetime && (
          <div className={styles.field}>
            <span className={styles.fieldLabel}>DATE/TIME</span>
            <span className={styles.fieldValue}>{props.datetime}</span>
          </div>
        )}

        {/* Notes */}
        {props.notes && (
          <div className={styles.notes}>
            <span className={styles.fieldLabel}>NOTES</span>
            <p className={styles.notesText}>{props.notes}</p>
          </div>
        )}

        {/* Extra properties */}
        {props.extra && Object.keys(props.extra).length > 0 && (
          <div className={styles.extra}>
            <span className={styles.fieldLabel}>PROPERTIES</span>
            {Object.entries(props.extra)
              .filter(([, v]) => v != null && v !== false && v !== '')
              .map(([k, v]) => (
                <div key={k} className={styles.extraRow}>
                  <span className={styles.extraKey}>{k}</span>
                  <span className={styles.extraVal}>{String(v)}</span>
                </div>
              ))}
          </div>
        )}
      </div>
    </aside>
  );
}
