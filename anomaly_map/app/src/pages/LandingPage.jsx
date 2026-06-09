import React from 'react';
import { Link } from 'react-router-dom';
import styles from './LandingPage.module.css';

const TOP_ZONES = [
  { slug: 'rocky-mountain-rift',   name: 'Rocky Mountain Rift', score: '8.4', noise: 'Low',    level: 4 },
  { slug: 'southern-ca-offshore',  name: 'Southern CA Offshore', score: '7.9', noise: 'High',   level: 3 },
  { slug: 'new-madrid-zone',       name: 'New Madrid Seismic',  score: '6.2', noise: 'Medium', level: 3 },
  { slug: 'japan-trench-zone-e',   name: 'Japan Trench',        score: '5.8', noise: 'Low',    level: 3 },
  { slug: 'hessdalen-norway',      name: 'Hessdalen (control)', score: '5.1', noise: 'Low',    level: 5 },
];

export default function LandingPage() {
  return (
    <div className={styles.page}>
      <nav className={styles.nav}>
        <span className={styles.logo}>◈</span>
        <span className={styles.brand}>Anomaly Map</span>
        <div className={styles.navLinks}>
          <Link to="/map">Map</Link>
          <Link to="/about">About</Link>
          <Link to="/sources">Sources</Link>
          <Link to="/feedback">Feedback</Link>
        </div>
      </nav>

      <main className={styles.hero}>
        <h1 className={styles.headline}>Anomaly Map</h1>
        <p className={styles.tagline}>
          Explore where public anomaly reports, geophysical signals, biological events,
          and independent datasets converge — then test the boring explanations first.
        </p>

        <div className={styles.disclaimer}>
          Correlation is not causation. This map ranks patterns, not conclusions.
        </div>

        <div className={styles.ctaRow}>
          <Link to="/map" className={styles.ctaPrimary}>Explore Map</Link>
          <Link to="/about" className={styles.ctaSecondary}>How It Works</Link>
          <Link to="/sources" className={styles.ctaSecondary}>Sources</Link>
          <Link to="/feedback" className={styles.ctaSecondary}>Suggest Dataset</Link>
        </div>
      </main>

      <section className={styles.hotspots}>
        <h2 className={styles.sectionTitle}>
          Top Signal Candidates
          <span className={styles.sectionNote}>After current controls</span>
        </h2>

        <div className={styles.zoneGrid}>
          {TOP_ZONES.map(z => (
            <Link key={z.slug} to={`/z/${z.slug}`} className={styles.zoneCard}>
              <div className={styles.zoneCardTop}>
                <span className={styles.zoneName}>{z.name}</span>
                <span className={`${styles.claimBadge} ${styles[`level${z.level}`]}`}>
                  Lv {z.level}
                </span>
              </div>
              <div className={styles.zoneCardScores}>
                <span className={styles.cScore}>C-Score {z.score}</span>
                <span className={`${styles.noiseBadge} ${styles[`noise${z.noise}`]}`}>
                  Noise: {z.noise}
                </span>
              </div>
            </Link>
          ))}
        </div>
      </section>

      <footer className={styles.footer}>
        <span>Anomaly Map — public research tool</span>
        <Link to="/about">Methodology</Link>
        <Link to="/feedback">Submit feedback</Link>
        <span>No ads. No accounts. No conclusions.</span>
      </footer>
    </div>
  );
}
