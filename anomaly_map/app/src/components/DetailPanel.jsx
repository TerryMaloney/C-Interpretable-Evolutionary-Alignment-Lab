import React, { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useStore } from '../store/useStore.js';
import { computeCScore, cScoreLabel } from '../analysis/convergenceScore.js';
import { getCategoryColor } from '../utils/layers.js';
import styles from './DetailPanel.module.css';

// Claim Level ladder
const CLAIM_LEVELS = [
  '',
  'Visual cluster only',
  'Survives population correction',
  'Survives pop + military masking',
  'Multiple Tier 1 layers converge',
  'Spatial + temporal convergence',
  'Survives negative controls',
];

function computeClaimLevel(cScoreResult, props) {
  if (!cScoreResult || cScoreResult.cScore <= 0) return 1;
  let level = 1;

  // Level 2: population correction applied
  if (cScoreResult.populationCorrected) level = 2;

  // Level 3: military + industrial masks applied
  if (level >= 2 && (cScoreResult.penalties.military || cScoreResult.penalties.industrial)) level = 3;

  // Level 4: 2+ independent Tier 1 layers
  const tier1Layers = (cScoreResult.layers || []).filter(l => l.tier === 1);
  if (tier1Layers.length >= 2) level = Math.max(level, 4);

  // Level 5: temporal overlap (needs datetime on selected feature and convergence)
  if (level >= 4 && props.datetime && cScoreResult.temporalOverlap) level = 5;

  // Level 6: explicit negative controls passed
  if (cScoreResult.negativeControlsPassed) level = 6;

  return Math.min(level, 6);
}

function computeNoiseScore(cScoreResult, props) {
  if (!cScoreResult) return 'Unknown';
  let noisePts = 0;
  const factors = [];

  if (cScoreResult.penalties.military) { noisePts += 3; factors.push('military zone'); }
  if (cScoreResult.penalties.industrial) { noisePts += 2; factors.push('industrial area'); }
  if (cScoreResult.penalties.solar) { noisePts += 1; factors.push('solar activity'); }
  if ((props.confidence || 3) < 3) { noisePts += 1; factors.push('low confidence source'); }

  const layer = props.layer || '';
  if (layer.includes('nuforc') || layer.includes('bfro')) { noisePts += 1; factors.push('self-reported data'); }
  if (layer.includes('nighttime') || layer.includes('adsb')) { noisePts += 1; factors.push('coverage bias proxy'); }

  if (noisePts >= 4) return { label: 'High', factors, color: '#ff5050' };
  if (noisePts >= 2) return { label: 'Medium', factors, color: '#ffb400' };
  return { label: 'Low', factors, color: '#50ff78' };
}

function RealityChecks({ cScoreResult, props }) {
  const mil = cScoreResult?.penalties?.military;
  const solar = cScoreResult?.penalties?.solar;
  const ind = cScoreResult?.penalties?.industrial;
  const tier1Count = (cScoreResult?.layers || []).filter(l => l.tier === 1).length;
  const hasPopCorrect = cScoreResult?.populationCorrected;
  const layer = props.layer || '';
  const isCoastal = props.notes?.toLowerCase().includes('coast') || props.notes?.toLowerCase().includes('offshore');
  const isAirport = props.notes?.toLowerCase().includes('airport') || props.notes?.toLowerCase().includes('faa');
  const hasDt = !!props.datetime;
  const isDuplRisk = layer.includes('nuforc') || layer.includes('bfro');
  const negCtrl = cScoreResult?.negativeControlsPassed;

  const checks = [
    { label: 'Population correction', status: hasPopCorrect ? 'pass' : 'unknown', icon: '👥' },
    { label: 'Military/restricted airspace', status: mil ? 'warn' : 'pass', icon: '⚡', note: mil ? 'Applies — reduces confidence' : undefined },
    { label: 'Industrial/source contamination', status: ind ? 'warn' : 'pass', icon: '🏭', note: ind ? 'Applies — industrial area nearby' : undefined },
    { label: 'Airport/flight corridor', status: isAirport ? 'warn' : 'unknown', icon: '✈', note: isAirport ? 'Airport proximity detected' : undefined },
    { label: 'Coastal/shipping bias', status: isCoastal ? 'warn' : 'unknown', icon: '🌊', note: isCoastal ? 'Coastal zone — observation density elevated' : undefined },
    { label: 'Known geology', status: tier1Count >= 1 ? 'pass' : 'unknown', icon: '🪨', note: tier1Count >= 1 ? `${tier1Count} geophysical Tier 1 layers present` : undefined },
    { label: 'Reporting bias risk', status: isDuplRisk ? 'warn' : 'pass', icon: '📊', note: isDuplRisk ? 'Self-reported database — bias present' : undefined },
    { label: 'Duplicate report risk', status: isDuplRisk ? 'warn' : 'unknown', icon: '📋', note: isDuplRisk ? 'Multiple self-reports from same event possible' : undefined },
    { label: 'Temporal overlap confirmed', status: hasDt ? 'unknown' : 'unknown', icon: '🕐', note: hasDt ? 'Date present; temporal clustering not yet computed' : 'No timestamp available' },
    { label: 'Negative controls run', status: negCtrl === true ? 'pass' : 'unknown', icon: '⚖', note: negCtrl ? 'Survives negative controls' : 'Not yet run' },
  ];

  return (
    <div className={styles.realityChecks}>
      <div className={styles.checkTitle}>Reality Checks</div>
      {checks.map(c => (
        <div key={c.label} className={`${styles.checkRow} ${styles[`check_${c.status}`]}`}>
          <span className={styles.checkIcon}>{c.icon}</span>
          <span className={styles.checkLabel}>{c.label}</span>
          <span className={styles.checkStatus}>
            {c.status === 'pass' ? '✓' : c.status === 'warn' ? '△' : '?'}
          </span>
          {c.note && <span className={styles.checkNote}>{c.note}</span>}
        </div>
      ))}
    </div>
  );
}

export default function DetailPanel() {
  const {
    selectedFeature, selectFeature,
    layerData, registry, convergenceRadius,
    setConvergenceRadius,
  } = useStore();

  const [showChecks, setShowChecks] = useState(false);

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

  const claimLevel = computeClaimLevel(cScoreResult, props);
  const noiseScore = computeNoiseScore(cScoreResult, props);
  const noiseLabel = typeof noiseScore === 'object' ? noiseScore.label : noiseScore;
  const noiseColor = typeof noiseScore === 'object' ? noiseScore.color : '#aaa';
  const noiseFactors = typeof noiseScore === 'object' ? noiseScore.factors : [];

  // Residual interest heuristic
  const residualInterest = noiseLabel === 'Low' && cScoreResult?.cScore >= 4 ? 'High'
    : noiseLabel === 'Medium' && cScoreResult?.cScore >= 3 ? 'Medium'
    : cScoreResult?.cScore >= 5 && noiseLabel === 'High' ? 'Medium'
    : 'Low';
  const residualColor = residualInterest === 'High' ? '#50ff78' : residualInterest === 'Medium' ? '#ffb400' : '#888';

  const zoneSlug = props.zone_slug || null;
  const feedbackUrl = `/feedback?zone=${zoneSlug || ''}&type=bad_data_report`;

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

        {/* Score row: C-Score + Claim Level + Noise + Residual */}
        {cScoreResult && (
          <div className={styles.scoreBlock}>
            <div className={styles.scoreRow}>
              <div className={styles.scorePill}>
                <span className={styles.scoreNum} style={{ color: cLabel?.color || '#fff' }}>
                  {cScoreResult.cScore.toFixed(2)}
                </span>
                <span className={styles.scoreTag}>C-Score</span>
              </div>
              <div className={styles.scorePill}>
                <span className={styles.scoreNum} style={{ color: noiseColor }}>{noiseLabel}</span>
                <span className={styles.scoreTag}>Noise</span>
              </div>
              <div className={styles.scorePill}>
                <span className={styles.scoreNum} style={{ color: residualColor }}>{residualInterest}</span>
                <span className={styles.scoreTag}>Residual</span>
              </div>
            </div>

            {/* Claim Level badge */}
            <div className={`${styles.claimBadge} ${styles[`claim${claimLevel}`]}`}>
              <span className={styles.claimNum}>Level {claimLevel}</span>
              <span className={styles.claimDesc}>{CLAIM_LEVELS[claimLevel]}</span>
            </div>

            {/* Noise factor pills */}
            {noiseFactors.length > 0 && (
              <div className={styles.noiseFactors}>
                {noiseFactors.map(f => (
                  <span key={f} className={styles.noiseFactor}>{f}</span>
                ))}
              </div>
            )}

            {/* Radius control */}
            <div className={styles.radiusRow}>
              <span className={styles.radiusLabel}>Convergence radius</span>
              <select
                value={convergenceRadius}
                onChange={e => setConvergenceRadius(Number(e.target.value))}
                className={styles.radiusSelect}
              >
                {[25, 50, 75, 100, 150].map(r => (
                  <option key={r} value={r}>{r}km</option>
                ))}
              </select>
              <span className={styles.radiusMeta}>{cScoreResult.layerCount} layers</span>
            </div>

            {/* Penalties */}
            {(cScoreResult.penalties.military || cScoreResult.penalties.solar || cScoreResult.penalties.industrial) && (
              <div className={styles.penalties}>
                {cScoreResult.penalties.military && (
                  <span className={styles.penalty}>⚠ Military ×{cScoreResult.penalties.militaryFactor?.toFixed(1)}</span>
                )}
                {cScoreResult.penalties.solar && (
                  <span className={styles.penalty}>☀ Solar ×{cScoreResult.penalties.solarFactor?.toFixed(1)}</span>
                )}
                {cScoreResult.penalties.industrial && (
                  <span className={styles.penalty}>💡 Industrial ×{cScoreResult.penalties.industrialFactor?.toFixed(1)}</span>
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

            {/* Reality Checks toggle */}
            <button
              className={styles.checksToggle}
              onClick={() => setShowChecks(v => !v)}
            >
              {showChecks ? '▴' : '▾'} Reality Checks
            </button>
            {showChecks && <RealityChecks cScoreResult={cScoreResult} props={props} />}
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
              {'★'.repeat(Math.round(props.confidence * 5))}{'☆'.repeat(5 - Math.round(props.confidence * 5))}
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

        {/* Feedback links */}
        <div className={styles.feedbackLinks}>
          <Link to={feedbackUrl} className={styles.feedbackLink}>Report bad data</Link>
          <Link to={`/feedback?type=explanation_suggestion&zone=${zoneSlug || ''}`} className={styles.feedbackLink}>
            Suggest explanation
          </Link>
        </div>
      </div>
    </aside>
  );
}
