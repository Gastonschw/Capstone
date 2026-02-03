import React from 'react';

const styles = {
  container: {
    backgroundColor: '#fff',
    borderRadius: '8px',
    padding: '24px',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '20px',
  },
  title: {
    margin: 0,
    color: '#333',
  },
  backButton: {
    backgroundColor: '#6c757d',
    color: '#fff',
    border: 'none',
    padding: '8px 16px',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  statusBadge: {
    display: 'inline-block',
    padding: '4px 12px',
    borderRadius: '12px',
    fontSize: '14px',
    fontWeight: '600',
  },
  statusPending: {
    backgroundColor: '#fff3cd',
    color: '#856404',
  },
  statusProcessing: {
    backgroundColor: '#cce5ff',
    color: '#004085',
  },
  statusCompleted: {
    backgroundColor: '#d4edda',
    color: '#155724',
  },
  statusFailed: {
    backgroundColor: '#f8d7da',
    color: '#721c24',
  },
  section: {
    marginBottom: '24px',
    padding: '16px',
    backgroundColor: '#f8f9fa',
    borderRadius: '4px',
  },
  sectionTitle: {
    margin: '0 0 12px 0',
    fontSize: '18px',
    color: '#333',
  },
  scoreContainer: {
    textAlign: 'center',
    padding: '20px',
  },
  scoreValue: {
    fontSize: '48px',
    fontWeight: 'bold',
  },
  scoreLabel: {
    fontSize: '14px',
    color: '#666',
  },
  issueCard: {
    backgroundColor: '#fff',
    border: '1px solid #ddd',
    borderRadius: '4px',
    padding: '12px',
    marginBottom: '8px',
  },
  issueMissing: {
    borderLeft: '4px solid #dc3545',
  },
  issueRelationship: {
    borderLeft: '4px solid #fd7e14',
  },
  issueCardinality: {
    borderLeft: '4px solid #ffc107',
  },
  issueOrphaned: {
    borderLeft: '4px solid #6c757d',
  },
  issueAttribute: {
    borderLeft: '4px solid #17a2b8',
  },
  issueName: {
    fontWeight: '600',
    marginBottom: '4px',
  },
  issueReason: {
    fontSize: '14px',
    color: '#666',
  },
  entityList: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '8px',
  },
  entityChip: {
    backgroundColor: '#e9ecef',
    padding: '4px 12px',
    borderRadius: '16px',
    fontSize: '14px',
  },
  loading: {
    textAlign: 'center',
    padding: '40px',
  },
  spinner: {
    display: 'inline-block',
    width: '40px',
    height: '40px',
    border: '4px solid #f3f3f3',
    borderTop: '4px solid #007bff',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
  },
  summary: {
    fontSize: '16px',
    lineHeight: '1.6',
    color: '#333',
  },
  recommendation: {
    padding: '8px 12px',
    backgroundColor: '#e7f3ff',
    borderRadius: '4px',
    marginBottom: '8px',
  },
  error: {
    color: '#dc3545',
    padding: '20px',
    textAlign: 'center',
  },
  erdStructure: {
    fontFamily: 'monospace',
    fontSize: '12px',
    backgroundColor: '#fff',
    padding: '12px',
    borderRadius: '4px',
    overflow: 'auto',
    maxHeight: '300px',
  },
};

function getScoreColor(score) {
  if (score >= 80) return '#28a745';
  if (score >= 60) return '#ffc107';
  if (score >= 40) return '#fd7e14';
  return '#dc3545';
}

function StatusBadge({ status }) {
  const statusStyles = {
    pending: styles.statusPending,
    processing: styles.statusProcessing,
    completed: styles.statusCompleted,
    failed: styles.statusFailed,
  };

  return (
    <span style={{ ...styles.statusBadge, ...statusStyles[status] }}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

function IssueList({ title, issues, style, renderItem }) {
  if (!issues || issues.length === 0) return null;

  return (
    <div style={styles.section}>
      <h3 style={styles.sectionTitle}>
        {title} ({issues.length})
      </h3>
      {issues.map((issue, idx) => (
        <div key={idx} style={{ ...styles.issueCard, ...style }}>
          {renderItem(issue)}
        </div>
      ))}
    </div>
  );
}

export default function ReportView({ analysis, onBack }) {
  const { status, extracted_erd, report, error_message } = analysis;

  if (status === 'pending' || status === 'processing') {
    return (
      <div style={styles.container}>
        <div style={styles.header}>
          <h2 style={styles.title}>Analysis in Progress</h2>
          <button onClick={onBack} style={styles.backButton}>
            Back
          </button>
        </div>
        <div style={styles.loading}>
          <div style={styles.spinner} />
          <p>Analyzing your ERD diagram...</p>
          <StatusBadge status={status} />
        </div>
        <style>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  if (status === 'failed') {
    return (
      <div style={styles.container}>
        <div style={styles.header}>
          <h2 style={styles.title}>Analysis Failed</h2>
          <button onClick={onBack} style={styles.backButton}>
            Back
          </button>
        </div>
        <div style={styles.error}>
          <p>An error occurred during analysis:</p>
          <p>{error_message || 'Unknown error'}</p>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h2 style={styles.title}>Analysis Report</h2>
        <button onClick={onBack} style={styles.backButton}>
          New Analysis
        </button>
      </div>

      {/* Coverage Score */}
      {report && (
        <div style={styles.scoreContainer}>
          <div
            style={{
              ...styles.scoreValue,
              color: getScoreColor(report.coverage_score),
            }}
          >
            {report.coverage_score}%
          </div>
          <div style={styles.scoreLabel}>Coverage Score</div>
        </div>
      )}

      {/* Summary */}
      {report?.summary && (
        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>Summary</h3>
          <p style={styles.summary}>{report.summary}</p>
        </div>
      )}

      {/* Missing Entities */}
      <IssueList
        title="Missing Entities"
        issues={report?.missing_entities}
        style={styles.issueMissing}
        renderItem={(issue) => (
          <>
            <div style={styles.issueName}>{issue.entity_name}</div>
            <div style={styles.issueReason}>{issue.reason}</div>
            {issue.suggested_attributes && (
              <div style={{ marginTop: '8px' }}>
                <small>Suggested attributes: {issue.suggested_attributes.join(', ')}</small>
              </div>
            )}
          </>
        )}
      />

      {/* Missing Relationships */}
      <IssueList
        title="Missing Relationships"
        issues={report?.missing_relationships}
        style={styles.issueRelationship}
        renderItem={(issue) => (
          <>
            <div style={styles.issueName}>
              {issue.from_entity} → {issue.to_entity}
            </div>
            <div style={styles.issueReason}>{issue.reason}</div>
            {issue.suggested_type && (
              <small>Suggested type: {issue.suggested_type}</small>
            )}
          </>
        )}
      />

      {/* Cardinality Issues */}
      <IssueList
        title="Cardinality Issues"
        issues={report?.cardinality_issues}
        style={styles.issueCardinality}
        renderItem={(issue) => (
          <>
            <div style={styles.issueName}>{issue.relationship}</div>
            <div style={styles.issueReason}>
              Current: {issue.current} → Suggested: {issue.suggested}
            </div>
            <div style={styles.issueReason}>{issue.reason}</div>
          </>
        )}
      />

      {/* Missing Attributes */}
      <IssueList
        title="Missing Attributes"
        issues={report?.missing_attributes}
        style={styles.issueAttribute}
        renderItem={(issue) => (
          <>
            <div style={styles.issueName}>
              {issue.entity_name}.{issue.attribute_name}
            </div>
            <div style={styles.issueReason}>{issue.reason}</div>
          </>
        )}
      />

      {/* Orphaned Entities */}
      <IssueList
        title="Orphaned Entities"
        issues={report?.orphaned_entities}
        style={styles.issueOrphaned}
        renderItem={(issue) => (
          <>
            <div style={styles.issueName}>{issue.entity_name}</div>
            <div style={styles.issueReason}>{issue.reason}</div>
          </>
        )}
      />

      {/* Recommendations */}
      {report?.recommendations && report.recommendations.length > 0 && (
        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>Recommendations</h3>
          {report.recommendations.map((rec, idx) => (
            <div key={idx} style={styles.recommendation}>
              {rec}
            </div>
          ))}
        </div>
      )}

      {/* Extracted ERD Structure */}
      {extracted_erd && (
        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>Extracted ERD Structure</h3>
          {extracted_erd.entities && (
            <div style={{ marginBottom: '12px' }}>
              <strong>Entities:</strong>
              <div style={styles.entityList}>
                {extracted_erd.entities.map((entity, idx) => (
                  <span key={idx} style={styles.entityChip}>
                    {entity.name}
                  </span>
                ))}
              </div>
            </div>
          )}
          <details>
            <summary style={{ cursor: 'pointer', marginBottom: '8px' }}>
              View Full Structure (JSON)
            </summary>
            <pre style={styles.erdStructure}>
              {JSON.stringify(extracted_erd, null, 2)}
            </pre>
          </details>
        </div>
      )}
    </div>
  );
}
