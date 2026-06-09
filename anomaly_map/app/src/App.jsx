import React, { lazy, Suspense } from 'react';
import { Routes, Route } from 'react-router-dom';
import LoadingOverlay from './components/LoadingOverlay.jsx';

const MapPage    = lazy(() => import('./pages/MapPage.jsx'));
const LandingPage = lazy(() => import('./pages/LandingPage.jsx'));
const ZonePage   = lazy(() => import('./pages/ZonePage.jsx'));
const AboutPage  = lazy(() => import('./pages/AboutPage.jsx'));
const SourcesPage = lazy(() => import('./pages/SourcesPage.jsx'));
const FeedbackPage = lazy(() => import('./pages/FeedbackPage.jsx'));

export default function App() {
  return (
    <Suspense fallback={<LoadingOverlay message="Loading…" />}>
      <Routes>
        <Route path="/"               element={<LandingPage />} />
        <Route path="/map"            element={<MapPage />} />
        <Route path="/z/:zoneSlug"    element={<ZonePage />} />
        <Route path="/about"          element={<AboutPage />} />
        <Route path="/sources"        element={<SourcesPage />} />
        <Route path="/feedback"       element={<FeedbackPage />} />
        <Route path="*"               element={<LandingPage />} />
      </Routes>
    </Suspense>
  );
}
