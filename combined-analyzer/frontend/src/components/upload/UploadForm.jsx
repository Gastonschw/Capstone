import React, { useState, useEffect, useCallback } from 'react';
import {
  uploadFolder,
  getGitHubAuthStatus,
  getGitHubRepos,
  importGitHubRepo,
  initiateGitHubAuth,
  logoutGitHub,
  setSessionId,
} from '../../api';

const styles = {
  container: {
    backgroundColor: '#fff',
    borderRadius: '12px',
    padding: '24px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
    maxWidth: '700px',
  },
  title: {
    margin: '0 0 20px 0',
    color: '#1e3a5f',
    fontSize: '20px',
  },
  tabs: {
    display: 'flex',
    gap: '4px',
    marginBottom: '24px',
    backgroundColor: '#f0f0f0',
    padding: '4px',
    borderRadius: '8px',
  },
  tab: {
    flex: 1,
    padding: '10px 16px',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: '500',
    transition: 'all 0.2s',
  },
  tabActive: {
    backgroundColor: '#fff',
    color: '#1e3a5f',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
  },
  tabInactive: {
    backgroundColor: 'transparent',
    color: '#666',
  },
  dropZone: {
    border: '2px dashed #ccc',
    borderRadius: '12px',
    padding: '50px 20px',
    textAlign: 'center',
    cursor: 'pointer',
    transition: 'all 0.2s',
    backgroundColor: '#fafafa',
  },
  dropZoneActive: {
    borderColor: '#1e3a5f',
    backgroundColor: '#f0f7ff',
  },
  dropZoneIcon: {
    fontSize: '48px',
    marginBottom: '16px',
  },
  dropZoneText: {
    fontSize: '16px',
    color: '#333',
    marginBottom: '8px',
  },
  dropZoneHint: {
    fontSize: '13px',
    color: '#666',
  },
  selectedFile: {
    backgroundColor: '#e7f3ff',
    padding: '12px 16px',
    borderRadius: '8px',
    marginTop: '16px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  removeButton: {
    background: 'none',
    border: 'none',
    color: '#dc3545',
    cursor: 'pointer',
    fontSize: '20px',
  },
  button: {
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
  buttonDisabled: {
    backgroundColor: '#ccc',
    cursor: 'not-allowed',
  },
  buttonGitHub: {
    backgroundColor: '#24292e',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '10px',
  },
  error: {
    color: '#dc3545',
    backgroundColor: '#f8d7da',
    padding: '12px',
    borderRadius: '8px',
    marginBottom: '16px',
    fontSize: '14px',
  },
  success: {
    color: '#155724',
    backgroundColor: '#d4edda',
    padding: '12px',
    borderRadius: '8px',
    marginBottom: '16px',
    fontSize: '14px',
  },
  authStatus: {
    padding: '12px 16px',
    backgroundColor: '#f8f9fa',
    borderRadius: '8px',
    marginBottom: '16px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  searchInput: {
    width: '100%',
    padding: '12px 16px',
    border: '1px solid #ddd',
    borderRadius: '8px',
    fontSize: '14px',
    marginBottom: '12px',
  },
  repoList: {
    maxHeight: '300px',
    overflowY: 'auto',
    border: '1px solid #ddd',
    borderRadius: '8px',
  },
  repoItem: {
    padding: '12px 16px',
    borderBottom: '1px solid #eee',
    cursor: 'pointer',
    transition: 'background 0.2s',
  },
  repoItemSelected: {
    backgroundColor: '#e7f3ff',
  },
  repoName: {
    fontWeight: '600',
    marginBottom: '4px',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  repoDescription: {
    fontSize: '13px',
    color: '#666',
  },
  privateBadge: {
    fontSize: '11px',
    padding: '2px 6px',
    backgroundColor: '#ffc107',
    borderRadius: '4px',
  },
  disconnectButton: {
    backgroundColor: '#6c757d',
    color: '#fff',
    border: 'none',
    padding: '8px 16px',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '13px',
  },
};

export default function UploadForm({ onRepositoryCreated, tamuApiKey = '' }) {
  const [activeTab, setActiveTab] = useState('folder');

  // Folder upload state
  const [zipFile, setZipFile] = useState(null);
  const [isDragActive, setIsDragActive] = useState(false);

  // GitHub state
  const [githubAuth, setGithubAuth] = useState({ authenticated: false, username: null });
  const [githubRepos, setGithubRepos] = useState([]);
  const [repoSearch, setRepoSearch] = useState('');
  const [selectedRepo, setSelectedRepo] = useState(null);
  const [loadingRepos, setLoadingRepos] = useState(false);

  // Common state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  useEffect(() => {
    checkGitHubAuth();

    const params = new URLSearchParams(window.location.search);
    // Store session_id from OAuth callback for cross-origin cookie fallback
    const sid = params.get('session_id');
    if (sid) {
      setSessionId(sid);
    }
    if (params.get('github_auth') === 'success') {
      setSuccess('Successfully connected to GitHub!');
      checkGitHubAuth();
    } else if (params.get('github_auth') === 'error') {
      setError(`GitHub authentication failed: ${params.get('message') || 'Unknown error'}`);
    }
  }, []);

  const checkGitHubAuth = async () => {
    try {
      const status = await getGitHubAuthStatus();
      setGithubAuth(status);
      if (status.authenticated) {
        loadGitHubRepos();
      }
    } catch (err) {
      console.error('Failed to check GitHub auth:', err);
    }
  };

  const loadGitHubRepos = async () => {
    setLoadingRepos(true);
    try {
      const repos = await getGitHubRepos();
      setGithubRepos(repos);
    } catch (err) {
      setError('Failed to load GitHub repositories');
    } finally {
      setLoadingRepos(false);
    }
  };

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragActive(false);
    const file = e.dataTransfer.files[0];
    if (file && file.name.endsWith('.zip')) {
      setZipFile(file);
      setError(null);
    } else {
      setError('Please drop a ZIP file');
    }
  }, []);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragActive(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragActive(false);
  }, []);

  const handleZipSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      setZipFile(file);
      setError(null);
    }
  };

  const handleFolderSubmit = async (e) => {
    e.preventDefault();
    if (!zipFile) {
      setError('Please select a ZIP file');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const repository = await uploadFolder(zipFile, null, tamuApiKey);
      setSuccess(`Repository "${repository.name}" uploaded successfully!`);
      setZipFile(null);
      onRepositoryCreated(repository);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to upload folder');
    } finally {
      setLoading(false);
    }
  };

  const handleGitHubConnect = () => {
    initiateGitHubAuth();
  };

  const handleGitHubLogout = async () => {
    try {
      await logoutGitHub();
      setGithubAuth({ authenticated: false, username: null });
      setGithubRepos([]);
      setSelectedRepo(null);
    } catch (err) {
      setError('Failed to logout from GitHub');
    }
  };

  const handleGitHubImport = async () => {
    if (!selectedRepo) {
      setError('Please select a repository');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const repository = await importGitHubRepo(selectedRepo.full_name, tamuApiKey);
      setSuccess(`Repository "${repository.name}" imported successfully!`);
      setSelectedRepo(null);
      onRepositoryCreated(repository);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to import repository');
    } finally {
      setLoading(false);
    }
  };

  const filteredRepos = githubRepos.filter(
    (repo) =>
      repo.full_name.toLowerCase().includes(repoSearch.toLowerCase()) ||
      (repo.description && repo.description.toLowerCase().includes(repoSearch.toLowerCase()))
  );

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>Add Repository</h2>

      <div style={styles.tabs}>
        <button
          style={{ ...styles.tab, ...(activeTab === 'folder' ? styles.tabActive : styles.tabInactive) }}
          onClick={() => { setActiveTab('folder'); setError(null); setSuccess(null); }}
        >
          Upload Folder
        </button>
        <button
          style={{ ...styles.tab, ...(activeTab === 'github' ? styles.tabActive : styles.tabInactive) }}
          onClick={() => { setActiveTab('github'); setError(null); setSuccess(null); }}
        >
          GitHub
        </button>
      </div>

      {error && <div style={styles.error}>{error}</div>}
      {success && <div style={styles.success}>{success}</div>}

      {activeTab === 'folder' && (
        <form onSubmit={handleFolderSubmit}>
          <div
            style={{
              ...styles.dropZone,
              ...(isDragActive ? styles.dropZoneActive : {}),
            }}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onClick={() => document.getElementById('zip-input').click()}
          >
            <div style={styles.dropZoneIcon}>&#128193;</div>
            <div style={styles.dropZoneText}>
              {zipFile ? zipFile.name : 'Drop your ZIP file here or click to browse'}
            </div>
            <div style={styles.dropZoneHint}>
              ZIP file containing your project with code, ERD diagrams, and user stories
            </div>
            <input
              id="zip-input"
              type="file"
              accept=".zip"
              onChange={handleZipSelect}
              style={{ display: 'none' }}
            />
          </div>

          {zipFile && (
            <div style={styles.selectedFile}>
              <span>
                {zipFile.name} ({(zipFile.size / 1024 / 1024).toFixed(2)} MB)
              </span>
              <button type="button" style={styles.removeButton} onClick={() => setZipFile(null)}>
                &#10005;
              </button>
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !zipFile}
            style={{
              ...styles.button,
              ...(loading || !zipFile ? styles.buttonDisabled : {}),
            }}
          >
            {loading ? 'Uploading...' : 'Upload & Scan Repository'}
          </button>
        </form>
      )}

      {activeTab === 'github' && (
        <div>
          {!githubAuth.authenticated ? (
            <div>
              <p style={{ marginBottom: '16px', color: '#666' }}>
                Connect your GitHub account to import repositories directly.
              </p>
              <button style={{ ...styles.button, ...styles.buttonGitHub }} onClick={handleGitHubConnect}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
                </svg>
                Connect GitHub Account
              </button>
            </div>
          ) : (
            <div>
              <div style={styles.authStatus}>
                <span>
                  Connected as <strong>{githubAuth.username}</strong>
                </span>
                <button style={styles.disconnectButton} onClick={handleGitHubLogout}>
                  Disconnect
                </button>
              </div>

              <input
                type="text"
                placeholder="Search repositories..."
                value={repoSearch}
                onChange={(e) => setRepoSearch(e.target.value)}
                style={styles.searchInput}
              />

              {loadingRepos ? (
                <p style={{ textAlign: 'center', color: '#666', padding: '20px' }}>
                  Loading repositories...
                </p>
              ) : (
                <div style={styles.repoList}>
                  {filteredRepos.map((repo) => (
                    <div
                      key={repo.full_name}
                      style={{
                        ...styles.repoItem,
                        ...(selectedRepo?.full_name === repo.full_name ? styles.repoItemSelected : {}),
                      }}
                      onClick={() => setSelectedRepo(repo)}
                    >
                      <div style={styles.repoName}>
                        {repo.full_name}
                        {repo.private && <span style={styles.privateBadge}>Private</span>}
                      </div>
                      {repo.description && <div style={styles.repoDescription}>{repo.description}</div>}
                    </div>
                  ))}
                  {filteredRepos.length === 0 && (
                    <p style={{ padding: '20px', textAlign: 'center', color: '#666' }}>
                      No repositories found
                    </p>
                  )}
                </div>
              )}

              <button
                onClick={handleGitHubImport}
                disabled={loading || !selectedRepo}
                style={{
                  ...styles.button,
                  ...(loading || !selectedRepo ? styles.buttonDisabled : {}),
                }}
              >
                {loading ? 'Importing...' : 'Import Repository'}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
