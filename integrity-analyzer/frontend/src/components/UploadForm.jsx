import React, { useState, useEffect } from 'react';
import { uploadFolder, getGitHubStatus, listGitHubRepos, importGitHubRepo, logoutGitHub } from '../api';

const styles = {
  container: {
    padding: '20px',
  },
  tabs: {
    display: 'flex',
    gap: '10px',
    marginBottom: '25px',
    borderBottom: '2px solid #e0e0e0',
    paddingBottom: '15px',
  },
  tab: {
    padding: '12px 24px',
    border: 'none',
    background: 'transparent',
    cursor: 'pointer',
    fontSize: '1rem',
    fontWeight: '500',
    color: '#666',
    borderRadius: '8px',
    transition: 'all 0.2s',
  },
  tabActive: {
    background: '#1e3a5f',
    color: 'white',
  },
  section: {
    marginBottom: '30px',
  },
  sectionTitle: {
    fontSize: '1.3rem',
    fontWeight: '600',
    marginBottom: '15px',
    color: '#1e3a5f',
  },
  dropzone: {
    border: '3px dashed #ccc',
    borderRadius: '12px',
    padding: '60px 40px',
    textAlign: 'center',
    cursor: 'pointer',
    transition: 'all 0.2s',
    background: '#fafafa',
  },
  dropzoneActive: {
    borderColor: '#2196f3',
    background: '#e3f2fd',
  },
  dropzoneIcon: {
    fontSize: '4rem',
    marginBottom: '15px',
  },
  button: {
    padding: '12px 24px',
    background: '#1e3a5f',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '1rem',
    fontWeight: '500',
    transition: 'background 0.2s',
  },
  buttonDisabled: {
    background: '#ccc',
    cursor: 'not-allowed',
  },
  buttonSecondary: {
    background: '#e0e0e0',
    color: '#333',
  },
  githubButton: {
    background: '#24292e',
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    justifyContent: 'center',
  },
  repoList: {
    maxHeight: '400px',
    overflowY: 'auto',
    border: '1px solid #e0e0e0',
    borderRadius: '8px',
  },
  repoItem: {
    padding: '15px',
    borderBottom: '1px solid #e0e0e0',
    cursor: 'pointer',
    transition: 'background 0.2s',
  },
  repoItemHover: {
    background: '#f5f5f5',
  },
  repoName: {
    fontWeight: '500',
    marginBottom: '5px',
  },
  repoDescription: {
    fontSize: '0.9rem',
    color: '#666',
  },
  privateBadge: {
    display: 'inline-block',
    padding: '2px 8px',
    background: '#ffc107',
    color: '#333',
    borderRadius: '12px',
    fontSize: '0.75rem',
    marginLeft: '10px',
  },
  message: {
    padding: '15px',
    borderRadius: '8px',
    marginTop: '15px',
  },
  success: {
    background: '#e8f5e9',
    color: '#2e7d32',
  },
  error: {
    background: '#ffebee',
    color: '#c62828',
  },
  loading: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '40px',
    color: '#666',
  },
  spinner: {
    width: '30px',
    height: '30px',
    border: '3px solid #e0e0e0',
    borderTop: '3px solid #1e3a5f',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
    marginRight: '15px',
  },
  userInfo: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '15px',
    background: '#f5f5f5',
    borderRadius: '8px',
    marginBottom: '20px',
  },
};

function UploadForm({ onRepoCreated }) {
  const [activeTab, setActiveTab] = useState('upload');
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState(null);

  // GitHub state
  const [githubStatus, setGithubStatus] = useState({ authenticated: false });
  const [githubRepos, setGithubRepos] = useState([]);
  const [loadingRepos, setLoadingRepos] = useState(false);
  const [importing, setImporting] = useState(false);

  useEffect(() => {
    checkGitHubStatus();
  }, []);

  const checkGitHubStatus = async () => {
    try {
      const response = await getGitHubStatus();
      setGithubStatus(response.data);
      if (response.data.authenticated) {
        fetchGitHubRepos();
      }
    } catch (error) {
      console.error('Error checking GitHub status:', error);
    }
  };

  const fetchGitHubRepos = async () => {
    setLoadingRepos(true);
    try {
      const response = await listGitHubRepos();
      setGithubRepos(response.data);
    } catch (error) {
      console.error('Error fetching repos:', error);
      setMessage({ type: 'error', text: 'Failed to fetch repositories' });
    } finally {
      setLoadingRepos(false);
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      await handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = async (e) => {
    if (e.target.files && e.target.files[0]) {
      await handleFileUpload(e.target.files[0]);
    }
  };

  const handleFileUpload = async (file) => {
    if (!file.name.endsWith('.zip')) {
      setMessage({ type: 'error', text: 'Please upload a ZIP file' });
      return;
    }

    if (file.size > 100 * 1024 * 1024) {
      setMessage({ type: 'error', text: 'File size must be less than 100MB' });
      return;
    }

    setUploading(true);
    setMessage(null);

    try {
      const response = await uploadFolder(file);
      setMessage({ type: 'success', text: 'Upload successful! Discovering files...' });
      setTimeout(() => {
        onRepoCreated(response.data.repository_id);
      }, 1500);
    } catch (error) {
      setMessage({ type: 'error', text: error.response?.data?.detail || 'Upload failed' });
    } finally {
      setUploading(false);
    }
  };

  const handleGitHubLogin = () => {
    window.location.href = '/api/github/auth';
  };

  const handleGitHubLogout = async () => {
    try {
      await logoutGitHub();
      setGithubStatus({ authenticated: false });
      setGithubRepos([]);
    } catch (error) {
      console.error('Error logging out:', error);
    }
  };

  const handleImportRepo = async (repoFullName) => {
    setImporting(true);
    setMessage(null);

    try {
      const response = await importGitHubRepo(repoFullName);
      setMessage({ type: 'success', text: 'Import successful! Discovering files...' });
      setTimeout(() => {
        onRepoCreated(response.data.repository_id);
      }, 1500);
    } catch (error) {
      setMessage({ type: 'error', text: error.response?.data?.detail || 'Import failed' });
    } finally {
      setImporting(false);
    }
  };

  return (
    <div style={styles.container}>
      <style>
        {`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}
      </style>

      <div style={styles.tabs}>
        <button
          style={{ ...styles.tab, ...(activeTab === 'upload' ? styles.tabActive : {}) }}
          onClick={() => setActiveTab('upload')}
        >
          Upload ZIP
        </button>
        <button
          style={{ ...styles.tab, ...(activeTab === 'github' ? styles.tabActive : {}) }}
          onClick={() => setActiveTab('github')}
        >
          GitHub
        </button>
      </div>

      {activeTab === 'upload' && (
        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>Upload Codebase</h3>
          <p style={{ marginBottom: '20px', color: '#666' }}>
            Upload a ZIP file containing your project's source code for integrity analysis.
          </p>

          <div
            style={{ ...styles.dropzone, ...(dragActive ? styles.dropzoneActive : {}) }}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => document.getElementById('fileInput').click()}
          >
            <div style={styles.dropzoneIcon}>📁</div>
            <p style={{ fontSize: '1.1rem', marginBottom: '10px' }}>
              Drag and drop your ZIP file here
            </p>
            <p style={{ color: '#999' }}>or click to browse</p>
            <input
              id="fileInput"
              type="file"
              accept=".zip"
              onChange={handleFileChange}
              style={{ display: 'none' }}
            />
          </div>

          {uploading && (
            <div style={styles.loading}>
              <div style={styles.spinner}></div>
              Uploading and processing...
            </div>
          )}
        </div>
      )}

      {activeTab === 'github' && (
        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>Import from GitHub</h3>

          {!githubStatus.authenticated ? (
            <div style={{ textAlign: 'center', padding: '40px' }}>
              <p style={{ marginBottom: '20px', color: '#666' }}>
                Connect your GitHub account to import repositories for analysis.
              </p>
              <button
                style={{ ...styles.button, ...styles.githubButton }}
                onClick={handleGitHubLogin}
              >
                <svg height="20" viewBox="0 0 16 16" width="20" fill="currentColor">
                  <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
                </svg>
                Connect to GitHub
              </button>
            </div>
          ) : (
            <>
              <div style={styles.userInfo}>
                <span>Connected as <strong>{githubStatus.username}</strong></span>
                <button
                  style={{ ...styles.button, ...styles.buttonSecondary, padding: '8px 16px' }}
                  onClick={handleGitHubLogout}
                >
                  Disconnect
                </button>
              </div>

              {loadingRepos ? (
                <div style={styles.loading}>
                  <div style={styles.spinner}></div>
                  Loading repositories...
                </div>
              ) : (
                <div style={styles.repoList}>
                  {githubRepos.map((repo) => (
                    <div
                      key={repo.id}
                      style={styles.repoItem}
                      onClick={() => !importing && handleImportRepo(repo.full_name)}
                    >
                      <div style={styles.repoName}>
                        {repo.name}
                        {repo.private && <span style={styles.privateBadge}>Private</span>}
                      </div>
                      {repo.description && (
                        <div style={styles.repoDescription}>{repo.description}</div>
                      )}
                    </div>
                  ))}
                  {githubRepos.length === 0 && (
                    <div style={{ padding: '40px', textAlign: 'center', color: '#999' }}>
                      No repositories found
                    </div>
                  )}
                </div>
              )}

              {importing && (
                <div style={styles.loading}>
                  <div style={styles.spinner}></div>
                  Importing repository...
                </div>
              )}
            </>
          )}
        </div>
      )}

      {message && (
        <div style={{ ...styles.message, ...(message.type === 'success' ? styles.success : styles.error) }}>
          {message.text}
        </div>
      )}
    </div>
  );
}

export default UploadForm;
