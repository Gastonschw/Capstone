import React, { useState, useEffect } from 'react';
import UploadForm from './components/UploadForm';
import RepositoryBrowser from './components/RepositoryBrowser';
import ReportView from './components/ReportView';
import { listRepositories } from './api';

const styles = {
  container: {
    maxWidth: '1400px',
    margin: '0 auto',
    padding: '20px',
  },
  header: {
    background: 'linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%)',
    color: 'white',
    padding: '30px',
    borderRadius: '12px',
    marginBottom: '30px',
    boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
  },
  title: {
    fontSize: '2.5rem',
    fontWeight: '700',
    marginBottom: '10px',
  },
  subtitle: {
    fontSize: '1.1rem',
    opacity: '0.9',
  },
  mainContent: {
    display: 'grid',
    gridTemplateColumns: '350px 1fr',
    gap: '30px',
    alignItems: 'start',
  },
  sidebar: {
    background: 'white',
    borderRadius: '12px',
    padding: '20px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
  },
  sidebarTitle: {
    fontSize: '1.2rem',
    fontWeight: '600',
    marginBottom: '15px',
    color: '#1e3a5f',
  },
  repoList: {
    listStyle: 'none',
  },
  repoItem: {
    padding: '12px 15px',
    borderRadius: '8px',
    marginBottom: '8px',
    cursor: 'pointer',
    transition: 'all 0.2s',
    border: '1px solid #e0e0e0',
  },
  repoItemActive: {
    background: '#e3f2fd',
    borderColor: '#2196f3',
  },
  repoName: {
    fontWeight: '500',
    marginBottom: '4px',
  },
  repoMeta: {
    fontSize: '0.85rem',
    color: '#666',
  },
  badge: {
    display: 'inline-block',
    padding: '2px 8px',
    borderRadius: '12px',
    fontSize: '0.75rem',
    fontWeight: '500',
    marginLeft: '8px',
  },
  badgeGithub: {
    background: '#24292e',
    color: 'white',
  },
  badgeUpload: {
    background: '#4caf50',
    color: 'white',
  },
  content: {
    background: 'white',
    borderRadius: '12px',
    padding: '25px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
    minHeight: '600px',
  },
  emptyState: {
    textAlign: 'center',
    padding: '60px 20px',
    color: '#666',
  },
  emptyIcon: {
    fontSize: '4rem',
    marginBottom: '20px',
  },
};

function App() {
  const [view, setView] = useState('upload'); // 'upload', 'repository', 'report'
  const [repositories, setRepositories] = useState([]);
  const [selectedRepo, setSelectedRepo] = useState(null);
  const [selectedAnalysis, setSelectedAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchRepositories();

    // Check for GitHub callback
    const params = new URLSearchParams(window.location.search);
    if (params.get('github_success')) {
      window.history.replaceState({}, '', window.location.pathname);
    }
    if (params.get('github_error')) {
      alert('GitHub authentication failed: ' + params.get('github_error'));
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, []);

  const fetchRepositories = async () => {
    try {
      const response = await listRepositories();
      setRepositories(response.data);
    } catch (error) {
      console.error('Error fetching repositories:', error);
    }
  };

  const handleRepoCreated = (repoId) => {
    fetchRepositories();
    setSelectedRepo(repoId);
    setView('repository');
  };

  const handleRepoSelect = (repo) => {
    setSelectedRepo(repo.id);
    setSelectedAnalysis(null);
    setView('repository');
  };

  const handleAnalysisSelect = (analysisId) => {
    setSelectedAnalysis(analysisId);
    setView('report');
  };

  const handleBack = () => {
    if (view === 'report') {
      setView('repository');
      setSelectedAnalysis(null);
    } else if (view === 'repository') {
      setView('upload');
      setSelectedRepo(null);
    }
  };

  const handleRepoDeleted = () => {
    fetchRepositories();
    setSelectedRepo(null);
    setView('upload');
  };

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <h1 style={styles.title}>Integrity Analyzer</h1>
        <p style={styles.subtitle}>
          Analyze your codebase for security integrity characteristics: Confidentiality,
          Data Integrity, Authenticity, Non-Repudiation, Accountability, and Attack Resistance
        </p>
      </header>

      <div style={styles.mainContent}>
        <aside style={styles.sidebar}>
          <h2 style={styles.sidebarTitle}>Repositories</h2>

          <button
            onClick={() => { setView('upload'); setSelectedRepo(null); setSelectedAnalysis(null); }}
            style={{
              width: '100%',
              padding: '12px',
              background: '#1e3a5f',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: '500',
              marginBottom: '15px',
            }}
          >
            + Add Repository
          </button>

          <ul style={styles.repoList}>
            {repositories.map((repo) => (
              <li
                key={repo.id}
                style={{
                  ...styles.repoItem,
                  ...(selectedRepo === repo.id ? styles.repoItemActive : {}),
                }}
                onClick={() => handleRepoSelect(repo)}
              >
                <div style={styles.repoName}>
                  {repo.name}
                  <span style={{
                    ...styles.badge,
                    ...(repo.source_type === 'github' ? styles.badgeGithub : styles.badgeUpload),
                  }}>
                    {repo.source_type === 'github' ? 'GitHub' : 'Upload'}
                  </span>
                </div>
                <div style={styles.repoMeta}>
                  {repo.file_count} files • {repo.analysis_count} analyses
                </div>
              </li>
            ))}
          </ul>

          {repositories.length === 0 && (
            <p style={{ color: '#999', textAlign: 'center', padding: '20px' }}>
              No repositories yet
            </p>
          )}
        </aside>

        <main style={styles.content}>
          {view === 'upload' && (
            <UploadForm onRepoCreated={handleRepoCreated} />
          )}

          {view === 'repository' && selectedRepo && (
            <RepositoryBrowser
              repositoryId={selectedRepo}
              onAnalysisSelect={handleAnalysisSelect}
              onBack={handleBack}
              onDeleted={handleRepoDeleted}
            />
          )}

          {view === 'report' && selectedAnalysis && (
            <ReportView
              analysisId={selectedAnalysis}
              onBack={handleBack}
            />
          )}

          {view === 'upload' && repositories.length === 0 && (
            <div style={styles.emptyState}>
              <div style={styles.emptyIcon}>📊</div>
              <h3>Welcome to Integrity Analyzer</h3>
              <p>Upload a codebase or connect to GitHub to get started</p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
