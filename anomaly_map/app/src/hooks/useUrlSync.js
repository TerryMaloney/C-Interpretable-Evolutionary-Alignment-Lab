/**
 * Bidirectional URL ↔ store sync for shareable map state.
 *
 * URL schema:
 *   /map?lat=33.4&lon=-118.5&z=7&layers=nuforc,usgs_seismic&view=residual
 *        &radius=50&time=all&conf=2&pop=0&mil=0&cscore=0&sort=convergence
 *        &zone=santa-catalina-channel
 *
 * Calling serializeToUrl() returns the full URL string.
 * Calling applyFromUrl(searchParams) pushes stored state from params.
 */
import { useEffect, useCallback, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useStore } from '../store/useStore.js';

const DEBOUNCE_MS = 400;

function serializeState(state) {
  const p = new URLSearchParams();

  const { longitude, latitude, zoom } = state.viewState;
  p.set('lat', latitude.toFixed(4));
  p.set('lon', longitude.toFixed(4));
  p.set('z', Math.round(zoom));

  p.set('view', state.mapView);

  if (state.visibleLayers.size > 0) {
    p.set('layers', Array.from(state.visibleLayers).sort().join(','));
  }

  p.set('radius', state.convergenceRadius);

  const { minConfidence, dateRange, hideMilitary, hideSolar, hideIndustrial } = state.filters;
  if (minConfidence > 1) p.set('conf', minConfidence);
  if (hideMilitary) p.set('mil', '1');
  if (hideSolar) p.set('sol', '1');
  if (hideIndustrial) p.set('ind', '1');
  if (dateRange[0]) p.set('from', dateRange[0]);
  if (dateRange[1]) p.set('to', dateRange[1]);

  if (state.showCScoreOverlay) p.set('cscore', '1');
  if (state.activeZone) p.set('zone', state.activeZone);
  if (state.selectedFeature?.properties?.id) {
    p.set('feat', state.selectedFeature.properties.id);
  }
  if (state.sortMode) p.set('sort', state.sortMode);

  return p;
}

function applyParams(params, store) {
  const lat = parseFloat(params.get('lat'));
  const lon = parseFloat(params.get('lon'));
  const zoom = parseFloat(params.get('z'));

  if (!isNaN(lat) && !isNaN(lon) && !isNaN(zoom)) {
    store.setViewState({ longitude: lon, latitude: lat, zoom, pitch: 0, bearing: 0 });
  }

  const view = params.get('view');
  if (view) store.setMapView(view);

  const layersParam = params.get('layers');
  if (layersParam) {
    const layerList = layersParam.split(',').filter(Boolean);
    const newVisible = new Set(layerList);
    // Only overwrite if we got a non-empty list from URL
    if (newVisible.size > 0) {
      store.setVisibleLayersFromUrl(newVisible);
    }
  }

  const radius = parseInt(params.get('radius') || params.get('rad'), 10);
  if (!isNaN(radius) && radius > 0) store.setConvergenceRadius(radius);

  const conf = parseInt(params.get('conf'), 10);
  if (!isNaN(conf)) store.updateFilter('minConfidence', conf);
  if (params.get('mil') === '1') store.updateFilter('hideMilitary', true);
  if (params.get('sol') === '1') store.updateFilter('hideSolar', true);
  if (params.get('ind') === '1') store.updateFilter('hideIndustrial', true);

  const from = params.get('from');
  const to = params.get('to');
  if (from || to) store.updateFilter('dateRange', [from || null, to || null]);

  if (params.get('cscore') === '1') store.setShowCScoreOverlay(true);

  const zone = params.get('zone');
  if (zone) store.setActiveZone(zone);

  const sort = params.get('sort');
  if (sort) store.setSortMode(sort);
}

/**
 * Hook — call inside MapPage. Syncs URL ↔ store bidirectionally.
 * Returns a `copyShareUrl` function for the share button.
 */
export function useUrlSync() {
  const [searchParams, setSearchParams] = useSearchParams();
  const store = useStore();
  const initializedRef = useRef(false);
  const timerRef = useRef(null);

  // On first mount, apply URL params to store
  useEffect(() => {
    if (initializedRef.current) return;
    initializedRef.current = true;
    if (searchParams.toString()) {
      applyParams(searchParams, store);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Subscribe to store changes, debounce URL updates
  useEffect(() => {
    const unsub = useStore.subscribe(
      state => ({
        viewState: state.viewState,
        mapView: state.mapView,
        visibleLayers: state.visibleLayers,
        convergenceRadius: state.convergenceRadius,
        filters: state.filters,
        showCScoreOverlay: state.showCScoreOverlay,
        activeZone: state.activeZone,
        selectedFeature: state.selectedFeature,
        sortMode: state.sortMode,
      }),
      (slice) => {
        if (!initializedRef.current) return;
        clearTimeout(timerRef.current);
        timerRef.current = setTimeout(() => {
          const params = serializeState(slice);
          setSearchParams(params, { replace: true });
        }, DEBOUNCE_MS);
      }
    );
    return () => {
      unsub();
      clearTimeout(timerRef.current);
    };
  }, [setSearchParams]);

  const copyShareUrl = useCallback(() => {
    const state = useStore.getState();
    const params = serializeState(state);
    const url = `${window.location.origin}/map?${params.toString()}`;
    navigator.clipboard?.writeText(url).catch(() => {
      // Fallback for non-secure contexts
      const el = document.createElement('textarea');
      el.value = url;
      document.body.appendChild(el);
      el.select();
      document.execCommand('copy');
      document.body.removeChild(el);
    });
    return url;
  }, []);

  return { copyShareUrl };
}

export { serializeState };
