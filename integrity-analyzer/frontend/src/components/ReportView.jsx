import React, { useState, useEffect } from 'react';
import { getAnalysis, pollAnalysis } from '../api';

const styles = {
  container: {
    padding: '10px',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '25px',
  },
  backButton: {
    padding: '10px 20px',
    background: '#e0e0e0',
    color: '#333',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '0.95rem',
    fontWeight: '500',
  },
  title: {
    fontSize: '1.5rem',
    fontWeight: '600',
    color: '#1e3a5f',
  },
  loading: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '80px 40px',
    color: '#666',
  },
  spinner: {
    width: '50px',
    height: '50px',
    border: '4px solid #e0e0e0',
    borderTop: '4px solid #1e3a5f',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
    marginBottom: '20px',
  },
  error: {
    background: '#ffebee',
    color: '#c62828',
    padding: '20px',
    borderRadius: '8px',
    marginBottom: '20px',
  },
  summary: {
    background: 'linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%)',
    color: 'white',
    padding: '30px',
    borderRadius: '12px',
    marginBottom: '30px',
  },
  summaryGrid: {
    display: 'grid',
    gridTemplateColumns: 'auto 1fr',
    gap: '30px',
    alignItems: 'center',
  },
  overallScore: {
    width: '140px',
    height: '140px',
    borderRadius: '50%',
    background: 'rgba(255,255,255,0.15)',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
  },
  scoreValue: {
    fontSize: '3rem',
    fontWeight: '700',
  },
  scoreLabel: {
    fontSize: '0.9rem',
    opacity: '0.8',
  },
  summaryContent: {},
  riskBadge: {
    display: 'inline-block',
    padding: '6px 16px',
    borderRadius: '20px',
    fontSize: '0.9rem',
    fontWeight: '600',
    marginBottom: '15px',
  },
  riskLow: {
    background: '#4caf50',
  },
  riskMedium: {
    background: '#ff9800',
  },
  riskHigh: {
    background: '#f44336',
  },
  riskCritical: {
    background: '#9c27b0',
  },
  executiveSummary: {
    fontSize: '1.1rem',
    lineHeight: '1.6',
    marginBottom: '20px',
  },
  summaryLists: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '20px',
  },
  summaryList: {
    background: 'rgba(255,255,255,0.1)',
    borderRadius: '8px',
    padding: '15px',
  },
  summaryListTitle: {
    fontWeight: '600',
    marginBottom: '10px',
    fontSize: '0.95rem',
  },
  summaryListItem: {
    fontSize: '0.9rem',
    marginBottom: '5px',
    paddingLeft: '15px',
    position: 'relative',
  },
  characteristicsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '20px',
    marginBottom: '30px',
  },
  characteristicCard: {
    background: 'white',
    border: '1px solid #e0e0e0',
    borderRadius: '12px',
    overflow: 'hidden',
  },
  cardHeader: {
    padding: '20px',
    borderBottom: '1px solid #e0e0e0',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  cardTitle: {
    fontSize: '1.1rem',
    fontWeight: '600',
    color: '#1e3a5f',
  },
  cardScore: {
    fontSize: '1.5rem',
    fontWeight: '700',
  },
  statusBadge: {
    padding: '4px 12px',
    borderRadius: '12px',
    fontSize: '0.8rem',
    fontWeight: '500',
  },
  statusFulfilled: {
    background: '#e8f5e9',
    color: '#2e7d32',
  },
  statusPartial: {
    background: '#fff3e0',
    color: '#ef6c00',
  },
  statusNotFulfilled: {
    background: '#ffebee',
    color: '#c62828',
  },
  statusNA: {
    background: '#f5f5f5',
    color: '#666',
  },
  cardBody: {
    padding: '20px',
  },
  description: {
    color: '#666',
    marginBottom: '15px',
    lineHeight: '1.5',
  },
  findingsSection: {
    marginTop: '15px',
  },
  findingsTitle: {
    fontSize: '0.9rem',
    fontWeight: '600',
    marginBottom: '10px',
    color: '#333',
  },
  finding: {
    background: '#f9f9f9',
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
    fontSize: '0.85rem',
    color: '#1565c0',
  },
  findingType: {
    fontSize: '0.75rem',
    fontWeight: '500',
    padding: '2px 8px',
    borderRadius: '10px',
  },
  codeSnippet: {
    background: '#263238',
    color: '#aed581',
    padding: '10px',
    borderRadius: '6px',
    fontFamily: 'monospace',
    fontSize: '0.85rem',
    overflowX: 'auto',
    marginBottom: '8px',
    whiteSpace: 'pre-wrap',
  },
  findingExplanation: {
    fontSize: '0.9rem',
    color: '#555',
    lineHeight: '1.4',
  },
  recommendations: {
    marginTop: '15px',
    padding: '15px',
    background: '#e3f2fd',
    borderRadius: '8px',
  },
  recommendationsTitle: {
    fontSize: '0.9rem',
    fontWeight: '600',
    marginBottom: '10px',
    color: '#1565c0',
  },
  recommendation: {
    fontSize: '0.9rem',
    marginBottom: '5px',
    paddingLeft: '15px',
    position: 'relative',
  },
  expandButton: {
    background: 'none',
    border: 'none',
    color: '#1565c0',
    cursor: 'pointer',
    fontSize: '0.9rem',
    padding: '5px 0',
  },
  priorityRecommendations: {
    background: '#fff3e0',
    borderRadius: '12px',
    padding: '25px',
    marginTop: '20px',
  },
  priorityTitle: {
    fontSize: '1.2rem',
    fontWeight: '600',
    color: '#ef6c00',
    marginBottom: '15px',
  },
  priorityItem: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '12px',
    marginBottom: '12px',
  },
  priorityNumber: {
    width: '28px',
    height: '28px',
    borderRadius: '50%',
    background: '#ef6c00',
    color: 'white',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontWeight: '600',
    fontSize: '0.9rem',
    flexShrink: 0,
  },
};

function ReportView({ analysisId, onBack }) {
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expandedCards, setExpandedCards] = useState({});

  useEffect(() => {
    fetchAnalysis();
  }, [analysisId]);

  const fetchAnalysis = async () => {
    setLoading(true);
    try {
      const response = await getAnalysis(analysisId);
      setAnalysis(response.data);

      if (response.data.status === 'pending' || response.data.status === 'processing') {
        pollAnalysis(analysisId, (data) => {
          setAnalysis(data);
          if (data.status === 'completed' || data.status === 'failed') {
            setLoading(false);
          }
        });
      } else {
        setLoading(false);
      }
    } catch (error) {
      console.error('Error fetching analysis:', error);
      setLoading(false);
    }
  };

  const toggleCard = (cardId) => {
    setExpandedCards((prev) => ({
      ...prev,
      [cardId]: !prev[cardId],
    }));
  };

  const getScoreColor = (score) => {
    if (score >= 80) return '#4caf50';
    if (score >= 60) return '#ff9800';
    if (score >= 40) return '#f57c00';
    return '#f44336';
  };

  const getStatusStyle = (status) => {
    switch (status) {
      case 'fulfilled':
        return styles.statusFulfilled;
      case 'partially_fulfilled':
        return styles.statusPartial;
      case 'not_fulfilled':
        return styles.statusNotFulfilled;
      default:
        return styles.statusNA;
    }
  };

  const getRiskStyle = (riskLevel) => {
    switch (riskLevel) {
      case 'low':
        return styles.riskLow;
      case 'medium':
        return styles.riskMedium;
      case 'high':
        return styles.riskHigh;
      case 'critical':
        return styles.riskCritical;
      default:
        return styles.riskMedium;
    }
  };

  const getFindingStyle = (type) => {
    switch (type) {
      case 'positive':
        return styles.findingPositive;
      case 'negative':
        return styles.findingNegative;
      default:
        return styles.findingWarning;
    }
  };

  const formatStatus = (status) => {
    return status?.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()) || 'Unknown';
  };

  if (loading || !analysis || analysis.status === 'pending' || analysis.status === 'processing') {
    return (
      <div style={styles.loading}>
        <style>
          {`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}
        </style>
        <div style={styles.spinner}></div>
        <h3>Analyzing Integrity Characteristics...</h3>
        <p style={{ marginTop: '10px', color: '#999' }}>
          This may take a few moments as we analyze your codebase
        </p>
      </div>
    );
  }

  if (analysis.status === 'failed') {
    return (
      <div style={styles.container}>
        <button style={styles.backButton} onClick={onBack}>
          ← Back
        </button>
        <div style={styles.error}>
          <h3>Analysis Failed</h3>
          <p>{analysis.error_message || 'An unknown error occurred'}</p>
        </div>
      </div>
    );
  }

  const characteristics = [
    { key: 'confidentiality', data: analysis.confidentiality_report, icon: '🔒' },
    { key: 'data_integrity', data: analysis.data_integrity_report, icon: '✓' },
    { key: 'authenticity', data: analysis.authenticity_report, icon: '🔑' },
    { key: 'non_repudiation', data: analysis.non_repudiation_report, icon: '📝' },
    { key: 'accountability', data: analysis.accountability_report, icon: '👤' },
    { key: 'resistance', data: analysis.resistance_report, icon: '🛡️' },
  ];

  const summary = analysis.summary_report || {};

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <button style={styles.backButton} onClick={onBack}>
          ← Back to Repository
        </button>
        <span style={{ color: '#666' }}>
          Analysis completed {new Date(analysis.completed_at).toLocaleString()}
        </span>
      </div>

      {/* Summary Section */}
      <div style={styles.summary}>
        <div style={styles.summaryGrid}>
          <div style={styles.overallScore}>
            <span style={styles.scoreValue}>{Math.round(analysis.overall_score || 0)}</span>
            <span style={styles.scoreLabel}>Overall Score</span>
          </div>
          <div style={styles.summaryContent}>
            <span style={{ ...styles.riskBadge, ...getRiskStyle(summary.risk_level) }}>
              {(summary.risk_level || 'medium').toUpperCase()} RISK
            </span>
            <p style={styles.executiveSummary}>
              {summary.executive_summary || 'Analysis complete. Review individual characteristics below.'}
            </p>
            <div style={styles.summaryLists}>
              {summary.strengths && summary.strengths.length > 0 && (
                <div style={styles.summaryList}>
                  <div style={styles.summaryListTitle}>✓ Strengths</div>
                  {summary.strengths.map((s, i) => (
                    <div key={i} style={styles.summaryListItem}>
                      • {s}
                    </div>
                  ))}
                </div>
              )}
              {summary.areas_for_improvement && summary.areas_for_improvement.length > 0 && (
                <div style={styles.summaryList}>
                  <div style={styles.summaryListTitle}>⚠ Areas for Improvement</div>
                  {summary.areas_for_improvement.map((a, i) => (
                    <div key={i} style={styles.summaryListItem}>
                      • {a}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Characteristics Grid */}
      <div style={styles.characteristicsGrid}>
        {characteristics.map(({ key, data, icon }) => {
          if (!data) return null;
          const isExpanded = expandedCards[key];
          const visibleFindings = isExpanded ? data.findings : data.findings?.slice(0, 2);

          return (
            <div key={key} style={styles.characteristicCard}>
              <div style={styles.cardHeader}>
                <div>
                  <span style={{ marginRight: '8px' }}>{icon}</span>
                  <span style={styles.cardTitle}>{data.characteristic}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
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

                {data.findings && data.findings.length > 0 && (
                  <div style={styles.findingsSection}>
                    <div style={styles.findingsTitle}>
                      Findings ({data.findings.length})
                    </div>
                    {visibleFindings.map((finding, i) => (
                      <div key={i} style={{ ...styles.finding, ...getFindingStyle(finding.type) }}>
                        <div style={styles.findingHeader}>
                          <span style={styles.findingFile}>
                            {finding.file_path}
                            {finding.line_number && `:${finding.line_number}`}
                          </span>
                          <span
                            style={{
                              ...styles.findingType,
                              background:
                                finding.type === 'positive'
                                  ? '#e8f5e9'
                                  : finding.type === 'negative'
                                  ? '#ffebee'
                                  : '#fff3e0',
                              color:
                                finding.type === 'positive'
                                  ? '#2e7d32'
                                  : finding.type === 'negative'
                                  ? '#c62828'
                                  : '#ef6c00',
                            }}
                          >
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
                      <button style={styles.expandButton} onClick={() => toggleCard(key)}>
                        {isExpanded
                          ? '▲ Show less'
                          : `▼ Show ${data.findings.length - 2} more findings`}
                      </button>
                    )}
                  </div>
                )}

                {data.recommendations && data.recommendations.length > 0 && (
                  <div style={styles.recommendations}>
                    <div style={styles.recommendationsTitle}>Recommendations</div>
                    {data.recommendations.map((rec, i) => (
                      <div key={i} style={styles.recommendation}>
                        • {rec}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Priority Recommendations */}
      {summary.priority_recommendations && summary.priority_recommendations.length > 0 && (
        <div style={styles.priorityRecommendations}>
          <div style={styles.priorityTitle}>Priority Actions</div>
          {summary.priority_recommendations.map((rec, i) => (
            <div key={i} style={styles.priorityItem}>
              <span style={styles.priorityNumber}>{i + 1}</span>
              <span>{rec}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default ReportView;
