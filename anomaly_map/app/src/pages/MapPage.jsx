import React, { useEffect, useRef, useState } from 'react';
import { useStore } from '../store/useStore.js';
import { useUrlSync } from '../hooks/useUrlSync.js';
import Map from '../components/Map.jsx';
import LayerPanel from '../components/LayerPanel.jsx';
import DetailPanel from '../components/DetailPanel.jsx';
import MapHeader from '../components/MapHeader.jsx';
import PresetsPanel from '../components/PresetsPanel.jsx';
import TimeSlider from '../components/TimeSlider.jsx';
import BearingRose from '../components/BearingRose.jsx';
import LoadingOverlay from '../components/LoadingOverlay.jsx';
import styles from './MapPage.module.css';

const DATA_BASE = '/data/processed';
const REGISTRY_PATH = '/data/layer_registry.json';
const CONVERGENCE_PATH = '/output/analysis/convergence_scores.geojson';
const ALIGNMENTS_PATH = '/output/analysis/alignments.geojson';
const ALIGNMENT_CONTROL_PATH = '/output/analysis/alignments_control.geojson';
const BEARINGS_PATH = '/output/analysis/alignment_bearings.json';

const LOGIC_REMINDERS = [
  'A hotspot is a question, not an answer.',
  'What would explain this normally?',
  'Did this survive population correction?',
  'Are these independent sources?',
  'Is this spatial overlap, temporal overlap, or both?',
  'Could reporting bias explain this?',
  'Could military activity explain this?',
  'Could geology explain this?',
  'Investigate freely. Conclude carefully.',
  'Patterns are clues, not conclusions.',
  'High noise ≠ no signal. Low noise ≠ confirmed signal.',
  'A confound reduces confidence. It does not eliminate the question.',
];

function RotatingReminder() {
  const [idx, setIdx] = useState(() => Math.floor(Math.random() * LOGIC_REMINDERS.length));

  useEffect(() => {
    const t = setInterval(() => {
      setIdx(i => (i + 1) % LOGIC_REMINDERS.length);
    }, 8000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className={styles.logicReminder} title="Rotating methodological reminder">
      <span className={styles.reminderIcon}>⚑</span>
      {LOGIC_REMINDERS[idx]}
    </div>
  );
}

export default function MapPage() {
  const {
    setRegistry, setLayerData, setConvergenceData,
    setAlignmentData, setAlignmentControlData, setBearingData,
    setLoading, visibleLayers, layerData,
  } = useStore();

  const loadedLayers = useRef(new Set());
  const { copyShareUrl } = useUrlSync();
  const [copied, setCopied] = useState(false);

  // Load registry on mount
  useEffect(() => {
    setLoading(true, 'Loading layer registry…');
    fetch(REGISTRY_PATH)
      .then(r => r.json())
      .then(registry => {
        setRegistry(registry);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [setRegistry, setLoading]);

  // Lazy-load layer GeoJSON when it becomes visible
  useEffect(() => {
    for (const layerName of visibleLayers) {
      if (loadedLayers.current.has(layerName)) continue;
      if (layerData[layerName]) continue;
      loadedLayers.current.add(layerName);
      const url = `${DATA_BASE}/${layerName}.geojson`;
      fetch(url)
        .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
        .then(gj => setLayerData(layerName, gj))
        .catch(err => console.warn(`Layer ${layerName} unavailable: ${err.message}`));
    }
  }, [visibleLayers, layerData, setLayerData]);

  // Load convergence scores
  useEffect(() => {
    fetch(CONVERGENCE_PATH)
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then(gj => setConvergenceData(gj))
      .catch(() => {});
  }, [setConvergenceData]);

  // Load alignment analysis (lines, negative control, bearing rose) — all optional
  useEffect(() => {
    const grab = (url, setter) =>
      fetch(url)
        .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
        .then(setter)
        .catch(() => {});
    grab(ALIGNMENTS_PATH, setAlignmentData);
    grab(ALIGNMENT_CONTROL_PATH, setAlignmentControlData);
    grab(BEARINGS_PATH, setBearingData);
  }, [setAlignmentData, setAlignmentControlData, setBearingData]);

  const handleShare = () => {
    copyShareUrl();
    setCopied(true);
    setTimeout(() => setCopied(false), 2200);
  };

  return (
    <div className={styles.page}>
      {/* Permanent reality header — always visible */}
      <div className={styles.realityBanner}>
        <span className={styles.bannerIcon}>◈</span>
        Correlation ≠ causation. A hotspot means "worth investigating," not "explained."
        <button className={styles.shareBtn} onClick={handleShare} title="Copy shareable URL">
          {copied ? '✓ Copied!' : '⧉ Share'}
        </button>
        <a className={styles.navLink} href="/about">About</a>
        <a className={styles.navLink} href="/sources">Sources</a>
        <a className={styles.navLink} href="/">Home</a>
      </div>

      <RotatingReminder />

      <div className={styles.headerRow}>
        <MapHeader />
        <PresetsPanel />
      </div>

      <div className={styles.body}>
        <LayerPanel />
        <Map />
        <BearingRose />
        <DetailPanel />
      </div>

      <TimeSlider />

      <LoadingOverlay />
    </div>
  );
}
