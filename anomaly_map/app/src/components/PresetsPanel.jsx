import React, { useState } from 'react';
import { useStore, INVESTIGATION_PRESETS } from '../store/useStore.js';
import styles from './PresetsPanel.module.css';

export default function PresetsPanel() {
  const { activePreset, applyPreset, clearPreset } = useStore();
  const [open, setOpen] = useState(false);

  const presets = Object.values(INVESTIGATION_PRESETS);

  return (
    <div className={styles.wrapper}>
      <button
        className={`${styles.trigger} ${activePreset ? styles.triggerActive : ''}`}
        onClick={() => setOpen(v => !v)}
        title="Investigation Presets"
      >
        <span>{activePreset ? INVESTIGATION_PRESETS[activePreset]?.icon : '🧪'}</span>
        <span className={styles.triggerLabel}>
          {activePreset ? INVESTIGATION_PRESETS[activePreset]?.label : 'Presets'}
        </span>
        <span className={styles.caret}>{open ? '▴' : '▾'}</span>
      </button>

      {open && (
        <div className={styles.dropdown}>
          <div className={styles.header}>Investigation Presets</div>
          <div className={styles.desc}>
            Curated layer + filter combinations for specific research modes.
          </div>

          {presets.map(preset => (
            <button
              key={preset.id}
              className={`${styles.presetBtn} ${activePreset === preset.id ? styles.presetActive : ''}`}
              onClick={() => {
                if (activePreset === preset.id) {
                  clearPreset();
                } else {
                  applyPreset(preset.id);
                }
                setOpen(false);
              }}
            >
              <div className={styles.presetHeader}>
                <span className={styles.presetIcon}>{preset.icon}</span>
                <span className={styles.presetLabel}>{preset.label}</span>
                {activePreset === preset.id && (
                  <span className={styles.activeBadge}>ACTIVE</span>
                )}
              </div>
              <div className={styles.presetDesc}>{preset.description}</div>
              <div className={styles.presetMeta}>
                <span className={styles.metaItem}>{preset.visibleLayers.size} layers</span>
                <span className={styles.metaItem}>{preset.convergenceRadius}km radius</span>
                <span className={styles.metaItem}>{preset.sortMode}</span>
              </div>
            </button>
          ))}

          {activePreset && (
            <button className={styles.clearBtn} onClick={() => { clearPreset(); setOpen(false); }}>
              ✕ Clear preset
            </button>
          )}
        </div>
      )}
    </div>
  );
}
