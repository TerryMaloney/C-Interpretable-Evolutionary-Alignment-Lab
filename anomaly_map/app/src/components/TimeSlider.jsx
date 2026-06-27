import React, { useMemo, useEffect, useState } from 'react';
import { useStore } from '../store/useStore.js';
import { parseYear } from '../utils/layers.js';
import styles from './TimeSlider.module.css';

const STEP_MS = 650;

/**
 * Bottom time-slider: scrub anomalies across decades. Shows a trailing window of
 * `window` years up to the playhead, so waves/flaps appear and fade as you play.
 * Points without a parseable datetime are hidden while the filter is on.
 */
export default function TimeSlider() {
  const { layerData, timeFilter, setTimeFilter } = useStore();
  const [playing, setPlaying] = useState(false);

  const [minYear, maxYear] = useMemo(() => {
    let lo = Infinity, hi = -Infinity;
    for (const gj of Object.values(layerData)) {
      for (const f of gj?.features || []) {
        const y = parseYear(f.properties?.datetime);
        if (y == null) continue;
        if (y < lo) lo = y;
        if (y > hi) hi = y;
      }
    }
    return [Number.isFinite(lo) ? lo : null, Number.isFinite(hi) ? hi : null];
  }, [layerData]);

  // Seed the playhead once data + enable are present.
  useEffect(() => {
    if (timeFilter.enabled && timeFilter.current == null && maxYear != null) {
      setTimeFilter({ current: maxYear });
    }
  }, [timeFilter.enabled, timeFilter.current, maxYear, setTimeFilter]);

  // Playback loop.
  useEffect(() => {
    if (!playing || minYear == null) return;
    const id = setInterval(() => {
      const st = useStore.getState().timeFilter;
      let next = (st.current ?? minYear) + 1;
      if (next > maxYear) next = minYear + (st.window ?? 5);   // loop
      setTimeFilter({ current: next });
    }, STEP_MS);
    return () => clearInterval(id);
  }, [playing, minYear, maxYear, setTimeFilter]);

  if (minYear == null || maxYear == null || minYear === maxYear) return null;

  const enable = () => setTimeFilter({ enabled: true, current: maxYear });
  const disable = () => { setPlaying(false); setTimeFilter({ enabled: false }); };

  if (!timeFilter.enabled) {
    return (
      <div className={styles.bar}>
        <button className={styles.enableBtn} onClick={enable} title="Animate anomalies over time">
          ⏱ Time Lapse
        </button>
        <span className={styles.range}>{minYear}–{maxYear}</span>
      </div>
    );
  }

  const current = timeFilter.current ?? maxYear;
  const win = timeFilter.window ?? 5;

  return (
    <div className={styles.bar}>
      <button className={styles.playBtn} onClick={() => setPlaying(p => !p)}
              title={playing ? 'Pause' : 'Play'}>
        {playing ? '❚❚' : '▶'}
      </button>
      <span className={styles.yearLabel}>{Math.max(minYear, current - win)}–{current}</span>
      <input
        className={styles.slider}
        type="range"
        min={minYear}
        max={maxYear}
        value={current}
        onChange={e => { setPlaying(false); setTimeFilter({ current: parseInt(e.target.value, 10) }); }}
      />
      <label className={styles.winLabel} title="Trailing window (years)">
        ±{win}y
        <input
          className={styles.winSlider}
          type="range" min={1} max={30} value={win}
          onChange={e => setTimeFilter({ window: parseInt(e.target.value, 10) })}
        />
      </label>
      <button className={styles.closeBtn} onClick={disable} title="Exit time lapse">✕</button>
    </div>
  );
}
