import React, { useState, useEffect } from 'react';
import { getERDAnalysis, pollAnalysis } from '../../api';
import AnalysisChat from '../common/AnalysisChat';

const styles = {
  container: {
    backgroundColor: '#fff',
    borderRadius: '12px',
    padding: '24px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '24px',
  },
  title: {
    margin: 0,
    color: '#1e3a5f',
    fontSize: '20px',
  },
  backButton: {
    backgroundColor: '#e0e0e0',
    color: '#333',
    border: 'none',
    padding: '8px 16px',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '13px',
  },
  loading: {
    textAlign: 'center',
    padding: '60px',
    color: '#666',
  },
  spinner: {
    width: '50px',
    height: '50px',
    border: '4px solid #e0e0e0',
    borderTop: '4px solid #1e3a5f',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
    margin: '0 auto 20px',
  },
  error: {
    backgroundColor: '#f8d7da',
    color: '#721c24',
    padding: '20px',
    borderRadius: '8px',
    textAlign: 'center',
  },
  scoreContainer: {
    textAlign: 'center',
    padding: '24px',
    backgroundColor: '#f8f9fa',
    borderRadius: '12px',
    marginBottom: '24px',
  },
  scoreValue: {
    fontSize: '56px',
    fontWeight: '700',
  },
  scoreLabel: {
    fontSize: '14px',
    color: '#666',
    marginTop: '4px',
  },
  section: {
    marginBottom: '24px',
    padding: '20px',
    backgroundColor: '#f8f9fa',
    borderRadius: '8px',
  },
  sectionTitle: {
    margin: '0 0 16px 0',
    fontSize: '16px',
    color: '#333',
  },
  summary: {
    fontSize: '15px',
    lineHeight: 1.6,
    color: '#333',
  },
  issueCard: {
    backgroundColor: '#fff',
    border: '1px solid #ddd',
    borderRadius: '8px',
    padding: '14px',
    marginBottom: '10px',
  },
  issueMissing: { borderLeft: '4px solid #dc3545' },
  issueRelationship: { borderLeft: '4px solid #fd7e14' },
  issueCardinality: { borderLeft: '4px solid #ffc107' },
  issueOrphaned: { borderLeft: '4px solid #6c757d' },
  issueAttribute: { borderLeft: '4px solid #17a2b8' },
  issueIntegrity: { borderLeft: '4px solid #6f42c1' },
  issueName: {
    fontWeight: '600',
    marginBottom: '6px',
    color: '#333',
  },
  issueReason: {
    fontSize: '13px',
    color: '#666',
  },
  recommendation: {
    padding: '10px 14px',
    backgroundColor: '#e7f3ff',
    borderRadius: '6px',
    marginBottom: '8px',
    fontSize: '14px',
  },
  coverageItem: {
    padding: '12px 14px',
    backgroundColor: '#fff',
    borderRadius: '6px',
    marginBottom: '8px',
    border: '1px solid #ddd',
  },
  coverageFullyCovered: { borderLeft: '4px solid #28a745' },
  coveragePartiallyCovered: { borderLeft: '4px solid #ffc107' },
  coverageNotCovered: { borderLeft: '4px solid #dc3545' },
  coverageStatus: {
    fontSize: '11px',
    padding: '2px 8px',
    borderRadius: '4px',
    marginLeft: '8px',
  },
  umlGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))',
    gap: '16px',
  },
  umlClass: {
    backgroundColor: '#fff',
    border: '2px solid #333',
    borderRadius: '8px',
    overflow: 'hidden',
  },
  umlClassName: {
    backgroundColor: '#333',
    color: '#fff',
    padding: '10px 14px',
    fontWeight: '600',
    textAlign: 'center',
  },
  umlAttributes: {
    padding: '12px 14px',
    fontSize: '13px',
    fontFamily: 'monospace',
  },
  umlAttribute: {
    padding: '3px 0',
  },
  umlKey: {
    fontSize: '10px',
    padding: '1px 5px',
    borderRadius: '3px',
    marginLeft: '6px',
    fontWeight: '500',
  },
  umlPK: { backgroundColor: '#ffc107', color: '#333' },
  umlFK: { backgroundColor: '#17a2b8', color: '#fff' },
  jsonPreview: {
    fontFamily: 'monospace',
    fontSize: '12px',
    backgroundColor: '#fff',
    padding: '14px',
    borderRadius: '6px',
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

function IssueList({ title, issues, style, renderItem }) {
  if (!issues || issues.length === 0) return null;

  return (
    <div style={styles.section}>
      <h3 style={styles.sectionTitle}>{title} ({issues.length})</h3>
      {issues.map((issue, idx) => (
        <div key={idx} style={{ ...styles.issueCard, ...style }}>
          {renderItem(issue)}
        </div>
      ))}
    </div>
  );
}

function UMLClassDiagram({ umlStructure }) {
  if (!umlStructure?.classes || umlStructure.classes.length === 0) return null;

  return (
    <div style={styles.section}>
      <h3 style={styles.sectionTitle}>UML Class Diagram</h3>
      <div style={styles.umlGrid}>
        {umlStructure.classes.map((cls, idx) => (
          <div key={idx} style={styles.umlClass}>
            <div style={styles.umlClassName}>{cls.name}</div>
            <div style={styles.umlAttributes}>
              {cls.attributes?.length > 0 ? (
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

      {umlStructure.associations?.length > 0 && (
        <div style={{ marginTop: '20px' }}>
          <strong>Relationships:</strong>
          <div style={{ marginTop: '10px' }}>
            {umlStructure.associations.map((assoc, idx) => (
              <div key={idx} style={{ padding: '8px 0', borderBottom: '1px solid #eee' }}>
                <strong>{assoc.source}</strong> {assoc.source_multiplicity}{' '}
                <span style={{ color: '#666' }}>--[{assoc.association_type}]--</span>{' '}
                {assoc.target_multiplicity} <strong>{assoc.target}</strong>
                {assoc.label && <span style={{ color: '#666', marginLeft: '8px' }}>({assoc.label})</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      <details style={{ marginTop: '20px' }}>
        <summary style={{ cursor: 'pointer', fontWeight: '500' }}>View Full UML Structure (JSON)</summary>
        <pre style={styles.jsonPreview}>{JSON.stringify(umlStructure, null, 2)}</pre>
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

  return (
    <div style={styles.section}>
      <h3 style={styles.sectionTitle}>User Story Coverage</h3>
      {coverage.map((item, idx) => (
        <div key={idx} style={{ ...styles.coverageItem, ...getCoverageStyle(item.coverage_status) }}>
          <div style={{ marginBottom: '4px' }}>
            <strong>{item.story_summary}</strong>
            <span style={{ ...styles.coverageStatus, ...getCoverageStatusStyle(item.coverage_status) }}>
              {item.coverage_status.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
            </span>
          </div>
          {item.notes && <div style={styles.issueReason}>{item.notes}</div>}
        </div>
      ))}
    </div>
  );
}

export default function ERDReportView({ analysisId, onBack, chatModel, chatApiKey }) {
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAnalysis();
  }, [analysisId]);

  const fetchAnalysis = async () => {
    setLoading(true);
    try {
      const data = await getERDAnalysis(analysisId);
      setAnalysis(data);

      if (data.status === 'pending' || data.status === 'processing') {
        pollAnalysis('erd', analysisId, (updated) => {
          setAnalysis(updated);
          if (updated.status === 'completed' || updated.status === 'failed') {
            setLoading(false);
          }
        });
      } else {
        setLoading(false);
      }
    } catch (err) {
      console.error('Error fetching analysis:', err);
      setLoading(false);
    }
  };

  if (loading || !analysis || analysis.status === 'pending' || analysis.status === 'processing') {
    return (
      <div style={styles.container}>
        <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
        <div style={styles.loading}>
          <div style={styles.spinner}></div>
          <h3>Analyzing ERD Diagrams...</h3>
          <p style={{ marginTop: '10px', color: '#888' }}>
            Extracting UML structure and comparing against user stories
          </p>
        </div>
      </div>
    );
  }

  if (analysis.status === 'failed') {
    return (
      <div style={styles.container}>
        <div style={styles.header}>
          <h2 style={styles.title}>ERD Analysis Failed</h2>
          <button style={styles.backButton} onClick={onBack}>Back</button>
        </div>
        <div style={styles.error}>
          <p>{analysis.error_message || 'An unknown error occurred'}</p>
        </div>
      </div>
    );
  }

  const { uml_structure, report } = analysis;

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h2 style={styles.title}>ERD Analysis Report</h2>
        <button style={styles.backButton} onClick={onBack}>Back to Repository</button>
      </div>

      {report && (
        <div style={styles.scoreContainer}>
          <div style={{ ...styles.scoreValue, color: getScoreColor(report.coverage_score) }}>
            {report.coverage_score}%
          </div>
          <div style={styles.scoreLabel}>Coverage Score</div>
        </div>
      )}

      {report?.summary && (
        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>Summary</h3>
          <p style={styles.summary}>{report.summary}</p>
        </div>
      )}

      <UserStoryCoverage coverage={report?.user_story_coverage} />

      <IssueList
        title="Missing Entities"
        issues={report?.missing_entities}
        style={styles.issueMissing}
        renderItem={(issue) => (
          <>
            <div style={styles.issueName}>{issue.entity_name}</div>
            <div style={styles.issueReason}>{issue.reason}</div>
            {issue.suggested_attributes && (
              <div style={{ marginTop: '8px', fontSize: '12px' }}>
                <strong>Suggested attributes:</strong> {issue.suggested_attributes.join(', ')}
              </div>
            )}
          </>
        )}
      />

      <IssueList
        title="Missing Relationships"
        issues={report?.missing_relationships}
        style={styles.issueRelationship}
        renderItem={(issue) => (
          <>
            <div style={styles.issueName}>{issue.from_entity} &rarr; {issue.to_entity}</div>
            <div style={styles.issueReason}>{issue.reason}</div>
          </>
        )}
      />

      <IssueList
        title="Cardinality Issues"
        issues={report?.cardinality_issues}
        style={styles.issueCardinality}
        renderItem={(issue) => (
          <>
            <div style={styles.issueName}>{issue.relationship}</div>
            <div style={styles.issueReason}>
              Current: {issue.current} &rarr; Suggested: {issue.suggested}
            </div>
            <div style={styles.issueReason}>{issue.reason}</div>
          </>
        )}
      />

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

      <IssueList
        title="Data Integrity Concerns"
        issues={report?.data_integrity_concerns}
        style={styles.issueIntegrity}
        renderItem={(issue) => (
          <>
            <div style={styles.issueName}>{issue.concern}</div>
            {issue.affected_entities && (
              <div style={{ fontSize: '12px', marginBottom: '4px' }}>
                Affected: {issue.affected_entities.join(', ')}
              </div>
            )}
            <div style={styles.issueReason}>{issue.recommendation}</div>
          </>
        )}
      />

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

      {report?.recommendations?.length > 0 && (
        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>Recommendations</h3>
          {report.recommendations.map((rec, idx) => (
            <div key={idx} style={styles.recommendation}>{rec}</div>
          ))}
        </div>
      )}

      <UMLClassDiagram umlStructure={uml_structure} />

      <AnalysisChat
        analysisId={analysisId}
        analysisType="erd"
        chatModel={chatModel}
        chatApiKey={chatApiKey}
      />
    </div>
  );
}
