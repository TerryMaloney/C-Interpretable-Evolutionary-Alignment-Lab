import React from 'react';
import { useStore } from '../store/useStore.js';
import styles from './LoadingOverlay.module.css';

export default function LoadingOverlay() {
  const { isLoading, loadingMessage, error, setError } = useStore();

  if (error) {
    return (
      <div className={styles.overlay}>
        <div className={styles.errorBox}>
          <div className={styles.errorTitle}>Error</div>
          <div className={styles.errorMsg}>{error}</div>
          <button className={styles.dismissBtn} onClick={() => setError(null)}>Dismiss</button>
        </div>
      </div>
    );
  }

  if (!isLoading) return null;

  return (
    <div className={styles.overlay}>
      <div className={styles.spinner}>
        <div className={styles.ring} />
        <div className={styles.msg}>{loadingMessage || 'Loading…'}</div>
      </div>
    </div>
  );
}
