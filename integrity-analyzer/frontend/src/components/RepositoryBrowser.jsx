import React, { useState, useEffect } from 'react';
import { getRepository, updateFileSelection, rediscoverFiles, startAnalysis, listAnalyses, deleteRepository } from '../api';

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
  title: {
    fontSize: '1.5rem',
    fontWeight: '600',
    color: '#1e3a5f',
  },
  headerActions: {
    display: 'flex',
    gap: '10px',
  },
  button: {
    padding: '10px 20px',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '0.95rem',
    fontWeight: '500',
    transition: 'all 0.2s',
  },
  primaryButton: {
    background: '#1e3a5f',
    color: 'white',
  },
  secondaryButton: {
    background: '#e0e0e0',
    color: '#333',
  },
  dangerButton: {
    background: '#dc3545',
    color: 'white',
  },
  disabledButton: {
    background: '#ccc',
    cursor: 'not-allowed',
  },
  section: {
    marginBottom: '30px',
  },
  sectionTitle: {
    fontSize: '1.1rem',
    fontWeight: '600',
    marginBottom: '15px',
    color: '#333',
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  badge: {
    padding: '3px 10px',
    borderRadius: '12px',
    fontSize: '0.8rem',
    fontWeight: '500',
  },
  fileList: {
    border: '1px solid #e0e0e0',
    borderRadius: '8px',
    maxHeight: '300px',
    overflowY: 'auto',
  },
  fileItem: {
    display: 'flex',
    alignItems: 'center',
    padding: '12px 15px',
    borderBottom: '1px solid #e0e0e0',
    gap: '12px',
  },
  checkbox: {
    width: '18px',
    height: '18px',
    cursor: 'pointer',
  },
  fileName: {
    flex: 1,
    fontFamily: 'monospace',
    fontSize: '0.9rem',
  },
  fileType: {
    padding: '2px 8px',
    borderRadius: '4px',
    fontSize: '0.75rem',
    fontWeight: '500',
  },
  codeType: {
    background: '#e3f2fd',
    color: '#1565c0',
  },
  configType: {
    background: '#fff3e0',
    color: '#ef6c00',
  },
  docType: {
    background: '#e8f5e9',
    color: '#2e7d32',
  },
  relevanceScore: {
    fontSize: '0.85rem',
    color: '#666',
    minWidth: '50px',
    textAlign: 'right',
  },
  selectAll: {
    padding: '10px 15px',
    background: '#f5f5f5',
    borderBottom: '1px solid #e0e0e0',
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  analysisList: {
    border: '1px solid #e0e0e0',
    borderRadius: '8px',
  },
  analysisItem: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '15px',
    borderBottom: '1px solid #e0e0e0',
    cursor: 'pointer',
    transition: 'background 0.2s',
  },
  analysisInfo: {
    display: 'flex',
    alignItems: 'center',
    gap: '15px',
  },
  statusBadge: {
    padding: '4px 12px',
    borderRadius: '12px',
    fontSize: '0.8rem',
    fontWeight: '500',
  },
  statusPending: {
    background: '#fff3e0',
    color: '#ef6c00',
  },
  statusProcessing: {
    background: '#e3f2fd',
    color: '#1565c0',
  },
  statusCompleted: {
    background: '#e8f5e9',
    color: '#2e7d32',
  },
  statusFailed: {
    background: '#ffebee',
    color: '#c62828',
  },
  scoreBadge: {
    fontSize: '1.1rem',
    fontWeight: '600',
  },
  loading: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '40px',
    color: '#666',
  },
  spinner: {
    width: '24px',
    height: '24px',
    border: '3px solid #e0e0e0',
    borderTop: '3px solid #1e3a5f',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
    marginRight: '12px',
  },
  emptyState: {
    padding: '40px',
    textAlign: 'center',
    color: '#999',
  },
  meta: {
    display: 'flex',
    gap: '20px',
    marginBottom: '20px',
    fontSize: '0.9rem',
    color: '#666',
  },
};

function RepositoryBrowser({ repositoryId, onAnalysisSelect, onBack, onDeleted }) {
  const [repository, setRepository] = useState(null);
  const [analyses, setAnalyses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [rediscovering, setRediscovering] = useState(false);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchAnalyses, 3000);
    return () => clearInterval(interval);
  }, [repositoryId]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [repoResponse, analysesResponse] = await Promise.all([
        getRepository(repositoryId),
        listAnalyses(repositoryId),
      ]);
      setRepository(repoResponse.data);
      setAnalyses(analysesResponse.data);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchAnalyses = async () => {
    try {
      const response = await listAnalyses(repositoryId);
      setAnalyses(response.data);
    } catch (error) {
      console.error('Error fetching analyses:', error);
    }
  };

  const handleFileToggle = async (fileId, currentSelected) => {
    try {
      await updateFileSelection(repositoryId, [fileId], !currentSelected);
      setRepository((prev) => ({
        ...prev,
        discovered_files: prev.discovered_files.map((f) =>
          f.id === fileId ? { ...f, is_selected: !currentSelected } : f
        ),
      }));
    } catch (error) {
      console.error('Error updating selection:', error);
    }
  };

  const handleSelectAll = async (fileType, select) => {
    const fileIds = repository.discovered_files
      .filter((f) => f.file_type === fileType)
      .map((f) => f.id);

    try {
      await updateFileSelection(repositoryId, fileIds, select);
      setRepository((prev) => ({
        ...prev,
        discovered_files: prev.discovered_files.map((f) =>
          f.file_type === fileType ? { ...f, is_selected: select } : f
        ),
      }));
    } catch (error) {
      console.error('Error updating selection:', error);
    }
  };

  const handleRediscover = async () => {
    setRediscovering(true);
    try {
      await rediscoverFiles(repositoryId);
      // Wait a bit then refresh
      setTimeout(fetchData, 2000);
    } catch (error) {
      console.error('Error rediscovering:', error);
    } finally {
      setRediscovering(false);
    }
  };

  const handleStartAnalysis = async () => {
    setAnalyzing(true);
    try {
      const response = await startAnalysis(repositoryId);
      fetchAnalyses();
      // Navigate to the new analysis
      setTimeout(() => {
        onAnalysisSelect(response.data.analysis_id);
      }, 500);
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to start analysis');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this repository and all its analyses?')) {
      return;
    }

    try {
      await deleteRepository(repositoryId);
      onDeleted();
    } catch (error) {
      console.error('Error deleting:', error);
      alert('Failed to delete repository');
    }
  };

  const getFileTypeStyle = (fileType) => {
    switch (fileType) {
      case 'code':
        return styles.codeType;
      case 'config':
        return styles.configType;
      case 'documentation':
        return styles.docType;
      default:
        return {};
    }
  };

  const getStatusStyle = (status) => {
    switch (status) {
      case 'pending':
        return styles.statusPending;
      case 'processing':
        return styles.statusProcessing;
      case 'completed':
        return styles.statusCompleted;
      case 'failed':
        return styles.statusFailed;
      default:
        return {};
    }
  };

  const getScoreColor = (score) => {
    if (score >= 80) return '#2e7d32';
    if (score >= 60) return '#ef6c00';
    if (score >= 40) return '#f57c00';
    return '#c62828';
  };

  if (loading) {
    return (
      <div style={styles.loading}>
        <style>
          {`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}
        </style>
        <div style={styles.spinner}></div>
        Loading repository...
      </div>
    );
  }

  if (!repository) {
    return <div style={styles.emptyState}>Repository not found</div>;
  }

  const selectedCount = repository.discovered_files.filter((f) => f.is_selected).length;
  const codeFiles = repository.discovered_files.filter((f) => f.file_type === 'code');
  const configFiles = repository.discovered_files.filter((f) => f.file_type === 'config');
  const docFiles = repository.discovered_files.filter((f) => f.file_type === 'documentation');

  return (
    <div style={styles.container}>
      <style>
        {`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}
      </style>

      <div style={styles.header}>
        <div>
          <h2 style={styles.title}>{repository.name}</h2>
          <div style={styles.meta}>
            <span>Source: {repository.source_type === 'github' ? 'GitHub' : 'Upload'}</span>
            <span>{repository.discovered_files.length} files discovered</span>
            <span>{selectedCount} selected</span>
          </div>
        </div>
        <div style={styles.headerActions}>
          <button
            style={{ ...styles.button, ...styles.secondaryButton }}
            onClick={handleRediscover}
            disabled={rediscovering}
          >
            {rediscovering ? 'Scanning...' : 'Re-scan Files'}
          </button>
          <button
            style={{
              ...styles.button,
              ...styles.primaryButton,
              ...(selectedCount === 0 || analyzing ? styles.disabledButton : {}),
            }}
            onClick={handleStartAnalysis}
            disabled={selectedCount === 0 || analyzing}
          >
            {analyzing ? 'Starting...' : 'Run Integrity Analysis'}
          </button>
          <button
            style={{ ...styles.button, ...styles.dangerButton }}
            onClick={handleDelete}
          >
            Delete
          </button>
        </div>
      </div>

      {/* Code Files */}
      {codeFiles.length > 0 && (
        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>
            Code Files
            <span style={{ ...styles.badge, background: '#e3f2fd', color: '#1565c0' }}>
              {codeFiles.length}
            </span>
          </h3>
          <div style={styles.fileList}>
            <div style={styles.selectAll}>
              <input
                type="checkbox"
                style={styles.checkbox}
                checked={codeFiles.every((f) => f.is_selected)}
                onChange={(e) => handleSelectAll('code', e.target.checked)}
              />
              <span>Select all code files</span>
            </div>
            {codeFiles.map((file) => (
              <div key={file.id} style={styles.fileItem}>
                <input
                  type="checkbox"
                  style={styles.checkbox}
                  checked={file.is_selected}
                  onChange={() => handleFileToggle(file.id, file.is_selected)}
                />
                <span style={styles.fileName}>{file.file_path}</span>
                {file.language && (
                  <span style={{ ...styles.fileType, ...styles.codeType }}>
                    {file.language}
                  </span>
                )}
                <span style={styles.relevanceScore}>{file.relevance_score}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Config Files */}
      {configFiles.length > 0 && (
        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>
            Config Files
            <span style={{ ...styles.badge, background: '#fff3e0', color: '#ef6c00' }}>
              {configFiles.length}
            </span>
          </h3>
          <div style={styles.fileList}>
            <div style={styles.selectAll}>
              <input
                type="checkbox"
                style={styles.checkbox}
                checked={configFiles.every((f) => f.is_selected)}
                onChange={(e) => handleSelectAll('config', e.target.checked)}
              />
              <span>Select all config files</span>
            </div>
            {configFiles.map((file) => (
              <div key={file.id} style={styles.fileItem}>
                <input
                  type="checkbox"
                  style={styles.checkbox}
                  checked={file.is_selected}
                  onChange={() => handleFileToggle(file.id, file.is_selected)}
                />
                <span style={styles.fileName}>{file.file_path}</span>
                <span style={{ ...styles.fileType, ...styles.configType }}>config</span>
                <span style={styles.relevanceScore}>{file.relevance_score}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Documentation Files */}
      {docFiles.length > 0 && (
        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>
            Documentation
            <span style={{ ...styles.badge, background: '#e8f5e9', color: '#2e7d32' }}>
              {docFiles.length}
            </span>
          </h3>
          <div style={styles.fileList}>
            <div style={styles.selectAll}>
              <input
                type="checkbox"
                style={styles.checkbox}
                checked={docFiles.every((f) => f.is_selected)}
                onChange={(e) => handleSelectAll('documentation', e.target.checked)}
              />
              <span>Select all documentation</span>
            </div>
            {docFiles.map((file) => (
              <div key={file.id} style={styles.fileItem}>
                <input
                  type="checkbox"
                  style={styles.checkbox}
                  checked={file.is_selected}
                  onChange={() => handleFileToggle(file.id, file.is_selected)}
                />
                <span style={styles.fileName}>{file.file_path}</span>
                <span style={{ ...styles.fileType, ...styles.docType }}>docs</span>
                <span style={styles.relevanceScore}>{file.relevance_score}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Previous Analyses */}
      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>
          Analysis History
          <span style={{ ...styles.badge, background: '#f5f5f5', color: '#666' }}>
            {analyses.length}
          </span>
        </h3>
        {analyses.length > 0 ? (
          <div style={styles.analysisList}>
            {analyses.map((analysis) => (
              <div
                key={analysis.id}
                style={styles.analysisItem}
                onClick={() => onAnalysisSelect(analysis.id)}
              >
                <div style={styles.analysisInfo}>
                  <span style={{ ...styles.statusBadge, ...getStatusStyle(analysis.status) }}>
                    {analysis.status}
                  </span>
                  <span>{new Date(analysis.created_at).toLocaleString()}</span>
                </div>
                {analysis.overall_score !== null && (
                  <span
                    style={{
                      ...styles.scoreBadge,
                      color: getScoreColor(analysis.overall_score),
                    }}
                  >
                    {Math.round(analysis.overall_score)}%
                  </span>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div style={styles.emptyState}>No analyses yet. Select files and run an analysis.</div>
        )}
      </div>
    </div>
  );
}

export default RepositoryBrowser;
