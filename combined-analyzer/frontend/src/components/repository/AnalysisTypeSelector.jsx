import React from 'react';

const styles = {
  container: {},
  title: {
    margin: '0 0 16px 0',
    fontSize: '16px',
    color: '#333',
  },
  options: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '12px',
  },
  option: {
    padding: '14px',
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
  optionHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '6px',
  },
  checkbox: {
    width: '18px',
    height: '18px',
    cursor: 'pointer',
  },
  optionTitle: {
    fontSize: '14px',
    fontWeight: '600',
    color: '#333',
  },
  optionIcon: {
    fontSize: '20px',
  },
  optionDescription: {
    fontSize: '12px',
    color: '#666',
    lineHeight: 1.4,
    marginLeft: '26px',
  },
  statusBadge: {
    fontSize: '10px',
    padding: '2px 6px',
    borderRadius: '10px',
    marginLeft: '6px',
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

const analysisOptions = [
  {
    key: 'erd',
    icon: '&#128202;',
    title: 'ERD Analysis',
    description: 'Analyze ERD diagrams against user stories for coverage gaps.',
    canField: 'canAnalyzeErd',
  },
  {
    key: 'integrity',
    icon: '&#128274;',
    title: 'Integrity',
    description: 'Confidentiality, authenticity, non-repudiation, resistance.',
    canField: 'canAnalyzeIntegrity',
  },
  {
    key: 'compliance',
    icon: '&#9989;',
    title: 'Compliance',
    description: 'Functional completeness, correctness, and appropriateness.',
    canField: 'canAnalyzeCompliance',
  },
  {
    key: 'correctness',
    icon: '&#10004;',
    title: 'Correctness',
    description: 'Computation accuracy, off-by-one errors, precision issues.',
    canField: 'canAnalyzeCorrectness',
  },
  {
    key: 'usability',
    icon: '&#128100;',
    title: 'Usability',
    description: 'Learnability, operability, accessibility, error protection.',
    canField: 'canAnalyzeUsability',
  },
  {
    key: 'maintainability',
    icon: '&#9881;',
    title: 'Maintainability',
    description: 'Modularity, reusability, analysability, testability.',
    canField: 'canAnalyzeMaintainability',
  },
];

export default function AnalysisTypeSelector({
  analysisTypes, onChange,
  canAnalyzeErd, canAnalyzeIntegrity,
  canAnalyzeCompliance = false, canAnalyzeCorrectness = false,
  canAnalyzeUsability = false, canAnalyzeMaintainability = false,
}) {
  const canMap = {
    canAnalyzeErd,
    canAnalyzeIntegrity,
    canAnalyzeCompliance,
    canAnalyzeCorrectness,
    canAnalyzeUsability,
    canAnalyzeMaintainability,
  };

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
        {analysisOptions.map((opt) => {
          const canRun = canMap[opt.canField];
          return (
            <div
              key={opt.key}
              style={{
                ...styles.option,
                ...(analysisTypes[opt.key] ? styles.optionSelected : {}),
              }}
              onClick={() => handleToggle(opt.key)}
            >
              <div style={styles.optionHeader}>
                <input
                  type="checkbox"
                  checked={!!analysisTypes[opt.key]}
                  onChange={() => handleToggle(opt.key)}
                  style={styles.checkbox}
                />
                <span style={styles.optionIcon} dangerouslySetInnerHTML={{ __html: opt.icon }} />
                <span style={styles.optionTitle}>{opt.title}</span>
                <span
                  style={{
                    ...styles.statusBadge,
                    ...(canRun ? styles.statusReady : styles.statusNotReady),
                  }}
                >
                  {canRun ? 'Ready' : 'Need Files'}
                </span>
              </div>
              <p style={styles.optionDescription}>{opt.description}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
