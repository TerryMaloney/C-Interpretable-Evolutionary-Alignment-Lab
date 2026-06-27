import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { readFile } from 'fs/promises';
import { fileURLToPath } from 'url';
import path from 'path';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
// Repo data lives outside the app dir (anomaly_map/data, anomaly_map/output).
// In dev, serve /data/* and /output/* straight from disk so the map can load
// layers, the registry, and the analysis GeoJSON without symlinks or a copy step
// (cross-platform — works the same on Windows).
const REPO_ROOT = path.resolve(__dirname, '..');

function serveRepoData() {
  return {
    name: 'serve-repo-data',
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        const url = (req.url || '').split('?')[0];
        if (!url.startsWith('/data/') && !url.startsWith('/output/')) return next();
        // Block path traversal, then map the URL onto the repo dir.
        const rel = path.normalize(decodeURIComponent(url)).replace(/^(\.\.[/\\])+/, '');
        const filePath = path.join(REPO_ROOT, rel);
        if (!filePath.startsWith(REPO_ROOT)) { res.statusCode = 403; return res.end('Forbidden'); }
        try {
          const body = await readFile(filePath);
          res.setHeader('Content-Type',
            filePath.endsWith('.geojson') || filePath.endsWith('.json')
              ? 'application/json' : 'application/octet-stream');
          res.end(body);
        } catch {
          next();   // not found → let Vite 404 it (graceful in the app)
        }
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), serveRepoData()],
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
