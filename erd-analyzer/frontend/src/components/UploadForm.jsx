import React, { useState, useEffect, useCallback } from 'react';
import { 
  submitAnalysis, 
  uploadFolder, 
  getGitHubAuthStatus, 
  getGitHubRepos, 
  importGitHubRepo,
  initiateGitHubAuth,
  logoutGitHub
} from '../api';

const styles = {
  container: {
    backgroundColor: '#fff',
    borderRadius: '8px',
    padding: '24px',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
  },
  title: {
    margin: '0 0 20px 0',
    color: '#333',
  },
  tabs: {
    display: 'flex',
    borderBottom: '2px solid #e9ecef',
    marginBottom: '24px',
  },
  tab: {
    padding: '12px 24px',
    cursor: 'pointer',
    border: 'none',
    background: 'none',
    fontSize: '14px',
    fontWeight: '500',
    color: '#666',
    borderBottom: '2px solid transparent',
    marginBottom: '-2px',
    transition: 'all 0.2s',
  },
  tabActive: {
    color: '#007bff',
    borderBottomColor: '#007bff',
  },
  formGroup: {
    marginBottom: '20px',
  },
  label: {
    display: 'block',
    marginBottom: '8px',
    fontWeight: '600',
    color: '#555',
  },
  dropZone: {
    border: '2px dashed #ccc',
    borderRadius: '8px',
    padding: '40px 20px',
    textAlign: 'center',
    cursor: 'pointer',
    transition: 'all 0.2s',
    backgroundColor: '#fafafa',
  },
  dropZoneActive: {
    borderColor: '#007bff',
    backgroundColor: '#f0f7ff',
  },
  dropZoneIcon: {
    fontSize: '48px',
    marginBottom: '12px',
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
  fileInput: {
    display: 'block',
    width: '100%',
    padding: '10px',
    border: '2px dashed #ccc',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  textarea: {
    width: '100%',
    minHeight: '200px',
    padding: '12px',
    border: '1px solid #ccc',
    borderRadius: '4px',
    fontFamily: 'inherit',
    fontSize: '14px',
    resize: 'vertical',
    boxSizing: 'border-box',
  },
  button: {
    backgroundColor: '#007bff',
    color: '#fff',
    border: 'none',
    padding: '12px 24px',
    borderRadius: '4px',
    fontSize: '16px',
    cursor: 'pointer',
    width: '100%',
  },
  buttonSecondary: {
    backgroundColor: '#6c757d',
    color: '#fff',
    border: 'none',
    padding: '10px 20px',
    borderRadius: '4px',
    fontSize: '14px',
    cursor: 'pointer',
  },
  buttonGitHub: {
    backgroundColor: '#24292e',
    color: '#fff',
    border: 'none',
    padding: '12px 24px',
    borderRadius: '4px',
    fontSize: '16px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '10px',
    width: '100%',
  },
  buttonDisabled: {
    backgroundColor: '#ccc',
    cursor: 'not-allowed',
  },
  preview: {
    maxWidth: '100%',
    maxHeight: '200px',
    marginTop: '10px',
    borderRadius: '4px',
  },
  error: {
    color: '#dc3545',
    marginTop: '10px',
    padding: '10px',
    backgroundColor: '#f8d7da',
    borderRadius: '4px',
  },
  success: {
    color: '#155724',
    marginTop: '10px',
    padding: '10px',
    backgroundColor: '#d4edda',
    borderRadius: '4px',
  },
  hint: {
    fontSize: '12px',
    color: '#666',
    marginTop: '4px',
  },
  repoList: {
    maxHeight: '300px',
    overflowY: 'auto',
    border: '1px solid #ddd',
    borderRadius: '4px',
    marginTop: '12px',
  },
  repoItem: {
    padding: '12px 16px',
    borderBottom: '1px solid #eee',
    cursor: 'pointer',
    transition: 'background 0.2s',
  },
  repoItemHover: {
    backgroundColor: '#f8f9fa',
  },
  repoName: {
    fontWeight: '600',
    marginBottom: '4px',
  },
  repoDescription: {
    fontSize: '13px',
    color: '#666',
  },
  repoPrivate: {
    fontSize: '11px',
    padding: '2px 6px',
    backgroundColor: '#ffc107',
    borderRadius: '3px',
    marginLeft: '8px',
  },
  selectedFile: {
    backgroundColor: '#e7f3ff',
    padding: '12px',
    borderRadius: '4px',
    marginTop: '12px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  removeButton: {
    background: 'none',
    border: 'none',
    color: '#dc3545',
    cursor: 'pointer',
    fontSize: '18px',
  },
  authStatus: {
    padding: '12px',
    backgroundColor: '#f8f9fa',
    borderRadius: '4px',
    marginBottom: '16px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  authUser: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  searchInput: {
    width: '100%',
    padding: '10px 12px',
    border: '1px solid #ccc',
    borderRadius: '4px',
    fontSize: '14px',
    marginBottom: '12px',
  },
};

export default function UploadForm({ onAnalysisStarted, onRepositoryCreated }) {
  const [activeTab, setActiveTab] = useState('folder'); // 'single', 'folder', 'github'
  
  // Single file upload state
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [userStories, setUserStories] = useState('');
  
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

  // Check GitHub auth status on mount and after OAuth redirect
  useEffect(() => {
    checkGitHubAuth();
    
    // Check for OAuth callback
    const params = new URLSearchParams(window.location.search);
    if (params.get('github_auth') === 'success') {
      setSuccess('Successfully connected to GitHub!');
      checkGitHubAuth();
      // Clean up URL
      window.history.replaceState({}, '', window.location.pathname);
    } else if (params.get('github_auth') === 'error') {
      setError(`GitHub authentication failed: ${params.get('message') || 'Unknown error'}`);
      window.history.replaceState({}, '', window.location.pathname);
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

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setImageFile(file);
      const reader = new FileReader();
      reader.onload = (e) => setImagePreview(e.target.result);
      reader.readAsDataURL(file);
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

  const handleSingleFileSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!imageFile) {
      setError('Please select an ERD image');
      return;
    }

    if (!userStories.trim()) {
      setError('Please enter user stories');
      return;
    }

    setLoading(true);

    try {
      const analysis = await submitAnalysis(imageFile, userStories);
      onAnalysisStarted(analysis);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to submit analysis');
    } finally {
      setLoading(false);
    }
  };

  const handleFolderSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!zipFile) {
      setError('Please select a ZIP file');
      return;
    }

    setLoading(true);

    try {
      const repository = await uploadFolder(zipFile);
      setSuccess(`Repository "${repository.name}" uploaded successfully! Scanning for files...`);
      setZipFile(null);
      if (onRepositoryCreated) {
        onRepositoryCreated(repository);
      }
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
      const repository = await importGitHubRepo(selectedRepo.full_name);
      setSuccess(`Repository "${repository.name}" imported successfully! Scanning for files...`);
      setSelectedRepo(null);
      if (onRepositoryCreated) {
        onRepositoryCreated(repository);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to import repository');
    } finally {
      setLoading(false);
    }
  };

  const filteredRepos = githubRepos.filter(repo => 
    repo.full_name.toLowerCase().includes(repoSearch.toLowerCase()) ||
    (repo.description && repo.description.toLowerCase().includes(repoSearch.toLowerCase()))
  );

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>Start ERD Analysis</h2>

      {/* Tabs */}
      <div style={styles.tabs}>
        <button
          style={{ ...styles.tab, ...(activeTab === 'folder' ? styles.tabActive : {}) }}
          onClick={() => { setActiveTab('folder'); setError(null); setSuccess(null); }}
        >
          Upload Folder
        </button>
        <button
          style={{ ...styles.tab, ...(activeTab === 'github' ? styles.tabActive : {}) }}
          onClick={() => { setActiveTab('github'); setError(null); setSuccess(null); }}
        >
          GitHub
        </button>
        <button
          style={{ ...styles.tab, ...(activeTab === 'single' ? styles.tabActive : {}) }}
          onClick={() => { setActiveTab('single'); setError(null); setSuccess(null); }}
        >
          Single File
        </button>
      </div>

      {error && <p style={styles.error}>{error}</p>}
      {success && <p style={styles.success}>{success}</p>}

      {/* Single File Upload Tab */}
      {activeTab === 'single' && (
        <form onSubmit={handleSingleFileSubmit}>
          <div style={styles.formGroup}>
            <label style={styles.label}>ERD Image</label>
            <input
              type="file"
              accept=".png,.jpg,.jpeg,.gif,.webp"
              onChange={handleImageChange}
              style={styles.fileInput}
            />
            <p style={styles.hint}>Supported formats: PNG, JPG, GIF, WebP</p>
            {imagePreview && (
              <img src={imagePreview} alt="ERD Preview" style={styles.preview} />
            )}
          </div>

          <div style={styles.formGroup}>
            <label style={styles.label}>User Stories</label>
            <textarea
              value={userStories}
              onChange={(e) => setUserStories(e.target.value)}
              placeholder="Enter your user stories here, one per line...

Example:
As a user, I want to create an account so I can save my preferences.
As a user, I want to add items to my cart so I can purchase them later.
As an admin, I want to view all orders so I can manage fulfillment."
              style={styles.textarea}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{
              ...styles.button,
              ...(loading ? styles.buttonDisabled : {}),
            }}
          >
            {loading ? 'Submitting...' : 'Analyze ERD'}
          </button>
        </form>
      )}

      {/* Folder Upload Tab */}
      {activeTab === 'folder' && (
        <form onSubmit={handleFolderSubmit}>
          <div style={styles.formGroup}>
            <label style={styles.label}>Project Folder (ZIP)</label>
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
              <div style={styles.dropZoneIcon}>📁</div>
              <div style={styles.dropZoneText}>
                {zipFile ? zipFile.name : 'Drop your ZIP file here or click to browse'}
              </div>
              <div style={styles.dropZoneHint}>
                ZIP file containing your project with ERD diagrams and user stories
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
                <span>Selected: {zipFile.name} ({(zipFile.size / 1024 / 1024).toFixed(2)} MB)</span>
                <button
                  type="button"
                  style={styles.removeButton}
                  onClick={() => setZipFile(null)}
                >
                  ×
                </button>
              </div>
            )}
          </div>

          <p style={styles.hint}>
            The system will automatically scan your repository for ERD diagram images 
            and user story files (markdown, text, feature files, etc.)
          </p>

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

      {/* GitHub Tab */}
      {activeTab === 'github' && (
        <div>
          {!githubAuth.authenticated ? (
            <div>
              <p style={{ marginBottom: '16px', color: '#666' }}>
                Connect your GitHub account to import repositories directly.
              </p>
              <button
                style={styles.buttonGitHub}
                onClick={handleGitHubConnect}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
                </svg>
                Connect GitHub Account
              </button>
            </div>
          ) : (
            <div>
              <div style={styles.authStatus}>
                <div style={styles.authUser}>
                  <span style={{ fontSize: '20px' }}>👤</span>
                  <span>Connected as <strong>{githubAuth.username}</strong></span>
                </div>
                <button
                  style={styles.buttonSecondary}
                  onClick={handleGitHubLogout}
                >
                  Disconnect
                </button>
              </div>

              <div style={styles.formGroup}>
                <label style={styles.label}>Select Repository</label>
                <input
                  type="text"
                  placeholder="Search repositories..."
                  value={repoSearch}
                  onChange={(e) => setRepoSearch(e.target.value)}
                  style={styles.searchInput}
                />
                
                {loadingRepos ? (
                  <p style={{ textAlign: 'center', color: '#666' }}>Loading repositories...</p>
                ) : (
                  <div style={styles.repoList}>
                    {filteredRepos.map((repo) => (
                      <div
                        key={repo.full_name}
                        style={{
                          ...styles.repoItem,
                          backgroundColor: selectedRepo?.full_name === repo.full_name ? '#e7f3ff' : 'transparent',
                        }}
                        onClick={() => setSelectedRepo(repo)}
                      >
                        <div style={styles.repoName}>
                          {repo.full_name}
                          {repo.private && <span style={styles.repoPrivate}>Private</span>}
                        </div>
                        {repo.description && (
                          <div style={styles.repoDescription}>{repo.description}</div>
                        )}
                      </div>
                    ))}
                    {filteredRepos.length === 0 && (
                      <p style={{ padding: '20px', textAlign: 'center', color: '#666' }}>
                        No repositories found
                      </p>
                    )}
                  </div>
                )}
              </div>

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
