import React, { useState, useEffect } from 'react';
import { getUsabilityAnalysis, pollAnalysis } from '../../api';
import CharacteristicCard from '../integrity/CharacteristicCard';
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
  title: { margin: 0, color: '#1e3a5f', fontSize: '20px' },
  backButton: {
    backgroundColor: '#e0e0e0', color: '#333', border: 'none',
    padding: '8px 16px', borderRadius: '6px', cursor: 'pointer', fontSize: '13px',
  },
  loading: { textAlign: 'center', padding: '60px', color: '#666' },
  spinner: {
    width: '50px', height: '50px', border: '4px solid #e0e0e0',
    borderTop: '4px solid #1e3a5f', borderRadius: '50%',
    animation: 'spin 1s linear infinite', margin: '0 auto 20px',
  },
  error: {
    backgroundColor: '#f8d7da', color: '#721c24', padding: '20px',
    borderRadius: '8px', textAlign: 'center',
  },
  summary: {
    background: 'linear-gradient(135deg, #6a1b9a 0%, #8e24aa 100%)',
    color: '#fff', padding: '28px', borderRadius: '12px', marginBottom: '24px',
  },
  summaryGrid: { display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '28px', alignItems: 'center' },
  overallScore: {
    width: '130px', height: '130px', borderRadius: '50%',
    backgroundColor: 'rgba(255,255,255,0.15)', display: 'flex',
    flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
  },
  scoreValue: { fontSize: '42px', fontWeight: '700' },
  scoreLabel: { fontSize: '12px', opacity: 0.8 },
  riskBadge: {
    display: 'inline-block', padding: '6px 16px', borderRadius: '20px',
    fontSize: '13px', fontWeight: '600', marginBottom: '14px',
  },
  riskLow: { backgroundColor: '#4caf50' },
  riskMedium: { backgroundColor: '#ff9800' },
  riskHigh: { backgroundColor: '#f44336' },
  riskCritical: { backgroundColor: '#9c27b0' },
  executiveSummary: { fontSize: '15px', lineHeight: 1.6, marginBottom: '18px' },
  summaryLists: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' },
  summaryList: { backgroundColor: 'rgba(255,255,255,0.1)', borderRadius: '8px', padding: '14px' },
  summaryListTitle: { fontWeight: '600', marginBottom: '10px', fontSize: '13px' },
  summaryListItem: { fontSize: '13px', marginBottom: '5px', paddingLeft: '14px' },
  characteristicsGrid: {
    display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '20px', marginBottom: '24px',
  },
  priorityRecommendations: { backgroundColor: '#f3e5f5', borderRadius: '12px', padding: '24px' },
  priorityTitle: { fontSize: '16px', fontWeight: '600', color: '#6a1b9a', marginBottom: '16px' },
  priorityItem: { display: 'flex', alignItems: 'flex-start', gap: '12px', marginBottom: '12px' },
  priorityNumber: {
    width: '26px', height: '26px', borderRadius: '50%', backgroundColor: '#6a1b9a',
    color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontWeight: '600', fontSize: '13px', flexShrink: 0,
  },
  apiHint: {
    backgroundColor: '#fff3e0', border: '1px solid #ffb74d', borderRadius: '8px',
    padding: '14px 18px', marginBottom: '20px', fontSize: '14px', color: '#e65100',
  },
};

function getRiskStyle(riskLevel) {
  switch (riskLevel) {
    case 'low': return styles.riskLow;
    case 'medium': return styles.riskMedium;
    case 'high': return styles.riskHigh;
    case 'critical': return styles.riskCritical;
    default: return styles.riskMedium;
  }
}

export default function UsabilityReportView({ analysisId, onBack, chatModel, chatApiKey }) {
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAnalysis();
  }, [analysisId]);

  const fetchAnalysis = async () => {
    setLoading(true);
    try {
      const data = await getUsabilityAnalysis(analysisId);
      setAnalysis(data);
      if (data.status === 'pending' || data.status === 'processing') {
        pollAnalysis('usability', analysisId, (updated) => {
          setAnalysis(updated);
          if (updated.status === 'completed' || updated.status === 'failed') setLoading(false);
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
          <h3>Analyzing Usability Characteristics...</h3>
          <p style={{ marginTop: '10px', color: '#888' }}>
            Evaluating learnability, operability, accessibility, and more
          </p>
        </div>
      </div>
    );
  }

  if (analysis.status === 'failed') {
    return (
      <div style={styles.container}>
        <div style={styles.header}>
          <h2 style={styles.title}>Usability Analysis Failed</h2>
          <button style={styles.backButton} onClick={onBack}>Back</button>
        </div>
        <div style={styles.error}>
          <p>{analysis.error_message || 'An unknown error occurred'}</p>
        </div>
      </div>
    );
  }

  const characteristics = [
    { key: 'recognizability', data: analysis.appropriateness_recognizability_report, icon: '&#128065;' },
    { key: 'learnability', data: analysis.learnability_report, icon: '&#128218;' },
    { key: 'operability', data: analysis.operability_report, icon: '&#9881;' },
    { key: 'error_protection', data: analysis.user_error_protection_report, icon: '&#128737;' },
    { key: 'engagement', data: analysis.user_engagement_report, icon: '&#10024;' },
    { key: 'self_descriptiveness', data: analysis.self_descriptiveness_report, icon: '&#128196;' },
    { key: 'inclusivity', data: analysis.inclusivity_report, icon: '&#127758;' },
    { key: 'user_assistance', data: analysis.user_assistance_report, icon: '&#128161;' },
  ];

  const summary = analysis.summary_report || {};
  const allIncomplete = characteristics.every(
    ({ data }) => data?.description === 'Analysis incomplete' || data?.description?.includes('No structured result')
  );
  const summaryEmpty = !summary.executive_summary && !summary.strengths?.length;
  const showApiHint = (allIncomplete || summaryEmpty) && (analysis.overall_score === 50 || !analysis.overall_score);

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h2 style={styles.title}>Usability Analysis Report</h2>
        <button style={styles.backButton} onClick={onBack}>Back to Repository</button>
      </div>

      {showApiHint && (
        <div style={styles.apiHint}>
          <strong>API response incomplete.</strong> Ensure sufficient api tokens are available and the TAMU API key is set.
        </div>
      )}

      <div style={styles.summary}>
        <div style={styles.summaryGrid}>
          <div style={styles.overallScore}>
            <span style={styles.scoreValue}>{Math.round(analysis.overall_score || 0)}</span>
            <span style={styles.scoreLabel}>Overall Score</span>
          </div>
          <div>
            <span style={{ ...styles.riskBadge, ...getRiskStyle(summary.risk_level) }}>
              {(summary.risk_level || 'medium').toUpperCase()} RISK
            </span>
            <p style={styles.executiveSummary}>
              {summary.executive_summary || 'Analysis complete. Review individual characteristics below.'}
            </p>
            <div style={styles.summaryLists}>
              {summary.strengths?.length > 0 && (
                <div style={styles.summaryList}>
                  <div style={styles.summaryListTitle}>Strengths</div>
                  {summary.strengths.map((s, i) => (
                    <div key={i} style={styles.summaryListItem}>&#8226; {s}</div>
                  ))}
                </div>
              )}
              {summary.areas_for_improvement?.length > 0 && (
                <div style={styles.summaryList}>
                  <div style={styles.summaryListTitle}>Areas for Improvement</div>
                  {summary.areas_for_improvement.map((a, i) => (
                    <div key={i} style={styles.summaryListItem}>&#8226; {a}</div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <div style={styles.characteristicsGrid}>
        {characteristics.map(({ key, data, icon }) => (
          data && <CharacteristicCard key={key} data={data} icon={icon} />
        ))}
      </div>

      {summary.priority_recommendations?.length > 0 && (
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

      <AnalysisChat analysisId={analysisId} analysisType="usability" chatModel={chatModel} chatApiKey={chatApiKey} />
    </div>
  );
}
