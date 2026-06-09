import React from 'react';
import { Link } from 'react-router-dom';
import styles from './StaticPage.module.css';

export default function AboutPage() {
  return (
    <div className={styles.page}>
      <nav className={styles.nav}>
        <Link to="/" className={styles.navBrand}>◈ Anomaly Map</Link>
        <Link to="/map" className={styles.navLink}>Map</Link>
        <Link to="/sources" className={styles.navLink}>Sources</Link>
        <Link to="/feedback" className={styles.navLink}>Feedback</Link>
      </nav>

      <main className={styles.main}>
        <h1 className={styles.pageTitle}>About This Map</h1>

        <div className={styles.disclaimer}>
          Correlation is not causation.
          <br />
          This map does not prove what a hotspot means. It shows where independent
          public datasets appear to converge. A high score means "investigate this,"
          not "believe this."
        </div>

        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>How to read this map</h2>
          <p>
            Every pattern on this map should be tested against boring explanations first:
            population density, reporting bias, military activity, industrial sources,
            sensor coverage, known geology, weather, and chance.
          </p>
          <p>
            Stay curious. Stay skeptical. Keep it real.
          </p>
        </section>

        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Scoring model</h2>

          <div className={styles.scoreCard}>
            <h3 className={styles.scoreCardTitle}>C-Score (Convergence Score)</h3>
            <p>
              How many independent active layers overlap within a given radius of a location?
              Weighted by tier and adjusted for population density, military zones, solar
              activity, and industrial sources. A high C-Score means many independent
              datasets agree this location is anomalous — not that we know why.
            </p>
            <code className={styles.formula}>
              C = Σ(layers in radius) × tier_weight × population_correction
              × military_penalty × solar_penalty × industrial_correction
            </code>
          </div>

          <div className={styles.scoreCard}>
            <h3 className={styles.scoreCardTitle}>N-Score (Noise/Confound Score)</h3>
            <p>
              How likely is this hotspot explained by known biases and confounds?
              Factors: population density, airport proximity, military/restricted airspace,
              coastal/shipping bias, famous-location reporting, duplicate report density,
              solar storm windows, known geological activity, sensor coverage gaps.
            </p>
            <p className={styles.note}>
              A hotspot can have high convergence AND high noise. Both are shown clearly.
              High noise reduces confidence but does not eliminate the question.
            </p>
          </div>

          <div className={styles.scoreCard}>
            <h3 className={styles.scoreCardTitle}>R-Score (Residual Score)</h3>
            <p>
              What remains interesting after obvious noise is discounted?
              R-Score rewards independent Tier 1/Tier 2 convergence, low population density,
              incident-group counting instead of raw reports, physical-effect tags,
              spatial + temporal overlap, and survival of multiple negative controls.
            </p>
          </div>
        </section>

        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Confidence tiers</h2>
          <dl className={styles.termList}>
            <dt>Tier 1 (weight 1.0)</dt>
            <dd>Instrument-confirmed or scientifically-collected government data.
                Examples: USGS seismic, NOAA DART buoys, GPS-TEC ionospheric, EPA RadNet.</dd>
            <dt>Tier 2 (weight 0.5)</dt>
            <dd>Credible institutional or multi-witness data with independent documentation.
                Examples: FOIA-confirmed UAP incidents, NOAA marine mammal mortality events,
                GEIPAN Category D cases.</dd>
            <dt>Tier 3 (weight 0.25)</dt>
            <dd>Curated public report databases with partial verification.
                Examples: NUFORC self-reports, BFRO observations, manual context layers.</dd>
          </dl>
        </section>

        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Claim Level ladder</h2>
          <ol className={styles.claimList}>
            <li><strong>Level 1</strong> — Visual cluster only. No controls applied.</li>
            <li><strong>Level 2</strong> — Survives population correction.</li>
            <li><strong>Level 3</strong> — Survives population + military/industrial masking.</li>
            <li><strong>Level 4</strong> — Multiple independent Tier 1 layers converge.</li>
            <li><strong>Level 5</strong> — Spatial AND temporal convergence confirmed.</li>
            <li><strong>Level 6</strong> — Survives negative controls.</li>
          </ol>
          <p className={styles.note}>
            A zone cannot advance to a higher level unless the required data and checks exist.
            If a check has not been run, it shows as Unknown and the level stays lower.
          </p>
        </section>

        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Population correction</h2>
          <p>
            More people → more reports, independent of actual anomaly density.
            Population correction divides signal density by local population density
            (NASA SEDAC GPWV4 dataset). This prevents urban areas from dominating
            hotspot rankings just because there are more observers.
          </p>
          <p className={styles.note}>
            When population correction is OFF, urban hotspots appear higher.
            When ON, rural areas with unexpected convergence become more visible.
          </p>
        </section>

        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Military masking</h2>
          <p>
            Military activity explains many anomalous sightings without requiring
            exotic causes. The military mask applies a penalty to hotspots that overlap
            restricted airspace (FAA SUA polygons), known test ranges, and high-ADS-B
            coverage gaps (suggesting radar shadow zones used for classified testing).
          </p>
          <p className={styles.note}>
            Military mask ON is the credibility-first default. Toggling it OFF shows
            what the full picture looks like without that discount.
          </p>
        </section>

        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Why some checks show Unknown</h2>
          <p>
            A check shows Unknown when the data to run it has not been loaded or does
            not exist for that location. Unknown is not the same as "passed" — it means
            the check has not been performed. Honest limitations are shown rather than
            optimistic guesses.
          </p>
        </section>

        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Public submissions</h2>
          <p>
            Public suggestions do not automatically appear on the map. Every dataset
            suggestion, bad-data report, or explanation proposal is reviewed before
            it can affect scoring or public layers. The map changes on evidence, not
            on votes.
          </p>
        </section>

        <div className={styles.footer}>
          <Link to="/map" className={styles.footerBtn}>Open Map</Link>
          <Link to="/sources" className={styles.footerLink}>Data Sources</Link>
          <Link to="/feedback" className={styles.footerLink}>Submit Feedback</Link>
        </div>
      </main>
    </div>
  );
}
