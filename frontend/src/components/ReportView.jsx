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
  issueIntegrity: {
    borderLeft: '4px solid #6f42c1',
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
  umlClass: {
    backgroundColor: '#fff',
    border: '1px solid #333',
    borderRadius: '4px',
    marginBottom: '12px',
    overflow: 'hidden',
  },
  umlClassName: {
    backgroundColor: '#333',
    color: '#fff',
    padding: '8px 12px',
    fontWeight: '600',
    textAlign: 'center',
  },
  umlAttributes: {
    padding: '8px 12px',
    borderBottom: '1px solid #ddd',
    fontSize: '13px',
    fontFamily: 'monospace',
  },
  umlAttribute: {
    padding: '2px 0',
  },
  umlKey: {
    fontSize: '10px',
    padding: '1px 4px',
    borderRadius: '2px',
    marginLeft: '6px',
  },
  umlPK: {
    backgroundColor: '#ffc107',
    color: '#333',
  },
  umlFK: {
    backgroundColor: '#17a2b8',
    color: '#fff',
  },
  coverageItem: {
    padding: '10px 12px',
    backgroundColor: '#fff',
    borderRadius: '4px',
    marginBottom: '8px',
    border: '1px solid #ddd',
  },
  coverageFullyCovered: {
    borderLeft: '4px solid #28a745',
  },
  coveragePartiallyCovered: {
    borderLeft: '4px solid #ffc107',
  },
  coverageNotCovered: {
    borderLeft: '4px solid #dc3545',
  },
  coverageStatus: {
    fontSize: '12px',
    padding: '2px 6px',
    borderRadius: '3px',
    marginLeft: '8px',
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

function UMLClassDiagram({ umlStructure }) {
  if (!umlStructure || !umlStructure.classes || umlStructure.classes.length === 0) {
    return null;
  }

  return (
    <div style={styles.section}>
      <h3 style={styles.sectionTitle}>UML Class Diagram</h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '16px' }}>
        {umlStructure.classes.map((cls, idx) => (
          <div key={idx} style={styles.umlClass}>
            <div style={styles.umlClassName}>{cls.name}</div>
            <div style={styles.umlAttributes}>
              {cls.attributes && cls.attributes.length > 0 ? (
                cls.attributes.map((attr, attrIdx) => (
                  <div key={attrIdx} style={styles.umlAttribute}>
                    {attr.visibility === 'private' ? '-' : attr.visibility === 'protected' ? '#' : '+'}
                    {' '}{attr.name}: {attr.type}
                    {attr.is_primary_key && <span style={{ ...styles.umlKey, ...styles.umlPK }}>PK</span>}
                    {attr.is_foreign_key && <span style={{ ...styles.umlKey, ...styles.umlFK }}>FK</span>}
                  </div>
                ))
              ) : (
                <div style={{ color: '#999', fontStyle: 'italic' }}>No attributes</div>
              )}
            </div>
          </div>
        ))}
      </div>
      
      {/* Associations */}
      {umlStructure.associations && umlStructure.associations.length > 0 && (
        <div style={{ marginTop: '16px' }}>
          <strong>Relationships:</strong>
          <div style={{ marginTop: '8px' }}>
            {umlStructure.associations.map((assoc, idx) => (
              <div key={idx} style={{ padding: '6px 0', borderBottom: '1px solid #eee' }}>
                <strong>{assoc.source}</strong>
                {' '}{assoc.source_multiplicity}{' '}
                <span style={{ color: '#666' }}>
                  —[{assoc.association_type}]—
                </span>
                {' '}{assoc.target_multiplicity}{' '}
                <strong>{assoc.target}</strong>
                {assoc.label && <span style={{ color: '#666', marginLeft: '8px' }}>({assoc.label})</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      <details style={{ marginTop: '16px' }}>
        <summary style={{ cursor: 'pointer', marginBottom: '8px' }}>
          View Full UML Structure (JSON)
        </summary>
        <pre style={styles.erdStructure}>
          {JSON.stringify(umlStructure, null, 2)}
        </pre>
      </details>
    </div>
  );
}

function UserStoryCoverage({ coverage }) {
  if (!coverage || coverage.length === 0) return null;

  const getCoverageStyle = (status) => {
    switch (status) {
      case 'fully_covered': return styles.coverageFullyCovered;
      case 'partially_covered': return styles.coveragePartiallyCovered;
      case 'not_covered': return styles.coverageNotCovered;
      default: return {};
    }
  };

  const getCoverageStatusStyle = (status) => {
    switch (status) {
      case 'fully_covered': return { backgroundColor: '#d4edda', color: '#155724' };
      case 'partially_covered': return { backgroundColor: '#fff3cd', color: '#856404' };
      case 'not_covered': return { backgroundColor: '#f8d7da', color: '#721c24' };
      default: return {};
    }
  };

  const formatStatus = (status) => {
    return status.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  };

  return (
    <div style={styles.section}>
      <h3 style={styles.sectionTitle}>User Story Coverage</h3>
      {coverage.map((item, idx) => (
        <div key={idx} style={{ ...styles.coverageItem, ...getCoverageStyle(item.coverage_status) }}>
          <div style={{ marginBottom: '4px' }}>
            <strong>{item.story_summary}</strong>
            <span style={{ ...styles.coverageStatus, ...getCoverageStatusStyle(item.coverage_status) }}>
              {formatStatus(item.coverage_status)}
            </span>
          </div>
          {item.notes && <div style={styles.issueReason}>{item.notes}</div>}
        </div>
      ))}
    </div>
  );
}

export default function ReportView({ analysis, onBack }) {
  const { status, extracted_erd, uml_structure, report, error_message } = analysis;

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
          <p style={{ fontSize: '14px', color: '#666', marginTop: '8px' }}>
            This may take a minute for complex diagrams.
          </p>
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

  // Use uml_structure if available (new format), otherwise fall back to extracted_erd (legacy)
  const structure = uml_structure || extracted_erd;

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

      {/* User Story Coverage (new) */}
      <UserStoryCoverage coverage={report?.user_story_coverage} />

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
            {issue.suggested_multiplicity && (
              <small style={{ marginLeft: '8px' }}>Multiplicity: {issue.suggested_multiplicity}</small>
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
              {issue.attribute_type && <span style={{ color: '#666' }}> : {issue.attribute_type}</span>}
            </div>
            <div style={styles.issueReason}>{issue.reason}</div>
          </>
        )}
      />

      {/* Data Integrity Concerns (new) */}
      <IssueList
        title="Data Integrity Concerns"
        issues={report?.data_integrity_concerns}
        style={styles.issueIntegrity}
        renderItem={(issue) => (
          <>
            <div style={styles.issueName}>{issue.concern}</div>
            {issue.affected_entities && (
              <div style={{ marginBottom: '4px' }}>
                <small>Affected: {issue.affected_entities.join(', ')}</small>
              </div>
            )}
            <div style={styles.issueReason}>{issue.recommendation}</div>
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

      {/* UML Structure (new format) */}
      {uml_structure && <UMLClassDiagram umlStructure={uml_structure} />}

      {/* Legacy ERD Structure (fallback) */}
      {!uml_structure && extracted_erd && (
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
