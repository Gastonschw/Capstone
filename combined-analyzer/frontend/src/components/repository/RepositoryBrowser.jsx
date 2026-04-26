import React, { useState, useEffect, useCallback } from 'react';
import {
  getRepository,
  updateFileSelection,
  updateFileType,
  rediscoverFiles,
  deleteRepository,
  startERDAnalysis,
  startIntegrityAnalysis,
  startComplianceAnalysis,
  startCorrectnessAnalysis,
  startUsabilityAnalysis,
  startMaintainabilityAnalysis,
  pollAnalysis,
  listERDAnalyses,
  listIntegrityAnalyses,
  listComplianceAnalyses,
  listCorrectnessAnalyses,
  listUsabilityAnalyses,
  listMaintainabilityAnalyses,
  getERDAnalysis,
  getIntegrityAnalysis,
  getComplianceAnalysis,
  getCorrectnessAnalysis,
  getUsabilityAnalysis,
  getMaintainabilityAnalysis,
} from '../../api';
import AnalysisTypeSelector from './AnalysisTypeSelector';
import FileList from './FileList';

const styles = {
  container: {
    maxWidth: '900px',
  },
  latestSection: {
    backgroundColor: '#fff',
    borderRadius: '12px',
    padding: '20px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
    marginBottom: '20px',
  },
  latestHeaderRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '12px',
    flexWrap: 'wrap',
    marginBottom: '12px',
  },
  latestTitle: {
    margin: 0,
    fontSize: '16px',
    fontWeight: '600',
    color: '#333',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  latestGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
    gap: '12px',
  },
  latestCard: {
    border: '1px solid #e0e0e0',
    borderRadius: '12px',
    padding: '14px',
    backgroundColor: '#fafbfc',
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
    minHeight: '140px',
  },
  latestCardTop: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: '12px',
  },
  latestCardTitle: {
    margin: 0,
    fontSize: '14px',
    fontWeight: '600',
    color: '#1e3a5f',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  latestBadge: {
    fontSize: '11px',
    padding: '4px 10px',
    borderRadius: '999px',
    fontWeight: '600',
    whiteSpace: 'nowrap',
  },
  badgeCompleted: { backgroundColor: '#e8f5e9', color: '#2e7d32' },
  badgeProcessing: { backgroundColor: '#fff3cd', color: '#856404' },
  badgeFailed: { backgroundColor: '#f8d7da', color: '#721c24' },
  badgeNone: { backgroundColor: '#e9ecef', color: '#495057' },
  latestMetricsRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '12px',
  },
  latestScore: {
    fontSize: '28px',
    fontWeight: '700',
    color: '#333',
    lineHeight: 1,
  },
  latestScoreLabel: {
    fontSize: '12px',
    color: '#666',
    marginTop: '4px',
  },
  latestMeta: {
    fontSize: '12px',
    color: '#666',
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    textAlign: 'right',
  },
  latestActions: {
    display: 'flex',
    gap: '8px',
    flexWrap: 'wrap',
  },
  smallButton: {
    padding: '8px 12px',
    borderRadius: '8px',
    border: '1px solid #d0d7de',
    cursor: 'pointer',
    fontSize: '12px',
    fontWeight: '600',
    backgroundColor: '#fff',
    color: '#1e3a5f',
  },
  primarySmallButton: {
    backgroundColor: '#1e3a5f',
    color: '#fff',
    border: '1px solid #1e3a5f',
  },
  latestError: {
    marginTop: '10px',
    fontSize: '13px',
    color: '#721c24',
    backgroundColor: '#f8d7da',
    borderRadius: '8px',
    padding: '10px 12px',
  },
  expanderButton: {
    padding: '10px 14px',
    borderRadius: '10px',
    border: '1px solid #d0d7de',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: '600',
    backgroundColor: '#fff',
    color: '#1e3a5f',
  },
  expanderButtonPrimary: {
    backgroundColor: '#1e3a5f',
    border: '1px solid #1e3a5f',
    color: '#fff',
  },
  newRunPanel: {
    backgroundColor: '#fff',
    borderRadius: '12px',
    padding: '20px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
    marginTop: '16px',
  },
  newRunHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '12px',
    marginBottom: '12px',
  },
  newRunTitle: {
    margin: 0,
    fontSize: '16px',
    fontWeight: '600',
    color: '#333',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  header: {
    backgroundColor: '#fff',
    borderRadius: '12px',
    padding: '20px 24px',
    marginBottom: '20px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  repoInfo: {},
  repoName: {
    margin: '0 0 8px 0',
    fontSize: '24px',
    color: '#1e3a5f',
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  sourceBadge: {
    fontSize: '12px',
    padding: '4px 10px',
    borderRadius: '6px',
    fontWeight: '500',
  },
  badgeGithub: {
    backgroundColor: '#24292e',
    color: '#fff',
  },
  badgeFolder: {
    backgroundColor: '#6c757d',
    color: '#fff',
  },
  repoMeta: {
    color: '#666',
    fontSize: '14px',
  },
  headerButtons: {
    display: 'flex',
    gap: '8px',
  },
  button: {
    padding: '8px 16px',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: '500',
  },
  backButton: {
    backgroundColor: '#e0e0e0',
    color: '#333',
  },
  refreshButton: {
    backgroundColor: '#17a2b8',
    color: '#fff',
  },
  deleteButton: {
    backgroundColor: '#dc3545',
    color: '#fff',
  },
  content: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
    gap: '20px',
  },
  section: {
    backgroundColor: '#fff',
    borderRadius: '12px',
    padding: '20px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
  },
  sectionHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '12px',
    marginBottom: '16px',
  },
  sectionTitle: {
    margin: 0,
    fontSize: '16px',
    color: '#333',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  sectionIcon: {
    fontSize: '20px',
  },
  error: {
    backgroundColor: '#f8d7da',
    color: '#721c24',
    padding: '12px',
    borderRadius: '8px',
    marginBottom: '16px',
  },
  manualActions: {
    backgroundColor: '#fff',
    borderRadius: '12px',
    padding: '16px 20px',
    marginBottom: '20px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
    display: 'flex',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: '10px',
  },
  manualLabel: {
    fontSize: '13px',
    color: '#444',
    fontWeight: '500',
    marginRight: '6px',
  },
  actionButton: {
    padding: '7px 12px',
    borderRadius: '6px',
    border: '1px solid #d1d5db',
    backgroundColor: '#f8f9fa',
    color: '#333',
    cursor: 'pointer',
    fontSize: '12px',
    fontWeight: '500',
  },
  actionButtonDanger: {
    backgroundColor: '#fff3f3',
    border: '1px solid #f2b8b8',
    color: '#a12828',
  },
  loading: {
    textAlign: 'center',
    padding: '60px',
    color: '#666',
  },
  spinner: {
    width: '40px',
    height: '40px',
    border: '4px solid #e0e0e0',
    borderTop: '4px solid #1e3a5f',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
    margin: '0 auto 16px',
  },
  analyzeSection: {
    backgroundColor: '#fff',
    borderRadius: '12px',
    padding: '24px',
    marginTop: '20px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
  },
  analyzeButton: {
    backgroundColor: '#1e3a5f',
    color: '#fff',
    border: 'none',
    padding: '14px 24px',
    borderRadius: '8px',
    fontSize: '16px',
    fontWeight: '500',
    cursor: 'pointer',
    width: '100%',
    marginTop: '16px',
  },
  analyzeButtonDisabled: {
    backgroundColor: '#ccc',
    cursor: 'not-allowed',
  },
  hint: {
    fontSize: '13px',
    color: '#666',
    marginTop: '12px',
    lineHeight: 1.5,
  },
};

export default function RepositoryBrowser({ repositoryId, onBack, onAnalysisComplete, tamuApiKey = '', tamuModel = '' }) {
  const [repository, setRepository] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState(null);
  const [latestRuns, setLatestRuns] = useState({
    erd: null,
    integrity: null,
    compliance: null,
    correctness: null,
    usability: null,
    maintainability: null,
  });
  const [latestLoading, setLatestLoading] = useState(false);
  const [latestError, setLatestError] = useState('');
  const [showNewRun, setShowNewRun] = useState(false);
  const [runningTypes, setRunningTypes] = useState({
    erd: false,
    integrity: false,
    compliance: false,
    correctness: false,
    usability: false,
    maintainability: false,
  });
  const [analysisTypes, setAnalysisTypes] = useState({
    erd: false, integrity: false, compliance: false, correctness: false,
    usability: false, maintainability: false,
  });
  const [showOtherFiles, setShowOtherFiles] = useState(false);

  const loadRepository = async () => {
    setLoading(true);
    setError(null);
    try {
      const repo = await getRepository(repositoryId);
      setRepository(repo);
    } catch (err) {
      setError('Failed to load repository');
    } finally {
      setLoading(false);
    }
  };

  const loadLatestRuns = useCallback(async () => {
    setLatestLoading(true);
    setLatestError('');
    try {
      const [
        erdList,
        integrityList,
        complianceList,
        correctnessList,
        usabilityList,
        maintainabilityList,
      ] = await Promise.all([
        listERDAnalyses(repositoryId).catch(() => []),
        listIntegrityAnalyses(repositoryId).catch(() => []),
        listComplianceAnalyses(repositoryId).catch(() => []),
        listCorrectnessAnalyses(repositoryId).catch(() => []),
        listUsabilityAnalyses(repositoryId).catch(() => []),
        listMaintainabilityAnalyses(repositoryId).catch(() => []),
      ]);

      // APIs return newest first; surface the latest run for any status so in-progress jobs are visible.
      const pickLatestRun = (list) => {
        if (!Array.isArray(list) || list.length === 0) return null;
        return list[0];
      };

      const next = {
        erd: pickLatestRun(erdList),
        integrity: pickLatestRun(integrityList),
        compliance: pickLatestRun(complianceList),
        correctness: pickLatestRun(correctnessList),
        usability: pickLatestRun(usabilityList),
        maintainability: pickLatestRun(maintainabilityList),
      };
      setLatestRuns(next);
    } catch (e) {
      setLatestError('Failed to load latest results');
      setLatestRuns({
        erd: null,
        integrity: null,
        compliance: null,
        correctness: null,
        usability: null,
        maintainability: null,
      });
    } finally {
      setLatestLoading(false);
    }
  }, [repositoryId]);

  useEffect(() => {
    loadRepository();
    loadLatestRuns();
  }, [repositoryId, loadLatestRuns]);

  useEffect(() => {
    if (loading || !repository) return undefined;
    const busy = Object.values(latestRuns).some(
      (r) => r && (r.status === 'pending' || r.status === 'processing')
    );
    if (!busy) return undefined;
    const id = setInterval(() => {
      loadLatestRuns();
    }, 5000);
    return () => clearInterval(id);
  }, [latestRuns, loading, repository, loadLatestRuns]);

  const analysisGetters = {
    erd: getERDAnalysis,
    integrity: getIntegrityAnalysis,
    compliance: getComplianceAnalysis,
    correctness: getCorrectnessAnalysis,
    usability: getUsabilityAnalysis,
    maintainability: getMaintainabilityAnalysis,
  };

  const getLatestScore = (type, run) => {
    if (!run) return null;
    if (type === 'erd') {
      const v = run.coverage_score;
      return typeof v === 'number' ? v : null;
    }
    const v = run.overall_score;
    return typeof v === 'number' ? v : null;
  };

  const formatDateTime = (value) => {
    if (!value) return '—';
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return '—';
    return d.toLocaleString();
  };

  const getStatusBadgeStyle = (status, hasRun) => {
    if (!hasRun) return { ...styles.latestBadge, ...styles.badgeNone };
    if (status === 'completed') return { ...styles.latestBadge, ...styles.badgeCompleted };
    if (status === 'pending' || status === 'processing') {
      return { ...styles.latestBadge, ...styles.badgeProcessing };
    }
    if (status === 'failed') return { ...styles.latestBadge, ...styles.badgeFailed };
    return { ...styles.latestBadge, ...styles.badgeNone };
  };

  const getStatusLabel = (status, hasRun) => {
    if (!hasRun) return 'No runs';
    if (status === 'completed') return 'Completed';
    if (status === 'pending') return 'Pending…';
    if (status === 'processing') return 'Running…';
    if (status === 'failed') return 'Failed';
    return status || 'Unknown';
  };

  const handleViewLatest = async (type) => {
    const run = latestRuns[type];
    if (!run?.id) return;
    const getter = analysisGetters[type];
    if (!getter) return;
    try {
      const full = await getter(run.id);
      onAnalysisComplete(full, type);
    } catch (e) {
      setLatestError('Failed to open report');
    }
  };

  const fieldToType = {
    is_selected_erd: 'erd',
    is_selected_integrity: 'integrity',
    is_selected_compliance: 'compliance',
    is_selected_correctness: 'correctness',
    is_selected_usability: 'usability',
    is_selected_maintainability: 'maintainability',
  };

  const handleFileToggle = async (fileId, field, currentValue) => {
    try {
      const analysisType = fieldToType[field] || 'integrity';
      await updateFileSelection(repositoryId, [fileId], !currentValue, analysisType);
      setRepository((prev) => ({
        ...prev,
        discovered_files: prev.discovered_files.map((f) =>
          f.id === fileId ? { ...f, [field]: !currentValue } : f
        ),
      }));
    } catch (err) {
      setError('Failed to update file selection');
    }
  };

  const handleSelectAll = async (fileType, field, selected, explicitFileIds = null) => {
    const fileIds = explicitFileIds || repository.discovered_files
      .filter((f) => {
        if (fileType === 'erd') {
          return f.file_type === 'erd_image' || f.file_type === 'user_story';
        } else {
          return f.file_type === 'code' || f.file_type === 'config';
        }
      })
      .map((f) => f.id);

    const analysisType = fieldToType[field] || 'integrity';

    try {
      await updateFileSelection(repositoryId, fileIds, selected, analysisType);
      setRepository((prev) => ({
        ...prev,
        discovered_files: prev.discovered_files.map((f) => {
          if (fileType === 'erd' && (f.file_type === 'erd_image' || f.file_type === 'user_story')) {
            if (!explicitFileIds || explicitFileIds.includes(f.id)) {
              return { ...f, [field]: selected };
            }
          }
          if (fileType === 'integrity' && (f.file_type === 'code' || f.file_type === 'config')) {
            if (!explicitFileIds || explicitFileIds.includes(f.id)) {
              return { ...f, [field]: selected };
            }
          }
          return f;
        }),
      }));
    } catch (err) {
      setError('Failed to update file selection');
    }
  };

  const handleClearAiSelections = async () => {
    const erdIds = erdFiles.map((f) => f.id);
    const codeIds = integrityFiles.map((f) => f.id);
    try {
      if (erdIds.length > 0) {
        await updateFileSelection(repositoryId, erdIds, false, 'erd');
      }
      if (codeIds.length > 0) {
        await updateFileSelection(repositoryId, codeIds, false, 'integrity');
        await updateFileSelection(repositoryId, codeIds, false, 'compliance');
        await updateFileSelection(repositoryId, codeIds, false, 'correctness');
        await updateFileSelection(repositoryId, codeIds, false, 'usability');
        await updateFileSelection(repositoryId, codeIds, false, 'maintainability');
      }
      setRepository((prev) => ({
        ...prev,
        discovered_files: prev.discovered_files.map((f) => ({
          ...f,
          is_selected_erd:
            f.file_type === 'erd_image' || f.file_type === 'user_story' ? false : f.is_selected_erd,
          is_selected_integrity:
            f.file_type === 'code' || f.file_type === 'config' ? false : f.is_selected_integrity,
          is_selected_compliance:
            f.file_type === 'code' || f.file_type === 'config' ? false : f.is_selected_compliance,
          is_selected_correctness:
            f.file_type === 'code' || f.file_type === 'config' ? false : f.is_selected_correctness,
          is_selected_usability:
            f.file_type === 'code' || f.file_type === 'config' ? false : f.is_selected_usability,
          is_selected_maintainability:
            f.file_type === 'code' || f.file_type === 'config' ? false : f.is_selected_maintainability,
        })),
      }));
    } catch (err) {
      setError('Failed to clear AI selections');
    }
  };

  const handleClearAllSelections = async () => {
    const erdIds = erdFiles.map((f) => f.id);
    const codeIds = integrityFiles.map((f) => f.id);
    try {
      if (erdIds.length > 0) {
        await updateFileSelection(repositoryId, erdIds, false, 'erd');
      }
      if (codeIds.length > 0) {
        await updateFileSelection(repositoryId, codeIds, false, 'integrity');
        await updateFileSelection(repositoryId, codeIds, false, 'compliance');
        await updateFileSelection(repositoryId, codeIds, false, 'correctness');
        await updateFileSelection(repositoryId, codeIds, false, 'usability');
        await updateFileSelection(repositoryId, codeIds, false, 'maintainability');
      }
      setRepository((prev) => ({
        ...prev,
        discovered_files: prev.discovered_files.map((f) => ({
          ...f,
          is_selected_erd:
            f.file_type === 'erd_image' || f.file_type === 'user_story' ? false : f.is_selected_erd,
          is_selected_integrity:
            f.file_type === 'code' || f.file_type === 'config' ? false : f.is_selected_integrity,
          is_selected_compliance:
            f.file_type === 'code' || f.file_type === 'config' ? false : f.is_selected_compliance,
          is_selected_correctness:
            f.file_type === 'code' || f.file_type === 'config' ? false : f.is_selected_correctness,
          is_selected_usability:
            f.file_type === 'code' || f.file_type === 'config' ? false : f.is_selected_usability,
          is_selected_maintainability:
            f.file_type === 'code' || f.file_type === 'config' ? false : f.is_selected_maintainability,
        })),
      }));
    } catch (err) {
      setError('Failed to clear file selections');
    }
  };

  const handleReclassify = async (fileId, newType) => {
    try {
      await updateFileType(repositoryId, fileId, newType);
      setRepository((prev) => ({
        ...prev,
        discovered_files: prev.discovered_files.map((f) =>
          f.id === fileId ? { ...f, file_type: newType } : f
        ),
      }));
    } catch (err) {
      setError('Failed to reclassify file');
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    setError(null);
    try {
      await rediscoverFiles(repositoryId);
      await loadRepository();
      await loadLatestRuns();
    } catch (err) {
      setError('Failed to refresh files');
    } finally {
      setRefreshing(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this repository?')) {
      return;
    }

    try {
      await deleteRepository(repositoryId);
      onBack();
    } catch (err) {
      setError('Failed to delete repository');
    }
  };

  const handleAnalyze = async () => {
    const anySelected = Object.values(analysisTypes).some(Boolean);
    if (!anySelected) {
      setError('Please select at least one analysis type');
      return;
    }

    setAnalyzing(true);
    setError(null);

    const starters = {
      erd: () => startERDAnalysis(repositoryId, tamuApiKey, tamuModel),
      integrity: () => startIntegrityAnalysis(repositoryId, tamuApiKey, tamuModel),
      compliance: () => startComplianceAnalysis(repositoryId, tamuApiKey, tamuModel),
      correctness: () => startCorrectnessAnalysis(repositoryId, tamuApiKey, tamuModel),
      usability: () => startUsabilityAnalysis(repositoryId, tamuApiKey, tamuModel),
      maintainability: () => startMaintainabilityAnalysis(repositoryId, tamuApiKey, tamuModel),
    };

    const selectedTypes = Object.keys(analysisTypes).filter((t) => analysisTypes[t]);
    if (selectedTypes.length === 0) return;

    const total = selectedTypes.length;
    const terminalAnalysisIds = new Set();

    try {
      // Start each analysis sequentially to avoid race conditions
      const startedAnalyses = [];
      for (const type of selectedTypes) {
        const analysis = await starters[type]();
        console.log(`Started ${type} analysis with id=${analysis.id}`);
        startedAnalyses.push({ type, id: analysis.id });
        setRunningTypes((prev) => ({ ...prev, [type]: true }));
      }

      await loadLatestRuns();

      // Poll each analysis independently (update status but do not auto-navigate)
      for (const { type, id } of startedAnalyses) {
        pollAnalysis(type, id, (updatedAnalysis) => {
          if (updatedAnalysis.status === 'completed' || updatedAnalysis.status === 'failed') {
            if (terminalAnalysisIds.has(id)) return;
            terminalAnalysisIds.add(id);
            setRunningTypes((prev) => ({ ...prev, [type]: false }));
            // Refresh cards as each run finishes so users see scores without waiting for the whole batch
            loadLatestRuns();
            if (terminalAnalysisIds.size >= total) {
              setAnalyzing(false);
            }
          }
        });
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to start analysis');
      setAnalyzing(false);
    }
  };

  if (loading) {
    return (
      <div style={styles.loading}>
        <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
        <div style={styles.spinner}></div>
        <p>Loading repository...</p>
      </div>
    );
  }

  if (!repository) {
    return (
      <div style={styles.loading}>
        <p>Repository not found</p>
        <button style={{ ...styles.button, ...styles.backButton, marginTop: '16px' }} onClick={onBack}>
          Go Back
        </button>
      </div>
    );
  }

  // Separate files by type
  const erdFiles = repository.discovered_files?.filter(
    (f) => f.file_type === 'erd_image' || f.file_type === 'user_story'
  ) || [];
  const integrityFiles = repository.discovered_files?.filter(
    (f) => f.file_type === 'code' || f.file_type === 'config'
  ) || [];
  const otherFiles = repository.discovered_files?.filter(
    (f) => f.file_type === 'other'
  ) || [];

  const selectedErdCount = erdFiles.filter((f) => f.is_selected_erd).length;
  const selectedIntegrityCount = integrityFiles.filter((f) => f.is_selected_integrity).length;

  const canAnalyzeErd = erdFiles.filter((f) => f.file_type === 'erd_image' && f.is_selected_erd).length > 0 &&
                        erdFiles.filter((f) => f.file_type === 'user_story' && f.is_selected_erd).length > 0;
  const canAnalyzeIntegrity = selectedIntegrityCount > 0;
  // New analysis types reuse the same code/config files as integrity
  const canAnalyzeCompliance = integrityFiles.filter((f) => f.is_selected_compliance).length > 0;
  const canAnalyzeCorrectness = integrityFiles.filter((f) => f.is_selected_correctness).length > 0;
  const canAnalyzeUsability = integrityFiles.filter((f) => f.is_selected_usability).length > 0;
  const canAnalyzeMaintainability = integrityFiles.filter((f) => f.is_selected_maintainability).length > 0;

  const canAnalyzeMap = {
    erd: canAnalyzeErd,
    integrity: canAnalyzeIntegrity,
    compliance: canAnalyzeCompliance,
    correctness: canAnalyzeCorrectness,
    usability: canAnalyzeUsability,
    maintainability: canAnalyzeMaintainability,
  };

  const canAnalyze = Object.keys(analysisTypes).some((t) => analysisTypes[t] && canAnalyzeMap[t]);

  const latestCards = [
    { type: 'erd', label: 'ERD', icon: '📊', scoreLabel: 'Coverage' },
    { type: 'integrity', label: 'Integrity', icon: '🔒', scoreLabel: 'Overall' },
    { type: 'compliance', label: 'Compliance', icon: '✅', scoreLabel: 'Overall' },
    { type: 'correctness', label: 'Correctness', icon: '✔️', scoreLabel: 'Overall' },
    { type: 'usability', label: 'Usability', icon: '🧑‍💻', scoreLabel: 'Overall' },
    { type: 'maintainability', label: 'Maintainability', icon: '⚙️', scoreLabel: 'Overall' },
  ];

  return (
    <div style={styles.container}>
      <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>

      <div style={styles.header}>
        <div style={styles.repoInfo}>
          <h2 style={styles.repoName}>
            {repository.name}
            <span
              style={{
                ...styles.sourceBadge,
                ...(repository.source_type === 'github' ? styles.badgeGithub : styles.badgeFolder),
              }}
            >
              {repository.source_type === 'github' ? 'GitHub' : 'Uploaded'}
            </span>
          </h2>
          <p style={styles.repoMeta}>
            {repository.github_repo_full_name || 'Local upload'} &bull;{' '}
            {repository.discovered_files?.length || 0} files discovered
          </p>
        </div>
        <div style={styles.headerButtons}>
          <button
            style={{ ...styles.button, ...styles.refreshButton }}
            onClick={handleRefresh}
            disabled={refreshing}
          >
            {refreshing ? 'Scanning...' : 'Re-scan'}
          </button>
          <button style={{ ...styles.button, ...styles.deleteButton }} onClick={handleDelete}>
            Delete
          </button>
          <button style={{ ...styles.button, ...styles.backButton }} onClick={onBack}>
            Back
          </button>
        </div>
      </div>

      {error && <div style={styles.error}>{error}</div>}

      <div style={styles.latestSection}>
        <div style={styles.latestHeaderRow}>
          <h3 style={styles.latestTitle}>📌 Latest results</h3>
          <span style={{ fontSize: '12px', color: '#666', flex: '1 1 100%' }}>
            Each card shows the most recent run for that tool. Use New run / Run again to configure and start analyses.
          </span>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <button
              type="button"
              style={{ ...styles.expanderButton, ...(showNewRun ? {} : styles.expanderButtonPrimary) }}
              onClick={() => {
                setShowNewRun((open) => {
                  if (!open) {
                    setAnalysisTypes({
                      erd: false,
                      integrity: false,
                      compliance: false,
                      correctness: false,
                      usability: false,
                      maintainability: false,
                    });
                  }
                  return !open;
                });
              }}
            >
              {showNewRun ? 'Hide new run' : 'New run / Run again'}
            </button>
            <button style={styles.expanderButton} onClick={loadLatestRuns} disabled={latestLoading}>
              {latestLoading ? 'Refreshing…' : 'Refresh results'}
            </button>
          </div>
        </div>

        {showNewRun && (
          <div style={styles.newRunPanel}>
            <div style={styles.newRunHeader}>
              <h3 style={styles.newRunTitle}>🧪 New run</h3>
              <button type="button" style={styles.expanderButton} onClick={() => setShowNewRun(false)}>
                Collapse
              </button>
            </div>

            {(analysisTypes.erd || analysisTypes.integrity) && (
              <div style={styles.content}>
                {analysisTypes.erd && (
                  <div style={styles.section}>
                    <h3 style={styles.sectionTitle}>
                      <span style={styles.sectionIcon}>&#128202;</span>
                      ERD Analysis Files ({selectedErdCount} selected)
                    </h3>
                    <FileList
                      files={erdFiles}
                      selectionField="is_selected_erd"
                      onToggle={handleFileToggle}
                      onSelectAll={(selected) => handleSelectAll('erd', 'is_selected_erd', selected)}
                      scoreField="confidence_score"
                      scoreLabel="Confidence"
                    />
                  </div>
                )}

                {analysisTypes.integrity && (
                  <div style={styles.section}>
                    <h3 style={styles.sectionTitle}>
                      <span style={styles.sectionIcon}>&#128274;</span>
                      Code Analysis Files ({selectedIntegrityCount} selected for Integrity)
                    </h3>
                    <FileList
                      files={integrityFiles}
                      selectionField="is_selected_integrity"
                      onToggle={handleFileToggle}
                      onSelectAll={(selected) => handleSelectAll('integrity', 'is_selected_integrity', selected)}
                      scoreField="relevance_score"
                      scoreLabel="Relevance"
                    />
                  </div>
                )}
              </div>
            )}

            {(analysisTypes.compliance || analysisTypes.correctness || analysisTypes.usability || analysisTypes.maintainability) && (
              <div style={{ ...styles.content, marginTop: '20px' }}>
                {analysisTypes.compliance && (
                  <div style={styles.section}>
                    <h3 style={styles.sectionTitle}>
                      <span style={styles.sectionIcon}>&#9989;</span>
                      Compliance Files ({integrityFiles.filter((f) => f.is_selected_compliance).length} selected)
                    </h3>
                    <FileList
                      files={integrityFiles}
                      selectionField="is_selected_compliance"
                      onToggle={handleFileToggle}
                      onSelectAll={(selected) => handleSelectAll('integrity', 'is_selected_compliance', selected)}
                      scoreField="relevance_score"
                      scoreLabel="Relevance"
                    />
                  </div>
                )}
                {analysisTypes.correctness && (
                  <div style={styles.section}>
                    <h3 style={styles.sectionTitle}>
                      <span style={styles.sectionIcon}>&#10004;</span>
                      Correctness Files ({integrityFiles.filter((f) => f.is_selected_correctness).length} selected)
                    </h3>
                    <FileList
                      files={integrityFiles}
                      selectionField="is_selected_correctness"
                      onToggle={handleFileToggle}
                      onSelectAll={(selected) => handleSelectAll('integrity', 'is_selected_correctness', selected)}
                      scoreField="relevance_score"
                      scoreLabel="Relevance"
                    />
                  </div>
                )}
                {analysisTypes.usability && (
                  <div style={styles.section}>
                    <h3 style={styles.sectionTitle}>
                      <span style={styles.sectionIcon}>&#128100;</span>
                      Usability Files ({integrityFiles.filter((f) => f.is_selected_usability).length} selected)
                    </h3>
                    <FileList
                      files={integrityFiles}
                      selectionField="is_selected_usability"
                      onToggle={handleFileToggle}
                      onSelectAll={(selected) => handleSelectAll('integrity', 'is_selected_usability', selected)}
                      scoreField="relevance_score"
                      scoreLabel="Relevance"
                    />
                  </div>
                )}
                {analysisTypes.maintainability && (
                  <div style={styles.section}>
                    <h3 style={styles.sectionTitle}>
                      <span style={styles.sectionIcon}>&#9881;</span>
                      Maintainability Files ({integrityFiles.filter((f) => f.is_selected_maintainability).length} selected)
                    </h3>
                    <FileList
                      files={integrityFiles}
                      selectionField="is_selected_maintainability"
                      onToggle={handleFileToggle}
                      onSelectAll={(selected) => handleSelectAll('integrity', 'is_selected_maintainability', selected)}
                      scoreField="relevance_score"
                      scoreLabel="Relevance"
                    />
                  </div>
                )}
              </div>
            )}

            {otherFiles.length > 0 && (
              <div style={{ marginTop: '16px' }}>
                <button
                  type="button"
                  style={styles.expanderButton}
                  onClick={() => setShowOtherFiles((v) => !v)}
                >
                  {showOtherFiles ? 'Hide' : 'Show'} unclassified files ({otherFiles.length})
                </button>
                {showOtherFiles && (
                  <div style={{ ...styles.section, marginTop: '10px' }}>
                    <h3 style={styles.sectionTitle}>
                      <span style={styles.sectionIcon}>&#128196;</span>
                      Unclassified Files &mdash; use the dropdown to reclassify
                    </h3>
                    <FileList
                      files={otherFiles}
                      selectionField="is_selected_erd"
                      onToggle={handleFileToggle}
                      onSelectAll={(selected) => handleSelectAll('erd', 'is_selected_erd', selected)}
                      scoreField="confidence_score"
                      scoreLabel="Confidence"
                      onReclassify={handleReclassify}
                    />
                  </div>
                )}
              </div>
            )}

            <div style={styles.analyzeSection}>
              <AnalysisTypeSelector
                analysisTypes={analysisTypes}
                onChange={setAnalysisTypes}
                canAnalyzeErd={canAnalyzeErd}
                canAnalyzeIntegrity={canAnalyzeIntegrity}
                canAnalyzeCompliance={canAnalyzeCompliance}
                canAnalyzeCorrectness={canAnalyzeCorrectness}
                canAnalyzeUsability={canAnalyzeUsability}
                canAnalyzeMaintainability={canAnalyzeMaintainability}
              />

              <button
                onClick={handleAnalyze}
                disabled={!canAnalyze || analyzing}
                style={{
                  ...styles.analyzeButton,
                  ...(!canAnalyze || analyzing ? styles.analyzeButtonDisabled : {}),
                }}
              >
                {analyzing ? 'Analyzing...' : 'Start Analysis'}
              </button>

              {!canAnalyze && (
                <p style={styles.hint}>
                  {analysisTypes.erd && !canAnalyzeErd && (
                    <>For ERD analysis, select at least one ERD image and one user story file. </>
                  )}
                  {analysisTypes.integrity && !canAnalyzeIntegrity && (
                    <>For Integrity analysis, select at least one code or config file. </>
                  )}
                  {analysisTypes.compliance && !canAnalyzeCompliance && (
                    <>For Compliance analysis, select code/config files below. </>
                  )}
                  {analysisTypes.correctness && !canAnalyzeCorrectness && (
                    <>For Correctness analysis, select code/config files below. </>
                  )}
                  {analysisTypes.usability && !canAnalyzeUsability && (
                    <>For Usability analysis, select code/config files below. </>
                  )}
                  {analysisTypes.maintainability && !canAnalyzeMaintainability && (
                    <>For Maintainability analysis, select code/config files below. </>
                  )}
                  {!Object.values(analysisTypes).some(Boolean) && (
                    <>Select an analysis type above to begin. </>
                  )}
                </p>
              )}
            </div>
          </div>
        )}

        <div style={styles.latestGrid}>
          {latestCards.map((c) => {
            const run = latestRuns[c.type];
            const status = run?.status;
            const isCompleted = status === 'completed';
            const isInProgress = status === 'pending' || status === 'processing';
            const isRunning = isInProgress || runningTypes[c.type];
            const hasRun = Boolean(run && run.id);
            const score = getLatestScore(c.type, run);

            let badgeStyle;
            let badgeLabel;
            if (isRunning) {
              badgeStyle = { ...styles.latestBadge, ...styles.badgeProcessing };
              badgeLabel = 'Running…';
            } else if (latestLoading) {
              badgeStyle = { ...styles.latestBadge, ...styles.badgeProcessing };
              badgeLabel = 'Loading…';
            } else {
              badgeStyle = getStatusBadgeStyle(status, hasRun);
              badgeLabel = getStatusLabel(status, hasRun);
            }

            const showScore = !isRunning && score != null;

            return (
              <div key={c.type} style={styles.latestCard}>
                <div
                  onClick={() => {
                    if (!isRunning && isCompleted && run?.id) {
                      handleViewLatest(c.type);
                    }
                  }}
                  style={{ cursor: !isRunning && isCompleted && run?.id ? 'pointer' : 'default' }}
                >
                  <div style={styles.latestCardTop}>
                    <h4 style={styles.latestCardTitle}>
                      <span>{c.icon}</span>
                      <span>{c.label}</span>
                    </h4>
                    <span style={badgeStyle}>{badgeLabel}</span>
                  </div>

                  <div style={styles.latestMetricsRow}>
                    <div>
                      <div style={styles.latestScore}>{showScore ? Math.round(score) : '—'}</div>
                      <div style={styles.latestScoreLabel}>{c.scoreLabel} score</div>
                    </div>
                    <div style={styles.latestMeta}>
                      <div>Created: {formatDateTime(run?.created_at)}</div>
                      <div>Completed: {formatDateTime(run?.completed_at)}</div>
                    </div>
                  </div>
                </div>

                <div style={styles.latestActions}>
                  {isCompleted && !isRunning && (
                    <button
                      style={styles.smallButton}
                      onClick={() => handleViewLatest(c.type)}
                      disabled={!run?.id}
                    >
                      View report
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {latestError && <div style={styles.latestError}>{latestError}</div>}
      </div>
    </div>
  );
}
