import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ISO_ANALYSIS_LABELS,
  ISO_ANALYSIS_TYPES,
  listRepositories,
  listIsoAnalysesByType,
  getIsoAnalysisByType,
  sendChatMessage,
} from '../api';
import {
  extractIsoFindings,
  mergeAiMatches,
  summarizeFindings,
} from '../utils/reportComparison';

const CHAT_API_KEY_STORAGE = 'tamu_chat_api_key';
const CHAT_MODEL_STORAGE = 'tamu_chat_model';
const DEFAULT_CHAT_MODEL = 'protected.Claude Opus 4.5';
const AI_CONFIDENCE_THRESHOLD = 0.75;
const AI_MAX_UNMATCHED = Number.POSITIVE_INFINITY;

const styles = {
  page: {
    minHeight: '100vh',
    backgroundColor: '#f5f7fa',
    padding: '24px',
  },
  container: {
    maxWidth: '1200px',
    margin: '0 auto',
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: '12px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
    padding: '20px',
  },
  titleRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: '12px',
    flexWrap: 'wrap',
  },
  title: {
    margin: 0,
    color: '#1e3a5f',
    fontSize: '24px',
  },
  subtitle: {
    color: '#666',
    marginTop: '8px',
    marginBottom: 0,
    fontSize: '14px',
  },
  backButton: {
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    padding: '10px 14px',
    backgroundColor: '#e0e0e0',
    color: '#333',
    fontWeight: 600,
  },
  selectorsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
    gap: '12px',
    marginTop: '14px',
  },
  selectorGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  label: {
    fontSize: '12px',
    color: '#333',
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: '0.3px',
  },
  select: {
    border: '1px solid #d0d7de',
    borderRadius: '8px',
    padding: '10px 12px',
    fontSize: '14px',
    backgroundColor: '#fff',
  },
  actionRow: {
    marginTop: '12px',
    display: 'flex',
    gap: '10px',
    alignItems: 'center',
    flexWrap: 'wrap',
  },
  compareButton: {
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    padding: '10px 14px',
    backgroundColor: '#1e3a5f',
    color: '#fff',
    fontWeight: 600,
  },
  compareButtonDisabled: {
    backgroundColor: '#9aa6b2',
    cursor: 'not-allowed',
  },
  info: {
    marginTop: '6px',
    fontSize: '13px',
    color: '#555',
  },
  error: {
    borderRadius: '8px',
    backgroundColor: '#f8d7da',
    color: '#721c24',
    padding: '10px 12px',
    fontSize: '13px',
  },
  summaryGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
    gap: '12px',
  },
  summaryCard: {
    border: '1px solid #e0e0e0',
    borderRadius: '10px',
    padding: '14px',
    backgroundColor: '#fafbfc',
  },
  summaryTitle: {
    margin: 0,
    color: '#1e3a5f',
    fontSize: '16px',
  },
  summaryLine: {
    marginTop: '8px',
    fontSize: '14px',
    color: '#333',
  },
  bucketGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
    gap: '12px',
  },
  bucketCard: {
    borderRadius: '10px',
    border: '1px solid #e0e0e0',
    padding: '14px',
    backgroundColor: '#fff',
  },
  bucketHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '10px',
  },
  bucketTitle: {
    margin: 0,
    color: '#333',
    fontSize: '15px',
  },
  countBadge: {
    borderRadius: '999px',
    padding: '2px 10px',
    fontSize: '12px',
    fontWeight: 700,
    backgroundColor: '#edf2f7',
  },
  findingList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
    maxHeight: '420px',
    overflowY: 'auto',
  },
  findingItem: {
    border: '1px solid #ececec',
    borderRadius: '8px',
    padding: '10px',
    backgroundColor: '#fafafa',
  },
  findingMeta: {
    fontSize: '12px',
    color: '#666',
    marginBottom: '6px',
  },
  findingText: {
    fontSize: '13px',
    color: '#333',
    lineHeight: 1.5,
    margin: 0,
  },
};

function readFromStorage(key, fallback = '') {
  if (typeof window === 'undefined') return fallback;
  return window.localStorage.getItem(key) || fallback;
}

function formatRunLabel(item) {
  const completed = item?.completed_at ? new Date(item.completed_at).toLocaleString() : 'Unknown date';
  const score = typeof item?.overall_score === 'number' ? ` • Score ${Math.round(item.overall_score)}` : '';
  return `#${item.id} • ${completed}${score}`;
}

function tryParseJsonObject(text) {
  if (!text) return null;
  const fencedMatch = text.match(/```(?:json)?\s*([\s\S]*?)```/i);
  const candidate = fencedMatch ? fencedMatch[1] : text;
  try {
    return JSON.parse(candidate.trim());
  } catch {
    const firstBrace = candidate.indexOf('{');
    const lastBrace = candidate.lastIndexOf('}');
    if (firstBrace === -1 || lastBrace === -1 || lastBrace <= firstBrace) return null;
    try {
      return JSON.parse(candidate.slice(firstBrace, lastBrace + 1));
    } catch {
      return null;
    }
  }
}

function buildAiPrompt(analysisType, baselineUnmatched, currentUnmatched) {
  return [
    'You are matching similar findings across two software analysis runs.',
    `Analysis type: ${analysisType}.`,
    'Task: match baseline findings to current findings when they represent the same underlying issue.',
    'Return strict JSON only with this schema:',
    '{"matches":[{"baseline_index":0,"current_index":0,"confidence":0.0,"reason":"short reason"}]}',
    'Rules:',
    '- One-to-one matching only. Do not reuse indices.',
    '- Use confidence between 0 and 1.',
    '- Match on semantics and context (type, file path, line proximity, explanation).',
    '- If unsure, do not match.',
    '',
    'Baseline unmatched findings JSON:',
    JSON.stringify(baselineUnmatched),
    '',
    'Current unmatched findings JSON:',
    JSON.stringify(currentUnmatched),
  ].join('\n');
}

function sendChatAndCollect(analysisType, analysisId, message, model, apiKey) {
  return new Promise((resolve, reject) => {
    let content = '';
    sendChatMessage(
      analysisType,
      analysisId,
      message,
      [],
      model,
      apiKey,
      (chunk) => {
        content += chunk;
      },
      () => resolve(content),
      (error) => reject(error || new Error('AI matching failed'))
    ).catch((err) => reject(err));
  });
}

export default function ComparisonPage() {
  const navigate = useNavigate();
  const [repositories, setRepositories] = useState([]);
  const [repoLoading, setRepoLoading] = useState(true);
  const [error, setError] = useState('');

  const [baselineRepoId, setBaselineRepoId] = useState('');
  const [currentRepoId, setCurrentRepoId] = useState('');
  const [analysisType, setAnalysisType] = useState('integrity');
  const [baselineRuns, setBaselineRuns] = useState([]);
  const [currentRuns, setCurrentRuns] = useState([]);
  const [baselineRunsLoading, setBaselineRunsLoading] = useState(false);
  const [currentRunsLoading, setCurrentRunsLoading] = useState(false);
  const [baselineId, setBaselineId] = useState('');
  const [currentId, setCurrentId] = useState('');

  const [comparing, setComparing] = useState(false);
  const [result, setResult] = useState(null);
  const [lastInfo, setLastInfo] = useState('');

  const chatApiKey = readFromStorage(CHAT_API_KEY_STORAGE, '');
  const chatModel = readFromStorage(CHAT_MODEL_STORAGE, DEFAULT_CHAT_MODEL);

  useEffect(() => {
    const load = async () => {
      setRepoLoading(true);
      setError('');
      try {
        const repos = await listRepositories();
        setRepositories(Array.isArray(repos) ? repos : []);
      } catch (err) {
        setError('Failed to load repositories.');
      } finally {
        setRepoLoading(false);
      }
    };
    load();
  }, []);

  useEffect(() => {
    const loadBaselineRuns = async () => {
      if (!baselineRepoId) {
        setBaselineRuns([]);
        setBaselineId('');
        return;
      }
      setBaselineRunsLoading(true);
      setError('');
      setResult(null);
      try {
        const raw = await listIsoAnalysesByType(analysisType, baselineRepoId);
        const completed = (Array.isArray(raw) ? raw : []).filter((item) => item?.status === 'completed');
        setBaselineRuns(completed);
        setBaselineId(completed[0] ? String(completed[0].id) : '');
      } catch (err) {
        setError('Failed to load baseline reports for this type.');
        setBaselineRuns([]);
        setBaselineId('');
      } finally {
        setBaselineRunsLoading(false);
      }
    };
    loadBaselineRuns();
  }, [baselineRepoId, analysisType]);

  useEffect(() => {
    const loadCurrentRuns = async () => {
      if (!currentRepoId) {
        setCurrentRuns([]);
        setCurrentId('');
        return;
      }
      setCurrentRunsLoading(true);
      setError('');
      setResult(null);
      try {
        const raw = await listIsoAnalysesByType(analysisType, currentRepoId);
        const completed = (Array.isArray(raw) ? raw : []).filter((item) => item?.status === 'completed');
        setCurrentRuns(completed);
        setCurrentId(completed[0] ? String(completed[0].id) : '');
      } catch (err) {
        setError('Failed to load current reports for this type.');
        setCurrentRuns([]);
        setCurrentId('');
      } finally {
        setCurrentRunsLoading(false);
      }
    };
    loadCurrentRuns();
  }, [currentRepoId, analysisType]);

  useEffect(() => {
    if (!baselineRepoId || !currentRepoId) return;
    if (baselineRepoId !== currentRepoId) return;
    if (!baselineId || !currentId) return;
    if (baselineId !== currentId) return;
    const alternateCurrent = currentRuns.find((run) => String(run.id) !== baselineId);
    if (alternateCurrent) {
      setCurrentId(String(alternateCurrent.id));
    }
  }, [baselineRepoId, currentRepoId, baselineId, currentId, currentRuns]);

  const canCompare = useMemo(() => {
    const sameRepo = baselineRepoId && currentRepoId && baselineRepoId === currentRepoId;
    const sameRunSelection = baselineId && currentId && baselineId === currentId;
    if (sameRepo && sameRunSelection) return false;
    return Boolean(baselineRepoId && currentRepoId && baselineId && currentId && !comparing);
  }, [baselineRepoId, currentRepoId, baselineId, currentId, comparing]);

  const handleCompare = async () => {
    if (!canCompare) return;
    setComparing(true);
    setError('');
    setResult(null);
    setLastInfo('');

    try {
      const [baselineAnalysis, currentAnalysis] = await Promise.all([
        getIsoAnalysisByType(analysisType, baselineId),
        getIsoAnalysisByType(analysisType, currentId),
      ]);

      const baselineFindings = extractIsoFindings(baselineAnalysis, analysisType);
      const currentFindings = extractIsoFindings(currentAnalysis, analysisType);
      const aiInput = {
        unchanged: [],
        unmatchedBaseline: baselineFindings
          .slice(0, AI_MAX_UNMATCHED)
          .map((finding, index) => ({ finding, index })),
        unmatchedCurrent: currentFindings
          .slice(0, AI_MAX_UNMATCHED)
          .map((finding, index) => ({ finding, index })),
      };
      const limitedBaseline = aiInput.unmatchedBaseline.map((entry) => entry.finding);
      const limitedCurrent = aiInput.unmatchedCurrent.map((entry) => entry.finding);

      let aiMatches = [];
      let aiInfo = 'AI-only comparison did not run because one side has no findings.';

      if (limitedBaseline.length > 0 && limitedCurrent.length > 0) {
        const prompt = buildAiPrompt(analysisType, limitedBaseline, limitedCurrent);
        try {
          const responseText = await sendChatAndCollect(
            analysisType,
            currentId,
            prompt,
            chatModel,
            chatApiKey
          );
          const parsed = tryParseJsonObject(responseText);
          const rawMatches = Array.isArray(parsed?.matches) ? parsed.matches : [];
          aiMatches = rawMatches.filter((match) => (
            Number.isInteger(Number(match?.baseline_index)) &&
            Number.isInteger(Number(match?.current_index)) &&
            Number(match.baseline_index) >= 0 &&
            Number(match.current_index) >= 0 &&
            Number(match.baseline_index) < limitedBaseline.length &&
            Number(match.current_index) < limitedCurrent.length
          ));
          aiInfo = `AI-only processed ${limitedBaseline.length} baseline x ${limitedCurrent.length} current findings.`;
        } catch {
          aiMatches = [];
          aiInfo = 'AI-only comparison unavailable; no semantic matches were applied.';
        }
      }

      const merged = mergeAiMatches(
        aiInput,
        aiMatches,
        AI_CONFIDENCE_THRESHOLD
      );

      const baselineSummary = summarizeFindings(baselineFindings);
      const currentSummary = summarizeFindings(currentFindings);

      setResult({
        baselineSummary,
        currentSummary,
        unchanged: merged.unchanged,
        resolved: merged.resolved,
        newFindings: merged.newFindings,
        aiMatchedCount: merged.aiMatchedCount,
      });
      setLastInfo(aiInfo);
    } catch (err) {
      setError('Failed to compare selected reports.');
    } finally {
      setComparing(false);
    }
  };

  return (
    <div style={styles.page}>
      <div style={styles.container}>
        <div style={styles.card}>
          <div style={styles.titleRow}>
            <div>
              <h1 style={styles.title}>Report Comparison</h1>
              <p style={styles.subtitle}>
                Select baseline and current repositories, then compare completed ISO reports side-by-side.
              </p>
            </div>
            <button style={styles.backButton} onClick={() => navigate('/analyzer')}>
              Back to Analyzer
            </button>
          </div>

          <div style={styles.selectorsGrid}>
            <div style={styles.selectorGroup}>
              <label style={styles.label}>Baseline Repository</label>
              <select
                style={styles.select}
                value={baselineRepoId}
                onChange={(e) => setBaselineRepoId(e.target.value)}
                disabled={repoLoading}
              >
                <option value="">{repoLoading ? 'Loading repositories...' : 'Select baseline repository'}</option>
                {repositories.map((repo) => (
                  <option key={repo.id} value={repo.id}>{repo.name}</option>
                ))}
              </select>
            </div>

            <div style={styles.selectorGroup}>
              <label style={styles.label}>Current Repository</label>
              <select
                style={styles.select}
                value={currentRepoId}
                onChange={(e) => setCurrentRepoId(e.target.value)}
                disabled={repoLoading}
              >
                <option value="">{repoLoading ? 'Loading repositories...' : 'Select current repository'}</option>
                {repositories.map((repo) => (
                  <option key={repo.id} value={repo.id}>{repo.name}</option>
                ))}
              </select>
            </div>

            <div style={styles.selectorGroup}>
              <label style={styles.label}>Analysis Type</label>
              <select
                style={styles.select}
                value={analysisType}
                onChange={(e) => setAnalysisType(e.target.value)}
              >
                {ISO_ANALYSIS_TYPES.map((type) => (
                  <option key={type} value={type}>{ISO_ANALYSIS_LABELS[type]}</option>
                ))}
              </select>
            </div>

            <div style={styles.selectorGroup}>
              <label style={styles.label}>Baseline Report</label>
              <select
                style={styles.select}
                value={baselineId}
                onChange={(e) => setBaselineId(e.target.value)}
                disabled={baselineRunsLoading || baselineRuns.length === 0}
              >
                <option value="">
                  {baselineRunsLoading ? 'Loading reports...' : 'Select baseline report'}
                </option>
                {baselineRuns.map((run) => (
                  <option key={run.id} value={run.id}>{formatRunLabel(run)}</option>
                ))}
              </select>
            </div>

            <div style={styles.selectorGroup}>
              <label style={styles.label}>Current Report</label>
              <select
                style={styles.select}
                value={currentId}
                onChange={(e) => setCurrentId(e.target.value)}
                disabled={currentRunsLoading || currentRuns.length === 0}
              >
                <option value="">
                  {currentRunsLoading ? 'Loading reports...' : 'Select current report'}
                </option>
                {currentRuns.map((run) => (
                  <option key={run.id} value={run.id}>{formatRunLabel(run)}</option>
                ))}
              </select>
            </div>
          </div>

          <div style={styles.actionRow}>
            <button
              style={{
                ...styles.compareButton,
                ...(!canCompare ? styles.compareButtonDisabled : {}),
              }}
              onClick={handleCompare}
              disabled={!canCompare}
            >
              {comparing ? 'Comparing...' : 'Compare Reports'}
            </button>
            <span style={styles.info}>
              Uses AI-only semantic matching for all findings (test mode).
            </span>
          </div>

          {baselineRepoId && baselineRuns.length === 0 && !baselineRunsLoading && (
            <p style={styles.info}>Baseline repository has no completed reports for this type.</p>
          )}
          {currentRepoId && currentRuns.length === 0 && !currentRunsLoading && (
            <p style={styles.info}>Current repository has no completed reports for this type.</p>
          )}
          {baselineRepoId && currentRepoId && baselineRepoId === currentRepoId && baselineId && currentId && baselineId === currentId && (
            <p style={styles.info}>When comparing within the same repository, choose two different reports.</p>
          )}
          {lastInfo && <p style={styles.info}>{lastInfo}</p>}
          {error && <div style={styles.error}>{error}</div>}
        </div>

        {result && (
          <>
            <div style={styles.card}>
              <h2 style={{ marginTop: 0, color: '#1e3a5f' }}>Summary Counts</h2>
              <div style={styles.summaryGrid}>
                <div style={styles.summaryCard}>
                  <h3 style={styles.summaryTitle}>Baseline</h3>
                  <div style={styles.summaryLine}>Total: {result.baselineSummary.total}</div>
                  <div style={styles.summaryLine}>Negative: {result.baselineSummary.byType.negative}</div>
                  <div style={styles.summaryLine}>Warning: {result.baselineSummary.byType.warning}</div>
                  <div style={styles.summaryLine}>Positive: {result.baselineSummary.byType.positive}</div>
                </div>
                <div style={styles.summaryCard}>
                  <h3 style={styles.summaryTitle}>Current</h3>
                  <div style={styles.summaryLine}>Total: {result.currentSummary.total}</div>
                  <div style={styles.summaryLine}>Negative: {result.currentSummary.byType.negative}</div>
                  <div style={styles.summaryLine}>Warning: {result.currentSummary.byType.warning}</div>
                  <div style={styles.summaryLine}>Positive: {result.currentSummary.byType.positive}</div>
                </div>
              </div>
              <p style={styles.info}>
                New: {result.newFindings.length} • Resolved: {result.resolved.length} • Unchanged: {result.unchanged.length}
                {' '}• AI matched: {result.aiMatchedCount}
              </p>
            </div>

            <div style={styles.card}>
              <h2 style={{ marginTop: 0, color: '#1e3a5f' }}>Finding Changes</h2>
              <div style={styles.bucketGrid}>
                <div style={styles.bucketCard}>
                  <div style={styles.bucketHeader}>
                    <h3 style={styles.bucketTitle}>New</h3>
                    <span style={styles.countBadge}>{result.newFindings.length}</span>
                  </div>
                  <div style={styles.findingList}>
                    {result.newFindings.map((finding, idx) => (
                      <div key={`new-${idx}`} style={styles.findingItem}>
                        <div style={styles.findingMeta}>
                          {finding.characteristic} • {finding.type} • {finding.file_path || 'no file'}
                        </div>
                        <p style={styles.findingText}>{finding.explanation || 'No explanation provided.'}</p>
                      </div>
                    ))}
                  </div>
                </div>

                <div style={styles.bucketCard}>
                  <div style={styles.bucketHeader}>
                    <h3 style={styles.bucketTitle}>Resolved</h3>
                    <span style={styles.countBadge}>{result.resolved.length}</span>
                  </div>
                  <div style={styles.findingList}>
                    {result.resolved.map((finding, idx) => (
                      <div key={`resolved-${idx}`} style={styles.findingItem}>
                        <div style={styles.findingMeta}>
                          {finding.characteristic} • {finding.type} • {finding.file_path || 'no file'}
                        </div>
                        <p style={styles.findingText}>{finding.explanation || 'No explanation provided.'}</p>
                      </div>
                    ))}
                  </div>
                </div>

                <div style={styles.bucketCard}>
                  <div style={styles.bucketHeader}>
                    <h3 style={styles.bucketTitle}>Unchanged</h3>
                    <span style={styles.countBadge}>{result.unchanged.length}</span>
                  </div>
                  <div style={styles.findingList}>
                    {result.unchanged.map((pair, idx) => (
                      <div key={`unchanged-${idx}`} style={styles.findingItem}>
                        <div style={styles.findingMeta}>
                          {pair.current.characteristic} • {pair.current.type} • {pair.current.file_path || 'no file'}
                          {pair.match_source === 'ai' ? ` • AI ${Math.round((pair.confidence || 0) * 100)}%` : ''}
                        </div>
                        <p style={styles.findingText}>{pair.current.explanation || 'No explanation provided.'}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
