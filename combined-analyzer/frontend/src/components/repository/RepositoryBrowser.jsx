import React, { useState, useEffect } from 'react';
import {
  getRepository,
  updateFileSelection,
  rediscoverFiles,
  deleteRepository,
  startERDAnalysis,
  startIntegrityAnalysis,
  pollAnalysis,
} from '../../api';
import AnalysisTypeSelector from './AnalysisTypeSelector';
import FileList from './FileList';

const styles = {
  container: {
    maxWidth: '900px',
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
    gridTemplateColumns: '1fr 1fr',
    gap: '20px',
  },
  section: {
    backgroundColor: '#fff',
    borderRadius: '12px',
    padding: '20px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
  },
  sectionTitle: {
    margin: '0 0 16px 0',
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
  const [analysisTypes, setAnalysisTypes] = useState({ erd: false, integrity: false });

  useEffect(() => {
    loadRepository();
  }, [repositoryId]);

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

  const handleFileToggle = async (fileId, field, currentValue) => {
    try {
      const analysisType = field === 'is_selected_erd' ? 'erd' : 'integrity';
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

  const handleSelectAll = async (fileType, field, selected) => {
    const fileIds = repository.discovered_files
      .filter((f) => {
        if (fileType === 'erd') {
          return f.file_type === 'erd_image' || f.file_type === 'user_story';
        } else {
          return f.file_type === 'code' || f.file_type === 'config';
        }
      })
      .map((f) => f.id);

    const analysisType = field === 'is_selected_erd' ? 'erd' : 'integrity';

    try {
      await updateFileSelection(repositoryId, fileIds, selected, analysisType);
      setRepository((prev) => ({
        ...prev,
        discovered_files: prev.discovered_files.map((f) => {
          if (fileType === 'erd' && (f.file_type === 'erd_image' || f.file_type === 'user_story')) {
            return { ...f, [field]: selected };
          }
          if (fileType === 'integrity' && (f.file_type === 'code' || f.file_type === 'config')) {
            return { ...f, [field]: selected };
          }
          return f;
        }),
      }));
    } catch (err) {
      setError('Failed to update file selection');
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    setError(null);
    try {
      await rediscoverFiles(repositoryId);
      await loadRepository();
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
    if (!analysisTypes.erd && !analysisTypes.integrity) {
      setError('Please select at least one analysis type');
      return;
    }

    setAnalyzing(true);
    setError(null);

    try {
      if (analysisTypes.erd) {
        const analysis = await startERDAnalysis(repositoryId);
        pollAnalysis('erd', analysis.id, (updatedAnalysis) => {
          if (updatedAnalysis.status === 'completed' || updatedAnalysis.status === 'failed') {
            setAnalyzing(false);
            onAnalysisComplete(updatedAnalysis, 'erd');
          }
        });
      } else if (analysisTypes.integrity) {
        const analysis = await startIntegrityAnalysis(repositoryId, tamuApiKey, tamuModel);
        pollAnalysis('integrity', analysis.id, (updatedAnalysis) => {
          if (updatedAnalysis.status === 'completed' || updatedAnalysis.status === 'failed') {
            setAnalyzing(false);
            onAnalysisComplete(updatedAnalysis, 'integrity');
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

  const selectedErdCount = erdFiles.filter((f) => f.is_selected_erd).length;
  const selectedIntegrityCount = integrityFiles.filter((f) => f.is_selected_integrity).length;

  const canAnalyzeErd = erdFiles.filter((f) => f.file_type === 'erd_image' && f.is_selected_erd).length > 0 &&
                        erdFiles.filter((f) => f.file_type === 'user_story' && f.is_selected_erd).length > 0;
  const canAnalyzeIntegrity = selectedIntegrityCount > 0;

  const canAnalyze = (analysisTypes.erd && canAnalyzeErd) || (analysisTypes.integrity && canAnalyzeIntegrity);

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

      <div style={styles.content}>
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

        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>
            <span style={styles.sectionIcon}>&#128274;</span>
            Integrity Analysis Files ({selectedIntegrityCount} selected)
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
      </div>

      <div style={styles.analyzeSection}>
        <AnalysisTypeSelector
          analysisTypes={analysisTypes}
          onChange={setAnalysisTypes}
          canAnalyzeErd={canAnalyzeErd}
          canAnalyzeIntegrity={canAnalyzeIntegrity}
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
            {!analysisTypes.erd && !analysisTypes.integrity && (
              <>Select an analysis type above to begin. </>
            )}
          </p>
        )}
      </div>
    </div>
  );
}
