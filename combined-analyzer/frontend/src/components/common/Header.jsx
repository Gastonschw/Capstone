import React from 'react';

const styles = {
  header: {
    background: 'linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%)',
    color: '#fff',
    padding: '16px 24px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
  },
  logo: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  logoIcon: {
    fontSize: '28px',
  },
  title: {
    margin: 0,
    fontSize: '22px',
    fontWeight: '600',
  },
  subtitle: {
    margin: 0,
    fontSize: '12px',
    opacity: 0.8,
    marginTop: '2px',
  },
  badge: {
    backgroundColor: 'rgba(255,255,255,0.2)',
    padding: '6px 12px',
    borderRadius: '16px',
    fontSize: '12px',
    fontWeight: '500',
  },
};

export default function Header() {
  return (
    <header style={styles.header}>
      <div style={styles.logo}>
        <span style={styles.logoIcon}>&#128202;</span>
        <div>
          <h1 style={styles.title}>Combined Analyzer</h1>
          <p style={styles.subtitle}>ERD + Integrity Analysis Platform</p>
        </div>
      </div>
      <div style={styles.badge}>
        v1.0.0
      </div>
    </header>
  );
}
