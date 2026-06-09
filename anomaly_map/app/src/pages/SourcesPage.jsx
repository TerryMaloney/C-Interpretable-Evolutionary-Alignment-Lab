import React from 'react';
import { Link } from 'react-router-dom';
import styles from './StaticPage.module.css';

const SOURCES = [
  {
    group: 'Tier 1 — Geophysical / Instrument-confirmed',
    items: [
      { name: 'USGS Earthquake Catalog (FDSN)', tier: 1, records: '~50,000/yr', coverage: 'Global', notes: 'Seismic events ≥M2.5; FDSN web service' },
      { name: 'USGS North American Magnetic Anomaly Grid', tier: 1, records: '~200k grid cells', coverage: 'North America', notes: '1km resolution aeromagnetic compilation' },
      { name: 'USGS Geologic Radon Potential', tier: 1, records: 'County-level', coverage: 'Contiguous US', notes: 'Geologic radon potential by county/region' },
      { name: 'NASA FIRMS Thermal Anomaly Archive', tier: 1, records: '~1M events', coverage: 'Global', notes: 'MODIS + VIIRS; requires FIRMS API key' },
      { name: 'NOAA DART Buoy Network', tier: 1, records: '~60 buoys', coverage: 'Global oceans', notes: 'Deep ocean pressure; tsunami + acoustic' },
      { name: 'GPS-TEC Ionospheric Disturbance (IONEX)', tier: 1, records: 'Daily maps', coverage: 'Global', notes: 'CODE AIUB IONEX products; TEC anomalies' },
      { name: 'EPA RadNet Radiation Monitoring', tier: 1, records: '~140 stations', coverage: 'US', notes: 'Continuous gamma radiation monitoring' },
      { name: 'DOE OE-417 Grid Disturbances', tier: 1, records: '~500/yr', coverage: 'US', notes: 'Grid emergency reports; includes unexplained' },
      { name: 'NRC + DOE Nuclear Facility Locations', tier: 1, records: '~200', coverage: 'US', notes: 'NRC FOIA reactor database + DOE sites' },
      { name: 'NASA GRACE Gravity Anomaly', tier: 1, records: 'Grid', coverage: 'Global', notes: 'Gravity Recovery and Climate Experiment' },
      { name: 'NOAA Marine Mammal Unusual Mortality Events', tier: 1, records: '~500', coverage: 'US coastal', notes: 'Declared UMEs 1991-present; MMPA mandated' },
    ],
  },
  {
    group: 'Tier 1 — Foreign Government Databases',
    items: [
      { name: 'GEIPAN Category D (CNES, France)', tier: 1, records: '~700', coverage: 'France', notes: 'Unexplained after rigorous CNES investigation; D2 = physical evidence' },
    ],
  },
  {
    group: 'Tier 2 — Institutional / Multi-witness',
    items: [
      { name: 'FOIA-derived UAP Institutional Records', tier: 2, records: '15+ key cases', coverage: 'US + global', notes: 'Nimitz, Gimbal, GoFast, AARO Vol 1, Grusch testimony' },
      { name: 'OpenSky ADS-B Traffic + Coverage Gaps', tier: 2, records: '~100k/day', coverage: 'Global', notes: 'Coverage gaps indicate radar shadow zones; control mask' },
      { name: 'NOAA SWPC Space Weather Events', tier: 2, records: '~2,000', coverage: 'Global', notes: 'Solar flares, CME, geomagnetic storms; control mask' },
      { name: 'CTBTO IMS Infrasound Network', tier: 2, records: '50 stations', coverage: 'Global', notes: 'Nuclear monitoring dual-use; infrasound anomalies' },
      { name: 'VLF/ELF Electromagnetic Network', tier: 2, records: '~12 stations', coverage: 'Global', notes: 'SAO Observatory + amateur network; Schumann resonance' },
      { name: 'NOAA GOES IR Atmospheric Gravity Waves', tier: 2, records: 'Satellite imagery', coverage: 'Western hemisphere', notes: 'IR channel anomalies; atmospheric dynamics' },
      { name: 'Movebank Animal Migration Anomalies', tier: 2, records: '8 curated events', coverage: 'Zonal', notes: 'Behavioral anomalies from Movebank API + curated' },
      { name: 'FAA Wildlife Strike Database', tier: 2, records: '~200k', coverage: 'US', notes: 'Magnetoreceptive species elevated; strike clusters' },
      { name: 'NDBC Buoys + Maritime Anomaly Records', tier: 2, records: '~50 curated', coverage: 'Oceans', notes: 'USO encounters, navigation blackouts, acoustic events' },
      { name: 'Project Blue Book Unknowns (NICAP/NARA)', tier: 2, records: '701 unknowns', coverage: 'US', notes: 'Official Unknown classification after military investigation' },
      { name: 'Atmospheric Nuclear Test Dates', tier: 2, records: '528 tests', coverage: 'Global', notes: 'ICAN / Johnston Archive; 1945-1980 atmospheric tests' },
    ],
  },
  {
    group: 'Tier 3 — Public Report Databases',
    items: [
      { name: 'NUFORC UAP Sightings', tier: 3, records: '~150,000', coverage: 'Global, US-heavy', notes: '75-year archive; self-reported; strong reporting bias confound' },
      { name: 'BFRO Anomalous Observations', tier: 3, records: '~5,000', coverage: 'US/Canada', notes: 'Class A elevated confidence; data.world mirror' },
    ],
  },
  {
    group: 'Tier 3 — Manual / Curated Context Layers',
    items: [
      { name: 'Cattle Mutilation Cases', tier: 3, records: '~200', coverage: 'US', notes: 'Manually compiled; quality varies significantly' },
      { name: 'USO / Transmedium Incident Locations', tier: 3, records: '~50', coverage: 'Global', notes: 'Navy / civilian maritime transmedium encounters' },
      { name: 'Persistent Earth Lights / Spooklights', tier: 3, records: '~30', coverage: 'US/global', notes: 'Recurring unexplained light phenomena at fixed locations' },
      { name: 'Earthquake Light (EQL) Cases', tier: 3, records: '~60', coverage: 'Global', notes: 'Scientifically documented pre-seismic light phenomena' },
      { name: 'Black Budget / Government Research Sites', tier: 3, records: '~30', coverage: 'US', notes: 'Context layer; infrastructure confound indicator' },
      { name: 'Skyquake / Unexplained Boom Clusters', tier: 3, records: '~80', coverage: 'US', notes: 'Reported unexplained sonic booms; some military-confirmed' },
      { name: 'Indigenous Sacred Sites', tier: 3, records: '~100', coverage: 'US', notes: 'Context layer; intergenerational significance of locations' },
      { name: 'Solar Cycle Correlation Layer', tier: 3, records: 'Computed', coverage: 'Global/temporal', notes: 'SILSO sunspot data + UAP flap period cross-reference' },
    ],
  },
];

function TierBadge({ tier }) {
  const labels = { 1: 'T1', 2: 'T2', 3: 'T3' };
  const cls = styles[`tier${tier}`];
  return <span className={`${styles.tierBadge} ${cls}`}>{labels[tier]}</span>;
}

export default function SourcesPage() {
  return (
    <div className={styles.page}>
      <nav className={styles.nav}>
        <Link to="/" className={styles.navBrand}>◈ Anomaly Map</Link>
        <Link to="/map" className={styles.navLink}>Map</Link>
        <Link to="/about" className={styles.navLink}>About</Link>
        <Link to="/feedback" className={styles.navLink}>Suggest Dataset</Link>
      </nav>

      <main className={styles.main}>
        <h1 className={styles.pageTitle}>Data Sources</h1>
        <p className={styles.intro}>
          All datasets are public-access sources. Confidence tiers reflect
          instrument quality, institutional rigor, and verification level —
          not the extraordinary nature of the data.
        </p>

        {SOURCES.map(group => (
          <section key={group.group} className={styles.section}>
            <h2 className={styles.sectionTitle}>{group.group}</h2>
            <div className={styles.sourceTable}>
              {group.items.map(item => (
                <div key={item.name} className={styles.sourceRow}>
                  <div className={styles.sourceMain}>
                    <TierBadge tier={item.tier} />
                    <span className={styles.sourceName}>{item.name}</span>
                  </div>
                  <div className={styles.sourceMeta}>
                    <span className={styles.metaItem}>{item.records} records</span>
                    <span className={styles.metaItem}>{item.coverage}</span>
                  </div>
                  <p className={styles.sourceNote}>{item.notes}</p>
                </div>
              ))}
            </div>
          </section>
        ))}

        <div className={styles.footer}>
          <Link to="/feedback" className={styles.footerBtn}>Suggest a Dataset</Link>
          <Link to="/about" className={styles.footerLink}>Methodology</Link>
        </div>
      </main>
    </div>
  );
}
