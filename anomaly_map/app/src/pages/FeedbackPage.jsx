import React, { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import styles from './StaticPage.module.css';

const FEEDBACK_TYPES = [
  { id: 'dataset_suggestion', label: 'Suggest a Dataset' },
  { id: 'bad_data_report',    label: 'Report Bad Data' },
  { id: 'explanation_suggestion', label: 'Suggest an Explanation' },
  { id: 'source_submission',  label: 'Submit a Source' },
  { id: 'feature_request',    label: 'Feature Request' },
  { id: 'other',              label: 'Other' },
];

const PROBLEM_TYPES = [
  { id: 'wrong_location', label: 'Wrong location' },
  { id: 'duplicate',      label: 'Duplicate / same event' },
  { id: 'bad_source',     label: 'Questionable source' },
  { id: 'likely_conventional', label: 'Likely conventional explanation' },
  { id: 'outdated',       label: 'Outdated data' },
  { id: 'other',          label: 'Other' },
];

function DatasetFields({ form, onChange }) {
  return (
    <>
      <div className={styles.fieldGroup}>
        <label className={styles.label}>Dataset name *</label>
        <input className={styles.input} name="dataset_name" value={form.dataset_name || ''} onChange={onChange} placeholder="e.g. AATIP Medical Cases" />
      </div>
      <div className={styles.fieldGroup}>
        <label className={styles.label}>Dataset URL</label>
        <input className={styles.input} type="url" name="source_url" value={form.source_url || ''} onChange={onChange} placeholder="https://..." />
      </div>
      <div className={styles.fieldRow}>
        <div className={styles.fieldGroup}>
          <label className={styles.label}>Has lat/lon?</label>
          <select className={styles.select} name="has_lat_lon" value={form.has_lat_lon || ''} onChange={onChange}>
            <option value="">Unknown</option>
            <option value="yes">Yes</option>
            <option value="no">No</option>
          </select>
        </div>
        <div className={styles.fieldGroup}>
          <label className={styles.label}>Has timestamps?</label>
          <select className={styles.select} name="has_timestamps" value={form.has_timestamps || ''} onChange={onChange}>
            <option value="">Unknown</option>
            <option value="yes">Yes</option>
            <option value="no">No</option>
          </select>
        </div>
        <div className={styles.fieldGroup}>
          <label className={styles.label}>Public access?</label>
          <select className={styles.select} name="public_access" value={form.public_access || ''} onChange={onChange}>
            <option value="">Unknown</option>
            <option value="yes">Yes</option>
            <option value="no">No</option>
          </select>
        </div>
      </div>
      <div className={styles.fieldGroup}>
        <label className={styles.label}>Why relevant to anomaly convergence?</label>
        <textarea className={styles.textarea} name="why_relevant" value={form.why_relevant || ''} onChange={onChange} rows={3} />
      </div>
      <div className={styles.fieldGroup}>
        <label className={styles.label}>Known limitations</label>
        <textarea className={styles.textarea} name="known_limitations" value={form.known_limitations || ''} onChange={onChange} rows={2} />
      </div>
    </>
  );
}

function BadDataFields({ form, onChange }) {
  return (
    <>
      <div className={styles.fieldGroup}>
        <label className={styles.label}>Problem type</label>
        <select className={styles.select} name="problem_type" value={form.problem_type || ''} onChange={onChange}>
          <option value="">Select…</option>
          {PROBLEM_TYPES.map(p => <option key={p.id} value={p.id}>{p.label}</option>)}
        </select>
      </div>
      <div className={styles.fieldGroup}>
        <label className={styles.label}>Correction / what should change</label>
        <textarea className={styles.textarea} name="correction_summary" value={form.correction_summary || ''} onChange={onChange} rows={3} />
      </div>
      <div className={styles.fieldGroup}>
        <label className={styles.label}>Evidence URL (optional)</label>
        <input className={styles.input} type="url" name="evidence_url" value={form.evidence_url || ''} onChange={onChange} placeholder="https://..." />
      </div>
    </>
  );
}

function ExplanationFields({ form, onChange }) {
  return (
    <>
      <div className={styles.fieldGroup}>
        <label className={styles.label}>Proposed explanation *</label>
        <textarea className={styles.textarea} name="proposed_explanation" value={form.proposed_explanation || ''} onChange={onChange} rows={3} />
      </div>
      <div className={styles.fieldGroup}>
        <label className={styles.label}>Evidence for this explanation</label>
        <textarea className={styles.textarea} name="evidence_for_explanation" value={form.evidence_for_explanation || ''} onChange={onChange} rows={3} />
      </div>
      <div className={styles.fieldGroup}>
        <label className={styles.label}>Source URL (optional)</label>
        <input className={styles.input} type="url" name="source_url" value={form.source_url || ''} onChange={onChange} placeholder="https://..." />
      </div>
    </>
  );
}

export default function FeedbackPage() {
  const [params] = useSearchParams();
  const [type, setType] = useState(params.get('type') || '');
  const [form, setForm] = useState({
    zone: params.get('zone') || '',
    related_hotspot_slug: params.get('related_hotspot_slug') || '',
    title: '',
    description: '',
    name_optional: '',
    email_optional: '',
    confidence: 'medium',
    public_source_confirmed: false,
    permission_to_contact: false,
  });
  const [submitted, setSubmitted] = useState(false);

  const onChange = e => {
    const { name, value, type: t, checked } = e.target;
    setForm(f => ({ ...f, [name]: t === 'checkbox' ? checked : value }));
  };

  const handleSubmit = e => {
    e.preventDefault();
    const payload = { feedback_type: type, ...form, submitted_at: new Date().toISOString(), status: 'New' };
    console.log('[Feedback submission]', payload);
    // TODO: POST to /api/feedback or write to local JSON store
    setSubmitted(true);
  };

  if (submitted) {
    return (
      <div className={styles.page}>
        <nav className={styles.nav}>
          <Link to="/" className={styles.navBrand}>◈ Anomaly Map</Link>
        </nav>
        <main className={styles.main}>
          <div className={styles.successBox}>
            <h2 className={styles.successTitle}>Thank you</h2>
            <p>Your feedback has been logged for review. Submissions are reviewed before affecting the map.</p>
            <div className={styles.footer}>
              <Link to="/map" className={styles.footerBtn}>Return to Map</Link>
              <Link to="/feedback" className={styles.footerLink}>Submit another</Link>
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <nav className={styles.nav}>
        <Link to="/" className={styles.navBrand}>◈ Anomaly Map</Link>
        <Link to="/map" className={styles.navLink}>Map</Link>
        <Link to="/about" className={styles.navLink}>About</Link>
      </nav>

      <main className={styles.main}>
        <h1 className={styles.pageTitle}>Feedback</h1>

        <div className={styles.disclaimer}>
          Help improve the map. Suggest public datasets, report bad data, submit sources,
          or propose ordinary explanations for hotspots.
          <br /><br />
          <strong>Submissions do not automatically appear on the map.</strong>{' '}
          Every suggestion is reviewed before it can affect scoring or public layers.
          Please submit public sources only — no private personal information,
          medical records, home addresses, or unverified accusations.
        </div>

        <form className={styles.form} onSubmit={handleSubmit}>
          <div className={styles.fieldGroup}>
            <label className={styles.label}>Feedback type *</label>
            <div className={styles.typeGrid}>
              {FEEDBACK_TYPES.map(t => (
                <button
                  key={t.id}
                  type="button"
                  className={`${styles.typeBtn} ${type === t.id ? styles.typeActive : ''}`}
                  onClick={() => setType(t.id)}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          {type && (
            <>
              <div className={styles.fieldGroup}>
                <label className={styles.label}>Title *</label>
                <input className={styles.input} name="title" value={form.title} onChange={onChange} placeholder="Brief title" required />
              </div>

              <div className={styles.fieldGroup}>
                <label className={styles.label}>Description</label>
                <textarea className={styles.textarea} name="description" value={form.description} onChange={onChange} rows={4} />
              </div>

              {form.zone && (
                <div className={styles.fieldGroup}>
                  <label className={styles.label}>Related zone</label>
                  <input className={styles.input} name="zone" value={form.zone} onChange={onChange} />
                </div>
              )}

              {type === 'dataset_suggestion'   && <DatasetFields     form={form} onChange={onChange} />}
              {type === 'bad_data_report'       && <BadDataFields      form={form} onChange={onChange} />}
              {type === 'explanation_suggestion'&& <ExplanationFields  form={form} onChange={onChange} />}

              <div className={styles.fieldRow}>
                <div className={styles.fieldGroup}>
                  <label className={styles.label}>Your confidence</label>
                  <select className={styles.select} name="confidence" value={form.confidence} onChange={onChange}>
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                </div>
              </div>

              <div className={styles.fieldRow}>
                <div className={styles.fieldGroup}>
                  <label className={styles.label}>Name (optional)</label>
                  <input className={styles.input} name="name_optional" value={form.name_optional} onChange={onChange} />
                </div>
                <div className={styles.fieldGroup}>
                  <label className={styles.label}>Email (optional)</label>
                  <input className={styles.input} type="email" name="email_optional" value={form.email_optional} onChange={onChange} />
                </div>
              </div>

              <div className={styles.checkboxRow}>
                <label className={styles.checkboxLabel}>
                  <input type="checkbox" name="public_source_confirmed" checked={form.public_source_confirmed} onChange={onChange} />
                  I confirm this is a public source — no private data, personal records, or home addresses
                </label>
              </div>
              <div className={styles.checkboxRow}>
                <label className={styles.checkboxLabel}>
                  <input type="checkbox" name="permission_to_contact" checked={form.permission_to_contact} onChange={onChange} />
                  You may contact me with follow-up questions
                </label>
              </div>

              <button type="submit" className={styles.submitBtn} disabled={!form.title || !type}>
                Submit for Review
              </button>
            </>
          )}
        </form>
      </main>
    </div>
  );
}
