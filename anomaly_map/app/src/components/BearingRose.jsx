import React from 'react';
import { useStore } from '../store/useStore.js';
import styles from './BearingRose.module.css';

const SIZE = 128;
const CX = SIZE / 2;
const CY = SIZE / 2;
const R = 50;

function polar(angleDeg, len) {
  // angle measured clockwise from north (up)
  const rad = (angleDeg * Math.PI) / 180;
  return [CX + len * Math.sin(rad), CY - len * Math.cos(rad)];
}

/**
 * Orientation rose for SIGNIFICANT, unconfounded alignments. Only meaningful if any
 * alignment survives the null test — otherwise it states so plainly. Bins cover 0–180°
 * (lines are undirected) and are mirrored to a full 0–360° rose.
 */
export default function BearingRose() {
  const { showAlignments, bearingData } = useStore();
  if (!showAlignments || !bearingData) return null;

  const counts = bearingData.counts || [];
  const total = counts.reduce((a, b) => a + b, 0);

  if (!total) {
    return (
      <div className={styles.card}>
        <div className={styles.title}>Alignment bearings</div>
        <div className={styles.empty}>
          No alignments survive the null test — consistent with chance.
        </div>
      </div>
    );
  }

  const n = counts.length;
  const binW = 180 / n;
  const max = Math.max(...counts);
  const spokes = [];
  counts.forEach((c, i) => {
    const len = max ? (c / max) * R : 0;
    if (len <= 0) return;
    const center = i * binW + binW / 2;
    [center, center + 180].forEach((a, k) => {
      const [x, y] = polar(a, len);
      spokes.push(<line key={`${i}-${k}`} x1={CX} y1={CY} x2={x} y2={y}
                        className={styles.spoke} />);
    });
  });

  return (
    <div className={styles.card}>
      <div className={styles.title}>Alignment bearings ({total})</div>
      <svg width={SIZE} height={SIZE} className={styles.svg}>
        <circle cx={CX} cy={CY} r={R} className={styles.ring} />
        <line x1={CX} y1={CY - R} x2={CX} y2={CY + R} className={styles.axis} />
        <line x1={CX - R} y1={CY} x2={CX + R} y2={CY} className={styles.axis} />
        <text x={CX} y={12} className={styles.cardinal} textAnchor="middle">N</text>
        <text x={SIZE - 6} y={CY + 4} className={styles.cardinal} textAnchor="end">E</text>
        {spokes}
        <circle cx={CX} cy={CY} r={2.5} className={styles.hub} />
      </svg>
    </div>
  );
}
