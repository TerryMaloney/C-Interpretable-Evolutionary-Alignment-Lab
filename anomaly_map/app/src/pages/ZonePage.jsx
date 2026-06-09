import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import styles from './ZonePage.module.css';

// Pre-defined zone metadata — populated from convergence analysis output
const ZONE_DATA = {
  'rocky-mountain-rift': {
    name: 'Rocky Mountain Rift — San Luis Valley',
    lat: 37.5, lon: -105.8,
    cScore: 8.4,
    noiseScore: 'Low',
    residualInterest: 'High',
    claimLevel: 4,
    layers: ['NUFORC UAP Sightings', 'USGS Seismic', 'USGS Magnetic Anomaly', 'USGS Radon Potential', 'Cattle Mutilations (manual)', 'Persistent Earth Lights'],
    mainConfound: 'Low population density reduces reporting-bias concern. Some military overflight from nearby ranges.',
    whatRemainsInteresting: 'Strong convergence of geophysical + anomaly report layers. Seismic, magnetic, and radon all elevated in same corridor. Independent sources agree on geography.',
    limitations: ['Cattle mutilation data is manually compiled — quality varies.', 'Radon map resolution is county-level only.', 'Population correction may slightly over-correct for rural areas.'],
    verdict: 'Moderate convergence that survives current controls. Further Tier 1 confirmation needed for Claim Level 5.',
  },
  'southern-ca-offshore': {
    name: 'Southern California Offshore / Santa Catalina Channel',
    lat: 33.4, lon: -118.5,
    cScore: 7.9,
    noiseScore: 'High',
    residualInterest: 'Medium',
    claimLevel: 3,
    layers: ['NUFORC UAP Sightings', 'NOAA Marine Mammal UMEs', 'USO Incidents (manual)', 'FOIA Documents', 'Maritime Anomalies', 'DART Buoys'],
    mainConfound: 'Heavy military presence (Pacific Fleet, Point Mugu, NAS Lemoore). Dense coastal population — high observation density. Major shipping lanes. Channel Islands National Park tourism.',
    whatRemainsInteresting: 'USO cluster at depth. Marine mammal anomalies concentrated in same bathymetric zone as sighting reports. FOIA cases include Nimitz (Tic-Tac) with instrument confirmation.',
    limitations: ['Nimitz encounter is a single high-quality event, not a persistent pattern.', 'Maritime data coverage varies significantly year to year.', 'Military-confound is very high — hard to separate signal from training activity.'],
    verdict: 'Strong convergence, heavily confounded. Interesting residual but cannot advance past Level 3 without negative military-schedule controls.',
  },
  'hessdalen-norway': {
    name: 'Hessdalen Valley, Norway (Control Zone)',
    lat: 62.8, lon: 11.2,
    cScore: 5.1,
    noiseScore: 'Low',
    residualInterest: 'High',
    claimLevel: 5,
    layers: ['Persistent Earth Lights', 'USGS Magnetic Anomaly', 'Schumann / ELF Monitoring', 'NUFORC International'],
    mainConfound: 'Very low population. No significant military. Geophysically active valley (sulfurous rock, rift-adjacent geology). Lights partially explained: plasma/piezoelectric mechanism proposed and partially validated by Hessdalen Project.',
    whatRemainsInteresting: 'Hessdalen is the best-documented resolved analog. Long-baseline scientific study. Some light behavior not fully accounted for by current geophysical models. Useful as calibration zone — if our system scores it high, that supports model validity.',
    limitations: ['Already partially explained — use as validation, not open investigation.', 'European data coverage thinner than US layers.'],
    verdict: 'Solved analog / control site. Scores Level 5 because spatial + temporal confirmation exists from long-baseline study. Use to validate scoring model.',
  },
  'new-madrid-zone': {
    name: 'New Madrid Seismic Zone',
    lat: 36.5, lon: -89.5,
    cScore: 6.2,
    noiseScore: 'Medium',
    residualInterest: 'Medium',
    claimLevel: 3,
    layers: ['USGS Seismic', 'USGS Magnetic Anomaly', 'USGS Radon Potential', 'NUFORC UAP Sightings', 'DOE Grid Disturbances'],
    mainConfound: 'Major seismic zone — all geophysical layers expected to be elevated here. Population moderate for rural Mississippi Valley.',
    whatRemainsInteresting: 'Earthquake light reports correlate with known pre-seismic EM emissions. Grid disturbances in same area as seismic events expected but magnitude interesting.',
    limitations: ['Seismic + EM correlation is expected for earthquake zone — not independently anomalous.', 'More testing needed to separate earthquake effects from other layers.'],
    verdict: 'Interesting geophysical convergence but largely explained by known seismology. Useful for mechanism testing.',
  },
  'japan-trench-zone-e': {
    name: 'Japan Trench (Validation Zone E)',
    lat: 38.1, lon: 144.5,
    cScore: 5.8,
    noiseScore: 'Low',
    residualInterest: 'High',
    claimLevel: 3,
    layers: ['USGS Seismic', 'DART Buoys', 'NOAA Marine Mammal UMEs', 'Maritime Anomalies', 'GPS-TEC Ionospheric'],
    mainConfound: 'Active subduction zone — seismic and ionospheric activity expected. Dense fishing + shipping traffic.',
    whatRemainsInteresting: 'Cross-national validation zone. Pre-seismic animal anomalies in 2011 Tōhoku record. If Japanese anomaly datasets (JSDF, Japan Meteorological Agency) show same geographic pattern as our independent US-sourced layers, that is strong cross-national confirmation.',
    limitations: ['Japanese language datasets not yet integrated.', 'Cross-national validation incomplete.', 'Ionospheric anomalies in subduction zones are expected pre-seismic signals.'],
    verdict: 'Validation zone — pending integration of Japanese national data. Currently Level 3; could advance with cross-national confirmation.',
  },
};

const CLAIM_LEVEL_LABELS = [
  '', 'Visual cluster only', 'Survives population correction',
  'Survives pop + military/industrial masking',
  'Multiple independent Tier 1 layers converge',
  'Spatial AND temporal convergence confirmed',
  'Survives negative controls',
];

export default function ZonePage() {
  const { zoneSlug } = useParams();
  const zone = ZONE_DATA[zoneSlug];

  useEffect(() => {
    if (zone) {
      document.title = `${zone.name} — Anomaly Map`;
      // Update meta description for OpenGraph
      const metaDesc = document.querySelector('meta[name="description"]') ||
        Object.assign(document.createElement('meta'), { name: 'description' });
      metaDesc.content = `C-Score ${zone.cScore}. ${zone.verdict}`;
      if (!metaDesc.parentNode) document.head.appendChild(metaDesc);

      // OpenGraph
      const setMeta = (prop, content) => {
        let el = document.querySelector(`meta[property="${prop}"]`);
        if (!el) el = Object.assign(document.createElement('meta'), { property: prop });
        el.content = content;
        if (!el.parentNode) document.head.appendChild(el);
      };
      setMeta('og:title', `${zone.name} — Anomaly Map`);
      setMeta('og:description', `C-Score ${zone.cScore}. Noise: ${zone.noiseScore}. ${zone.verdict}`);
      setMeta('og:type', 'article');
    }
    return () => { document.title = 'Anomaly Map'; };
  }, [zone, zoneSlug]);

  if (!zone) {
    return (
      <div className={styles.page}>
        <nav className={styles.nav}>
          <Link to="/" className={styles.navBrand}>◈ Anomaly Map</Link>
          <Link to="/map" className={styles.navLink}>Map</Link>
        </nav>
        <div className={styles.notFound}>
          <h2>Zone not found: {zoneSlug}</h2>
          <p>This zone may not have been analyzed yet, or the URL is incorrect.</p>
          <Link to="/map" className={styles.openBtn}>Open Interactive Map</Link>
        </div>
      </div>
    );
  }

  const mapUrl = `/map?lat=${zone.lat}&lon=${zone.lon}&z=8&zone=${zoneSlug}`;
  const feedbackUrl = `/feedback?zone=${zoneSlug}&related_hotspot_slug=${zoneSlug}`;
  const level = zone.claimLevel;

  return (
    <div className={styles.page}>
      <nav className={styles.nav}>
        <Link to="/" className={styles.navBrand}>◈ Anomaly Map</Link>
        <Link to="/map" className={styles.navLink}>Map</Link>
        <Link to="/about" className={styles.navLink}>About</Link>
        <Link to="/sources" className={styles.navLink}>Sources</Link>
      </nav>

      <main className={styles.main}>
        <div className={styles.zoneHeader}>
          <h1 className={styles.zoneName}>{zone.name}</h1>
          <div className={styles.scoreLine}>
            <div className={styles.scoreBlock}>
              <span className={styles.scoreLabel}>C-Score</span>
              <span className={styles.scoreValue}>{zone.cScore}</span>
            </div>
            <div className={styles.scoreBlock}>
              <span className={styles.scoreLabel}>Noise</span>
              <span className={`${styles.noiseValue} ${styles[`noise${zone.noiseScore}`]}`}>
                {zone.noiseScore}
              </span>
            </div>
            <div className={styles.scoreBlock}>
              <span className={styles.scoreLabel}>Residual</span>
              <span className={`${styles.residualValue} ${styles[`residual${zone.residualInterest}`]}`}>
                {zone.residualInterest}
              </span>
            </div>
            <div className={`${styles.claimBadge} ${styles[`level${level}`]}`}>
              <span className={styles.claimNum}>Level {level}</span>
              <span className={styles.claimLabel}>{CLAIM_LEVEL_LABELS[level]}</span>
            </div>
          </div>
        </div>

        <div className={styles.grid}>
          <section className={styles.card}>
            <h3 className={styles.cardTitle}>Contributing layers</h3>
            <ul className={styles.layerList}>
              {zone.layers.map(l => (
                <li key={l} className={styles.layerItem}>{l}</li>
              ))}
            </ul>
          </section>

          <section className={styles.card}>
            <h3 className={styles.cardTitle}>Main confound</h3>
            <p className={styles.cardText}>{zone.mainConfound}</p>
          </section>

          <section className={styles.card}>
            <h3 className={styles.cardTitle}>What remains interesting</h3>
            <p className={styles.cardText}>{zone.whatRemainsInteresting}</p>
          </section>

          <section className={styles.card}>
            <h3 className={styles.cardTitle}>Data limitations</h3>
            <ul className={styles.limitList}>
              {zone.limitations.map((l, i) => (
                <li key={i} className={styles.limitItem}>{l}</li>
              ))}
            </ul>
          </section>

          <section className={`${styles.card} ${styles.verdictCard}`}>
            <h3 className={styles.cardTitle}>Grounded verdict</h3>
            <p className={styles.verdict}>{zone.verdict}</p>
            <p className={styles.disclaimer}>
              Correlation is not causation. This page identifies a pattern worth investigating, not a conclusion.
            </p>
          </section>
        </div>

        <div className={styles.actions}>
          <Link to={mapUrl} className={styles.openBtn}>Open Interactive Map</Link>
          <button
            className={styles.shareBtn}
            onClick={() => navigator.clipboard?.writeText(window.location.href)}
          >
            ⧉ Copy Share Link
          </button>
          <Link to={`${feedbackUrl}&type=bad_data_report`} className={styles.feedbackBtn}>
            Report Bad Data
          </Link>
          <Link to={`${feedbackUrl}&type=explanation_suggestion`} className={styles.feedbackBtn}>
            Suggest Explanation
          </Link>
          <Link to={`${feedbackUrl}&type=dataset_suggestion`} className={styles.feedbackBtn}>
            Submit Source
          </Link>
        </div>
      </main>
    </div>
  );
}
