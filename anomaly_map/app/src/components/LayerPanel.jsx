import React, { useState } from 'react';
import { useStore } from '../store/useStore.js';
import { getCategoryColor } from '../utils/layers.js';
import styles from './LayerPanel.module.css';

export default function LayerPanel() {
  const {
    panelOpen, setPanelOpen,
    layerGroups, visibleLayers, toggleLayer, toggleLayerGroup,
    registry, layerData,
    filters, updateFilter,
  } = useStore();

  const [expandedGroups, setExpandedGroups] = useState(
    Object.fromEntries(Object.keys(layerGroups).map(k => [k, true]))
  );

  const toggleGroup = (key) => {
    setExpandedGroups(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const isGroupAllVisible = (groupKey) => {
    const group = layerGroups[groupKey];
    return group.layers.every(l => visibleLayers.has(l));
  };

  const isGroupPartialVisible = (groupKey) => {
    const group = layerGroups[groupKey];
    const count = group.layers.filter(l => visibleLayers.has(l)).length;
    return count > 0 && count < group.layers.length;
  };

  const getLayerFeatureCount = (layerName) => {
    return layerData[layerName]?.features?.length ?? null;
  };

  if (!panelOpen) {
    return (
      <button className={styles.openBtn} onClick={() => setPanelOpen(true)}>
        ☰ Layers
      </button>
    );
  }

  return (
    <aside className={styles.panel}>
      <div className={styles.header}>
        <span className={styles.title}>Data Layers</span>
        <button className={styles.closeBtn} onClick={() => setPanelOpen(false)}>✕</button>
      </div>

      {/* Confidence filter */}
      <div className={styles.filterRow}>
        <label className={styles.filterLabel}>Min confidence</label>
        <div className={styles.confButtons}>
          {[1, 2, 3, 4, 5].map(c => (
            <button
              key={c}
              className={`${styles.confBtn} ${filters.minConfidence === c ? styles.active : ''}`}
              onClick={() => updateFilter('minConfidence', c)}
            >
              {c}
            </button>
          ))}
        </div>
      </div>

      {/* Layer groups */}
      <div className={styles.groups}>
        {Object.entries(layerGroups).map(([groupKey, group]) => {
          const allVis = isGroupAllVisible(groupKey);
          const partVis = isGroupPartialVisible(groupKey);
          const expanded = expandedGroups[groupKey];
          const registryLayers = registry?.layers || {};

          return (
            <div key={groupKey} className={styles.group}>
              <div className={styles.groupHeader}>
                <button
                  className={`${styles.groupCheck} ${allVis ? styles.checked : partVis ? styles.partial : ''}`}
                  onClick={() => toggleLayerGroup(groupKey)}
                  title={allVis ? 'Hide all' : 'Show all'}
                >
                  {allVis ? '■' : partVis ? '◪' : '□'}
                </button>
                <button
                  className={styles.groupTitle}
                  onClick={() => toggleGroup(groupKey)}
                  style={{ color: group.color }}
                >
                  {group.label}
                  <span className={styles.groupCount}>
                    {group.layers.filter(l => visibleLayers.has(l)).length}/{group.layers.length}
                  </span>
                </button>
                <button className={styles.expandBtn} onClick={() => toggleGroup(groupKey)}>
                  {expanded ? '▾' : '▸'}
                </button>
              </div>

              {expanded && (
                <div className={styles.layerList}>
                  {group.layers.map(layerName => {
                    const meta = registryLayers[layerName];
                    const isVisible = visibleLayers.has(layerName);
                    const count = getLayerFeatureCount(layerName);
                    const color = getCategoryColor(meta?.category);
                    const colorStr = `rgb(${color.join(',')})`;

                    return (
                      <div key={layerName} className={`${styles.layerRow} ${isVisible ? styles.visible : ''}`}>
                        <button
                          className={`${styles.layerCheck} ${isVisible ? styles.checked : ''}`}
                          style={isVisible ? { borderColor: colorStr, backgroundColor: colorStr + '33' } : {}}
                          onClick={() => toggleLayer(layerName)}
                        >
                          {isVisible ? '●' : '○'}
                        </button>
                        <div className={styles.layerInfo}>
                          <span className={styles.layerName} title={meta?.description}>
                            {meta?.name || layerName}
                          </span>
                          <div className={styles.layerMeta}>
                            <span className={styles.layerTier}>T{meta?.tier ?? '?'}</span>
                            {count != null && (
                              <span className={styles.layerCount}>{count.toLocaleString()}</span>
                            )}
                            {meta?.confidence && (
                              <span className={styles.layerConf} title="Confidence">
                                {'★'.repeat(meta.confidence)}{'☆'.repeat(5 - meta.confidence)}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className={styles.footer}>
        <span className={styles.footerText}>
          {visibleLayers.size} layers active
        </span>
      </div>
    </aside>
  );
}
