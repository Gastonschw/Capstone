import React from 'react';

const styles = {
  container: {},
  title: {
    margin: '0 0 16px 0',
    fontSize: '16px',
    color: '#333',
  },
  options: {
    display: 'flex',
    gap: '16px',
  },
  option: {
    flex: 1,
    padding: '16px',
    border: '2px solid #e0e0e0',
    borderRadius: '12px',
    cursor: 'pointer',
    transition: 'all 0.2s',
    backgroundColor: '#fff',
  },
  optionSelected: {
    borderColor: '#1e3a5f',
    backgroundColor: '#f0f7ff',
  },
  optionDisabled: {
    opacity: 0.5,
    cursor: 'not-allowed',
  },
  optionHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    marginBottom: '8px',
  },
  checkbox: {
    width: '20px',
    height: '20px',
    cursor: 'pointer',
  },
  optionTitle: {
    fontSize: '16px',
    fontWeight: '600',
    color: '#333',
  },
  optionIcon: {
    fontSize: '24px',
  },
  optionDescription: {
    fontSize: '13px',
    color: '#666',
    lineHeight: 1.5,
    marginLeft: '32px',
  },
  statusBadge: {
    fontSize: '11px',
    padding: '2px 8px',
    borderRadius: '10px',
    marginLeft: '8px',
  },
  statusReady: {
    backgroundColor: '#d4edda',
    color: '#155724',
  },
  statusNotReady: {
    backgroundColor: '#f8d7da',
    color: '#721c24',
  },
};

export default function AnalysisTypeSelector({ analysisTypes, onChange, canAnalyzeErd, canAnalyzeIntegrity }) {
  const handleToggle = (type) => {
    onChange({
      ...analysisTypes,
      [type]: !analysisTypes[type],
    });
  };

  return (
    <div style={styles.container}>
      <h3 style={styles.title}>Select Analysis Type</h3>
      <div style={styles.options}>
        <div
          style={{
            ...styles.option,
            ...(analysisTypes.erd ? styles.optionSelected : {}),
          }}
          onClick={() => handleToggle('erd')}
        >
          <div style={styles.optionHeader}>
            <input
              type="checkbox"
              checked={analysisTypes.erd}
              onChange={() => handleToggle('erd')}
              style={styles.checkbox}
            />
            <span style={styles.optionIcon}>&#128202;</span>
            <span style={styles.optionTitle}>ERD Analysis</span>
            <span
              style={{
                ...styles.statusBadge,
                ...(canAnalyzeErd ? styles.statusReady : styles.statusNotReady),
              }}
            >
              {canAnalyzeErd ? 'Ready' : 'Need Files'}
            </span>
          </div>
          <p style={styles.optionDescription}>
            Analyze ERD diagrams against user stories to identify missing entities,
            relationships, and coverage gaps.
          </p>
        </div>

        <div
          style={{
            ...styles.option,
            ...(analysisTypes.integrity ? styles.optionSelected : {}),
          }}
          onClick={() => handleToggle('integrity')}
        >
          <div style={styles.optionHeader}>
            <input
              type="checkbox"
              checked={analysisTypes.integrity}
              onChange={() => handleToggle('integrity')}
              style={styles.checkbox}
            />
            <span style={styles.optionIcon}>&#128274;</span>
            <span style={styles.optionTitle}>Integrity Analysis</span>
            <span
              style={{
                ...styles.statusBadge,
                ...(canAnalyzeIntegrity ? styles.statusReady : styles.statusNotReady),
              }}
            >
              {canAnalyzeIntegrity ? 'Ready' : 'Need Files'}
            </span>
          </div>
          <p style={styles.optionDescription}>
            Assess security characteristics: Confidentiality, Data Integrity,
            Authenticity, Non-Repudiation, Accountability, and Resistance.
          </p>
        </div>
      </div>
    </div>
  );
}
