import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  optimizeDeps: {
    exclude: ['@duckdb/duckdb-wasm'],
  },
  server: {
    headers: {
      // Required for SharedArrayBuffer (DuckDB-WASM + Apache Arrow)
      'Cross-Origin-Opener-Policy': 'same-origin',
      'Cross-Origin-Embedder-Policy': 'credentialless',
    },
  },
  build: {
    target: 'esnext',
    rollupOptions: {
      output: {
        manualChunks: {
          'duckdb': ['@duckdb/duckdb-wasm'],
          'deck': ['deck.gl', '@deck.gl/core', '@deck.gl/layers', '@deck.gl/aggregation-layers'],
          'maplibre': ['maplibre-gl', '@vis.gl/react-maplibre'],
        },
      },
    },
  },
});
