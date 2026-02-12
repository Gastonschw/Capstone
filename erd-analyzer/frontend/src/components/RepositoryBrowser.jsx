import React, { useState, useEffect } from 'react';
import { 
  getRepository, 
  updateFileSelection, 
  startRepositoryAnalysis,
  rediscoverFiles,
  deleteRepository,
  pollAnalysis
} from '../api';

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
    alignItems: 'flex-start',
    marginBottom: '20px',
  },
  title: {
    margin: 0,
    color: '#333',
  },
  subtitle: {
    margin: '4px 0 0 0',
    color: '#666',
    fontSize: '14px',
  },
  headerButtons: {
    display: 'flex',
    gap: '8px',
  },
  backButton: {
    backgroundColor: '#6c757d',
    color: '#fff',
    border: 'none',
    padding: '8px 16px',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '14px',
  },
  deleteButton: {
    backgroundColor: '#dc3545',
    color: '#fff',
    border: 'none',
    padding: '8px 16px',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '14px',
  },
  refreshButton: {
    backgroundColor: '#17a2b8',
    color: '#fff',
    border: 'none',
    padding: '8px 16px',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '14px',
  },
  section: {
    marginBottom: '24px',
  },
  sectionTitle: {
    margin: '0 0 12px 0',
    fontSize: '16px',
    color: '#333',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  fileCount: {
    fontSize: '12px',
    color: '#666',
    backgroundColor: '#e9ecef',
    padding: '2px 8px',
    borderRadius: '10px',
  },
  fileList: {
    border: '1px solid #ddd',
    borderRadius: '4px',
    maxHeight: '300px',
    overflowY: 'auto',
  },
  fileItem: {
    display: 'flex',
    alignItems: 'flex-start',
    padding: '12px 16px',
    borderBottom: '1px solid #eee',
    gap: '12px',
  },
  fileItemLast: {
    borderBottom: 'none',
  },
  checkbox: {
    marginTop: '4px',
    width: '18px',
    height: '18px',
    cursor: 'pointer',
  },
  fileInfo: {
    flex: 1,
  },
  fileName: {
    fontWeight: '500',
    color: '#333',
    marginBottom: '4px',
    wordBreak: 'break-all',
  },
  filePreview: {
    fontSize: '13px',
    color: '#666',
    backgroundColor: '#f8f9fa',
    padding: '8px',
    borderRadius: '4px',
    marginTop: '8px',
    whiteSpace: 'pre-wrap',
    maxHeight: '100px',
    overflow: 'hidden',
  },
  confidenceBadge: {
    fontSize: '11px',
    padding: '2px 6px',
    borderRadius: '3px',
    fontWeight: '500',
  },
  confidenceHigh: {
    backgroundColor: '#d4edda',
    color: '#155724',
  },
  confidenceMedium: {
    backgroundColor: '#fff3cd',
    color: '#856404',
  },
  confidenceLow: {
    backgroundColor: '#f8d7da',
    color: '#721c24',
  },
  analyzeButton: {
    backgroundColor: '#007bff',
    color: '#fff',
    border: 'none',
    padding: '14px 28px',
    borderRadius: '4px',
    fontSize: '16px',
    cursor: 'pointer',
    width: '100%',
    fontWeight: '500',
  },
  buttonDisabled: {
    backgroundColor: '#ccc',
    cursor: 'not-allowed',
  },
  loadingState: {
    textAlign: 'center',
    padding: '40px',
    color: '#666',
  },
  spinner: {
    display: 'inline-block',
    width: '30px',
    height: '30px',
    border: '3px solid #f3f3f3',
    borderTop: '3px solid #007bff',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
  },
  emptyState: {
    textAlign: 'center',
    padding: '40px',
    color: '#666',
  },
  emptyIcon: {
    fontSize: '48px',
    marginBottom: '12px',
  },
  error: {
    color: '#dc3545',
    padding: '12px',
    backgroundColor: '#f8d7da',
    borderRadius: '4px',
    marginBottom: '16px',
  },
  info: {
    padding: '12px',
    backgroundColor: '#e7f3ff',
    borderRadius: '4px',
    marginBottom: '16px',
    fontSize: '14px',
    color: '#004085',
  },
  sourceBadge: {
    fontSize: '12px',
    padding: '4px 8px',
    borderRadius: '4px',
    marginLeft: '12px',
  },
  sourceGitHub: {
    backgroundColor: '#24292e',
    color: '#fff',
  },
  sourceFolder: {
    backgroundColor: '#6c757d',
    color: '#fff',
  },
  selectAllRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '8px 16px',
    backgroundColor: '#f8f9fa',
    borderBottom: '1px solid #ddd',
  },
  selectAllLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    cursor: 'pointer',
    fontSize: '14px',
  },
};

function getConfidenceStyle(score) {
  if (score >= 70) return styles.confidenceHigh;
  if (score >= 50) return styles.confidenceMedium;
  return styles.confidenceLow;
}

export default function RepositoryBrowser({ 
  repositoryId, 
  onBack, 
  onAnalysisStarted 
}) {
  const [repository, setRepository] = useState(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);

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

  const handleFileToggle = async (fileId, currentSelected) => {
    try {
      await updateFileSelection(repositoryId, [fileId], !currentSelected);
      // Update local state
      setRepository(prev => ({
        ...prev,
        discovered_files: prev.discovered_files.map(f =>
          f.id === fileId ? { ...f, is_selected: !currentSelected } : f
        )
      }));
    } catch (err) {
      setError('Failed to update file selection');
    }
  };

  const handleSelectAll = async (fileType, selected) => {
    const fileIds = repository.discovered_files
      .filter(f => f.file_type === fileType)
      .map(f => f.id);
    
    try {
      await updateFileSelection(repositoryId, fileIds, selected);
      setRepository(prev => ({
        ...prev,
        discovered_files: prev.discovered_files.map(f =>
          f.file_type === fileType ? { ...f, is_selected: selected } : f
        )
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
      // Poll for updated files
      setTimeout(loadRepository, 2000);
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
    setAnalyzing(true);
    setError(null);
    
    try {
      const analysis = await startRepositoryAnalysis(repositoryId);
      
      // Start polling for results
      pollAnalysis(analysis.id, (updatedAnalysis) => {
        if (updatedAnalysis.status === 'completed' || updatedAnalysis.status === 'failed') {
          setAnalyzing(false);
          onAnalysisStarted(updatedAnalysis);
        }
      });
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to start analysis');
      setAnalyzing(false);
    }
  };

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.loadingState}>
          <div style={styles.spinner} />
          <p>Loading repository...</p>
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

  if (!repository) {
    return (
      <div style={styles.container}>
        <div style={styles.emptyState}>
          <div style={styles.emptyIcon}>📭</div>
          <p>Repository not found</p>
          <button style={styles.backButton} onClick={onBack}>Go Back</button>
        </div>
      </div>
    );
  }

  const erdFiles = repository.discovered_files?.filter(f => f.file_type === 'erd_image') || [];
  const storyFiles = repository.discovered_files?.filter(f => f.file_type === 'user_story') || [];
  const selectedErdCount = erdFiles.filter(f => f.is_selected).length;
  const selectedStoryCount = storyFiles.filter(f => f.is_selected).length;
  const canAnalyze = selectedErdCount > 0 && selectedStoryCount > 0;

  return (
    <div style={styles.container}>
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
      
      <div style={styles.header}>
        <div>
          <h2 style={styles.title}>
            {repository.name}
            <span style={{
              ...styles.sourceBadge,
              ...(repository.source_type === 'github' ? styles.sourceGitHub : styles.sourceFolder)
            }}>
              {repository.source_type === 'github' ? 'GitHub' : 'Uploaded'}
            </span>
          </h2>
          <p style={styles.subtitle}>
            {repository.github_repo_full_name || 'Local upload'}
          </p>
        </div>
        <div style={styles.headerButtons}>
          <button style={styles.refreshButton} onClick={handleRefresh} disabled={refreshing}>
            {refreshing ? 'Scanning...' : 'Re-scan'}
          </button>
          <button style={styles.deleteButton} onClick={handleDelete}>
            Delete
          </button>
          <button style={styles.backButton} onClick={onBack}>
            Back
          </button>
        </div>
      </div>

      {error && <div style={styles.error}>{error}</div>}

      {repository.discovered_files?.length === 0 ? (
        <div style={styles.info}>
          Scanning repository for ERD diagrams and user story files... This may take a moment.
          <button 
            style={{ ...styles.refreshButton, marginLeft: '12px', padding: '4px 12px' }} 
            onClick={loadRepository}
          >
            Refresh
          </button>
        </div>
      ) : (
        <>
          {/* ERD Images Section */}
          <div style={styles.section}>
            <h3 style={styles.sectionTitle}>
              ERD Diagrams
              <span style={styles.fileCount}>
                {selectedErdCount} of {erdFiles.length} selected
              </span>
            </h3>
            
            {erdFiles.length === 0 ? (
              <div style={styles.emptyState}>
                <div style={styles.emptyIcon}>🖼️</div>
                <p>No ERD images found</p>
              </div>
            ) : (
              <div style={styles.fileList}>
                <div style={styles.selectAllRow}>
                  <label style={styles.selectAllLabel}>
                    <input
                      type="checkbox"
                      checked={selectedErdCount === erdFiles.length}
                      onChange={(e) => handleSelectAll('erd_image', e.target.checked)}
                      style={styles.checkbox}
                    />
                    Select all ERD images
                  </label>
                </div>
                {erdFiles.map((file, idx) => (
                  <div 
                    key={file.id} 
                    style={{
                      ...styles.fileItem,
                      ...(idx === erdFiles.length - 1 ? styles.fileItemLast : {})
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={file.is_selected}
                      onChange={() => handleFileToggle(file.id, file.is_selected)}
                      style={styles.checkbox}
                    />
                    <div style={styles.fileInfo}>
                      <div style={styles.fileName}>
                        {file.file_path}
                        <span style={{ ...styles.confidenceBadge, ...getConfidenceStyle(file.confidence_score), marginLeft: '8px' }}>
                          {file.confidence_score}% confidence
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* User Stories Section */}
          <div style={styles.section}>
            <h3 style={styles.sectionTitle}>
              User Story Files
              <span style={styles.fileCount}>
                {selectedStoryCount} of {storyFiles.length} selected
              </span>
            </h3>
            
            {storyFiles.length === 0 ? (
              <div style={styles.emptyState}>
                <div style={styles.emptyIcon}>📝</div>
                <p>No user story files found</p>
              </div>
            ) : (
              <div style={styles.fileList}>
                <div style={styles.selectAllRow}>
                  <label style={styles.selectAllLabel}>
                    <input
                      type="checkbox"
                      checked={selectedStoryCount === storyFiles.length}
                      onChange={(e) => handleSelectAll('user_story', e.target.checked)}
                      style={styles.checkbox}
                    />
                    Select all user story files
                  </label>
                </div>
                {storyFiles.map((file, idx) => (
                  <div 
                    key={file.id} 
                    style={{
                      ...styles.fileItem,
                      ...(idx === storyFiles.length - 1 ? styles.fileItemLast : {})
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={file.is_selected}
                      onChange={() => handleFileToggle(file.id, file.is_selected)}
                      style={styles.checkbox}
                    />
                    <div style={styles.fileInfo}>
                      <div style={styles.fileName}>
                        {file.file_path}
                        <span style={{ ...styles.confidenceBadge, ...getConfidenceStyle(file.confidence_score), marginLeft: '8px' }}>
                          {file.confidence_score}% confidence
                        </span>
                      </div>
                      {file.content_preview && (
                        <div style={styles.filePreview}>
                          {file.content_preview}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Analysis Button */}
          {!canAnalyze && (
            <div style={styles.info}>
              Please select at least one ERD image and one user story file to start analysis.
            </div>
          )}

          <button
            onClick={handleAnalyze}
            disabled={!canAnalyze || analyzing}
            style={{
              ...styles.analyzeButton,
              ...(!canAnalyze || analyzing ? styles.buttonDisabled : {}),
            }}
          >
            {analyzing ? (
              <>
                <span style={{ ...styles.spinner, width: '16px', height: '16px', marginRight: '8px', verticalAlign: 'middle' }} />
                Analyzing...
              </>
            ) : (
              `Analyze ${selectedErdCount} ERD(s) with ${selectedStoryCount} User Story File(s)`
            )}
          </button>
        </>
      )}
    </div>
  );
}
