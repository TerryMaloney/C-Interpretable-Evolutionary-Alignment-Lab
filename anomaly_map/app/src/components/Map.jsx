import React, { useMemo, useCallback } from 'react';
import DeckGL from '@deck.gl/react';
import { ScatterplotLayer, HeatmapLayer } from '@deck.gl/aggregation-layers';
import { GeoJsonLayer } from '@deck.gl/layers';
import { Map as MapLibre } from '@vis.gl/react-maplibre';
import { useStore, MAP_VIEWS } from '../store/useStore.js';
import { buildFlatFeatures, cScoreToColor, getCategoryColor } from '../utils/layers.js';
import styles from './Map.module.css';

const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/dark-matter-nolabels-gl-style/style.json';

export default function Map() {
  const {
    viewState, setViewState,
    mapView, visibleLayers, layerData, registry,
    convergenceData, showCScoreOverlay,
    selectFeature, hoverFeature, hoveredFeature,
  } = useStore();

  // Build flat point features for all visible layers
  const flatFeatures = useMemo(() => {
    return buildFlatFeatures(layerData, visibleLayers, registry);
  }, [layerData, visibleLayers, registry]);

  // Build convergence score features
  const convergenceFeatures = useMemo(() => {
    if (!convergenceData?.features) return [];
    return convergenceData.features.map(f => ({
      position: f.geometry.coordinates,
      cScore: f.properties?.c_score ?? 0,
      layerCount: f.properties?.layer_count ?? 0,
      zone: f.properties?.zone,
    }));
  }, [convergenceData]);

  const onFeatureClick = useCallback((info) => {
    if (info.object) {
      selectFeature({
        ...info.object,
        screenX: info.x,
        screenY: info.y,
      });
    }
  }, [selectFeature]);

  const onFeatureHover = useCallback((info) => {
    hoverFeature(info.object || null);
  }, [hoverFeature]);

  // ── Layer definitions ──────────────────────────────────────────────────────
  const layers = useMemo(() => {
    const result = [];

    // C-Score convergence overlay (always shown when toggled)
    if (showCScoreOverlay && convergenceFeatures.length > 0) {
      result.push(
        new ScatterplotLayer({
          id: 'convergence-overlay',
          data: convergenceFeatures,
          getPosition: d => d.position,
          getFillColor: d => cScoreToColor(d.cScore),
          getRadius: 18000,
          radiusUnits: 'meters',
          opacity: 0.6,
          pickable: true,
          onClick: onFeatureClick,
          onHover: onFeatureHover,
          updateTriggers: { getFillColor: [convergenceFeatures] },
        })
      );
    }

    if (mapView === MAP_VIEWS.HEATMAP && flatFeatures.length > 0) {
      result.push(
        new HeatmapLayer({
          id: 'heatmap',
          data: flatFeatures,
          getPosition: d => d.position,
          getWeight: d => (d.properties?.confidence ?? 2),
          radiusPixels: 40,
          intensity: 1,
          threshold: 0.05,
          colorRange: [
            [0, 0, 255, 0],
            [0, 100, 255, 80],
            [0, 200, 200, 150],
            [100, 255, 100, 200],
            [255, 200, 0, 220],
            [255, 0, 0, 255],
          ],
        })
      );
    }

    if (mapView === MAP_VIEWS.RESIDUAL || mapView === MAP_VIEWS.LAYERS || mapView === MAP_VIEWS.CONVERGENCE) {
      if (flatFeatures.length > 0) {
        result.push(
          new ScatterplotLayer({
            id: 'points',
            data: flatFeatures,
            getPosition: d => d.position,
            getFillColor: d => [...d.color, 200],
            getLineColor: d => [...d.color.map(c => Math.min(255, c + 60)), 255],
            lineWidthMinPixels: 1,
            stroked: true,
            filled: true,
            getRadius: d => d.radius,
            radiusUnits: 'pixels',
            pickable: true,
            autoHighlight: true,
            highlightColor: [255, 255, 255, 80],
            onClick: onFeatureClick,
            onHover: onFeatureHover,
            updateTriggers: {
              getFillColor: [visibleLayers, layerData],
              getRadius: [visibleLayers],
            },
          })
        );
      }
    }

    return result;
  }, [
    mapView, flatFeatures, convergenceFeatures,
    showCScoreOverlay, visibleLayers, layerData,
    onFeatureClick, onFeatureHover,
  ]);

  return (
    <div className={styles.mapWrapper}>
      <DeckGL
        viewState={viewState}
        onViewStateChange={({ viewState: vs }) => setViewState(vs)}
        controller
        layers={layers}
        getTooltip={({ object }) => {
          if (!object) return null;
          if (object.cScore !== undefined) {
            return {
              html: `<b>C-Score: ${object.cScore.toFixed(2)}</b><br/>Layers: ${object.layerCount}${object.zone ? ` | Zone ${object.zone}` : ''}`,
              style: { background: '#12121a', border: '1px solid #2a2a3e', color: '#e0e0e0', fontSize: '12px' },
            };
          }
          const p = object.properties;
          if (!p) return null;
          return {
            html: `<b>${p.layer}</b><br/>${(p.notes || '').slice(0, 120)}${p.notes?.length > 120 ? '…' : ''}`,
            style: { background: '#12121a', border: '1px solid #2a2a3e', color: '#e0e0e0', fontSize: '12px', maxWidth: '280px' },
          };
        }}
      >
        <MapLibre
          mapStyle={MAP_STYLE}
          attributionControl={false}
          reuseMaps
        />
      </DeckGL>

      {/* Hover tooltip for hovered feature */}
      {hoveredFeature && hoveredFeature.properties && (
        <div className={styles.tooltip}>
          <span className={styles.tooltipLayer}>{hoveredFeature.properties.layer}</span>
          <span className={styles.tooltipText}>
            {(hoveredFeature.properties.notes || '').slice(0, 100)}
          </span>
        </div>
      )}

      {/* Map attribution */}
      <div className={styles.attribution}>
        © CartoDB / OpenStreetMap
      </div>
    </div>
  );
}
