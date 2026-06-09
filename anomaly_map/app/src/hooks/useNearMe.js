/**
 * useNearMe — browser geolocation hook
 *
 * Returns { locate, position, loading, error, clearPosition }
 * Call locate() to trigger the browser geolocation permission request.
 * On success, the store's viewState is updated to fly to the user's location.
 */

import { useState, useCallback } from 'react';
import { useStore } from '../store/useStore.js';

export function useNearMe() {
  const setViewState = useStore(s => s.setViewState);
  const [position, setPosition] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const locate = useCallback(() => {
    if (!navigator.geolocation) {
      setError('Geolocation not supported by this browser.');
      return;
    }
    setLoading(true);
    setError(null);

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude, longitude, accuracy } = pos.coords;
        setPosition({ lat: latitude, lon: longitude, accuracy });
        setLoading(false);
        setViewState({
          longitude,
          latitude,
          zoom: 9,
          pitch: 0,
          bearing: 0,
        });
      },
      (err) => {
        setLoading(false);
        switch (err.code) {
          case err.PERMISSION_DENIED:
            setError('Location permission denied.');
            break;
          case err.POSITION_UNAVAILABLE:
            setError('Location unavailable.');
            break;
          case err.TIMEOUT:
            setError('Location request timed out.');
            break;
          default:
            setError('Unknown geolocation error.');
        }
      },
      { enableHighAccuracy: false, timeout: 8000, maximumAge: 60000 }
    );
  }, [setViewState]);

  const clearPosition = useCallback(() => {
    setPosition(null);
    setError(null);
  }, []);

  return { locate, position, loading, error, clearPosition };
}
