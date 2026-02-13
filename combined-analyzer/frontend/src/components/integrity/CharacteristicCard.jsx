import React, { useState } from 'react';

const styles = {
  card: {
    backgroundColor: '#fff',
    border: '1px solid #e0e0e0',
    borderRadius: '12px',
    overflow: 'hidden',
  },
  cardHeader: {
    padding: '18px 20px',
    borderBottom: '1px solid #e0e0e0',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  cardTitleSection: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  cardIcon: {
    fontSize: '20px',
  },
  cardTitle: {
    fontSize: '15px',
    fontWeight: '600',
    color: '#1e3a5f',
  },
  cardScoreSection: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  statusBadge: {
    padding: '4px 10px',
    borderRadius: '10px',
    fontSize: '11px',
    fontWeight: '500',
  },
  statusFulfilled: {
    backgroundColor: '#e8f5e9',
    color: '#2e7d32',
  },
  statusPartial: {
    backgroundColor: '#fff3e0',
    color: '#ef6c00',
  },
  statusNotFulfilled: {
    backgroundColor: '#ffebee',
    color: '#c62828',
  },
  statusNA: {
    backgroundColor: '#f5f5f5',
    color: '#666',
  },
  cardScore: {
    fontSize: '20px',
    fontWeight: '700',
  },
  cardBody: {
    padding: '18px 20px',
  },
  description: {
    color: '#666',
    fontSize: '13px',
    lineHeight: 1.5,
    marginBottom: '14px',
  },
  findingsSection: {
    marginTop: '14px',
  },
  findingsTitle: {
    fontSize: '13px',
    fontWeight: '600',
    marginBottom: '10px',
    color: '#333',
  },
  finding: {
    backgroundColor: '#f9f9f9',
    borderRadius: '8px',
    padding: '12px',
    marginBottom: '10px',
    borderLeft: '4px solid',
  },
  findingPositive: {
    borderLeftColor: '#4caf50',
  },
  findingNegative: {
    borderLeftColor: '#f44336',
  },
  findingWarning: {
    borderLeftColor: '#ff9800',
  },
  findingHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '8px',
  },
  findingFile: {
    fontFamily: 'monospace',
    fontSize: '12px',
    color: '#1565c0',
  },
  findingType: {
    fontSize: '10px',
    fontWeight: '500',
    padding: '2px 8px',
    borderRadius: '10px',
  },
  codeSnippet: {
    backgroundColor: '#263238',
    color: '#aed581',
    padding: '10px',
    borderRadius: '6px',
    fontFamily: 'monospace',
    fontSize: '12px',
    overflowX: 'auto',
    marginBottom: '8px',
    whiteSpace: 'pre-wrap',
  },
  findingExplanation: {
    fontSize: '12px',
    color: '#555',
    lineHeight: 1.4,
  },
  recommendations: {
    marginTop: '14px',
    padding: '14px',
    backgroundColor: '#e3f2fd',
    borderRadius: '8px',
  },
  recommendationsTitle: {
    fontSize: '13px',
    fontWeight: '600',
    marginBottom: '10px',
    color: '#1565c0',
  },
  recommendation: {
    fontSize: '12px',
    marginBottom: '5px',
    paddingLeft: '14px',
    position: 'relative',
  },
  expandButton: {
    background: 'none',
    border: 'none',
    color: '#1565c0',
    cursor: 'pointer',
    fontSize: '12px',
    padding: '6px 0',
  },
};

function getScoreColor(score) {
  if (score >= 80) return '#4caf50';
  if (score >= 60) return '#ff9800';
  if (score >= 40) return '#f57c00';
  return '#f44336';
}

function getStatusStyle(status) {
  switch (status) {
    case 'fulfilled': return styles.statusFulfilled;
    case 'partially_fulfilled': return styles.statusPartial;
    case 'not_fulfilled': return styles.statusNotFulfilled;
    default: return styles.statusNA;
  }
}

function formatStatus(status) {
  return status?.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()) || 'Unknown';
}

function getFindingStyle(type) {
  switch (type) {
    case 'positive': return styles.findingPositive;
    case 'negative': return styles.findingNegative;
    default: return styles.findingWarning;
  }
}

function getFindingTypeStyle(type) {
  switch (type) {
    case 'positive':
      return { backgroundColor: '#e8f5e9', color: '#2e7d32' };
    case 'negative':
      return { backgroundColor: '#ffebee', color: '#c62828' };
    default:
      return { backgroundColor: '#fff3e0', color: '#ef6c00' };
  }
}

export default function CharacteristicCard({ data, icon }) {
  const [expanded, setExpanded] = useState(false);

  if (!data) return null;

  const visibleFindings = expanded ? data.findings : data.findings?.slice(0, 2);

  return (
    <div style={styles.card}>
      <div style={styles.cardHeader}>
        <div style={styles.cardTitleSection}>
          <span style={styles.cardIcon} dangerouslySetInnerHTML={{ __html: icon }} />
          <span style={styles.cardTitle}>{data.characteristic}</span>
        </div>
        <div style={styles.cardScoreSection}>
          <span style={{ ...styles.statusBadge, ...getStatusStyle(data.status) }}>
            {formatStatus(data.status)}
          </span>
          <span style={{ ...styles.cardScore, color: getScoreColor(data.score) }}>
            {Math.round(data.score)}%
          </span>
        </div>
      </div>

      <div style={styles.cardBody}>
        <p style={styles.description}>{data.description}</p>

        {data.findings?.length > 0 && (
          <div style={styles.findingsSection}>
            <div style={styles.findingsTitle}>Findings ({data.findings.length})</div>
            {visibleFindings.map((finding, i) => (
              <div key={i} style={{ ...styles.finding, ...getFindingStyle(finding.type) }}>
                <div style={styles.findingHeader}>
                  <span style={styles.findingFile}>
                    {finding.file_path}
                    {finding.line_number && `:${finding.line_number}`}
                  </span>
                  <span style={{ ...styles.findingType, ...getFindingTypeStyle(finding.type) }}>
                    {finding.type}
                  </span>
                </div>
                {finding.code_snippet && (
                  <div style={styles.codeSnippet}>{finding.code_snippet}</div>
                )}
                <div style={styles.findingExplanation}>{finding.explanation}</div>
              </div>
            ))}
            {data.findings.length > 2 && (
              <button style={styles.expandButton} onClick={() => setExpanded(!expanded)}>
                {expanded ? '&#9650; Show less' : `&#9660; Show ${data.findings.length - 2} more findings`}
              </button>
            )}
          </div>
        )}

        {data.recommendations?.length > 0 && (
          <div style={styles.recommendations}>
            <div style={styles.recommendationsTitle}>Recommendations</div>
            {data.recommendations.map((rec, i) => (
              <div key={i} style={styles.recommendation}>&#8226; {rec}</div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
