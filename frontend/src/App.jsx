import React, { useState, useEffect } from 'react';
import UploadForm from './components/UploadForm';
import ReportView from './components/ReportView';
import RepositoryBrowser from './components/RepositoryBrowser';
import { pollAnalysis, listAnalyses, getAnalysis, listRepositories } from './api';

const styles = {
  app: {
    minHeight: '100vh',
    backgroundColor: '#f5f5f5',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  header: {
    backgroundColor: '#007bff',
    color: '#fff',
    padding: '20px',
    textAlign: 'center',
  },
  headerTitle: {
    margin: 0,
    fontSize: '28px',
  },
  headerSubtitle: {
    margin: '8px 0 0 0',
    opacity: 0.9,
    fontSize: '16px',
  },
  main: {
    maxWidth: '1000px',
    margin: '0 auto',
    padding: '24px',
  },
  history: {
    marginTop: '24px',
    backgroundColor: '#fff',
    borderRadius: '8px',
    padding: '16px',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
  },
  historyTitle: {
    margin: '0 0 12px 0',
    fontSize: '18px',
  },
  historyItem: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '8px 12px',
    borderBottom: '1px solid #eee',
    cursor: 'pointer',
  },
  historyItemHover: {
    backgroundColor: '#f8f9fa',
  },
  statusDot: {
    width: '10px',
    height: '10px',
    borderRadius: '50%',
    display: 'inline-block',
    marginRight: '8px',
  },
  repoList: {
    marginTop: '24px',
    backgroundColor: '#fff',
    borderRadius: '8px',
    padding: '16px',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
  },
  repoItem: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px',
    borderBottom: '1px solid #eee',
    cursor: 'pointer',
    transition: 'background 0.2s',
  },
  repoInfo: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  repoIcon: {
    fontSize: '24px',
  },
  repoName: {
    fontWeight: '500',
  },
  repoSource: {
    fontSize: '12px',
    color: '#666',
  },
  sourceBadge: {
    fontSize: '11px',
    padding: '2px 6px',
    borderRadius: '3px',
    marginLeft: '8px',
  },
  sourceGitHub: {
    backgroundColor: '#24292e',
    color: '#fff',
  },
  sourceFolder: {
    backgroundColor: '#6c757d',
    color: '#fff',
  },
};

const statusColors = {
  pending: '#ffc107',
  processing: '#007bff',
  completed: '#28a745',
  failed: '#dc3545',
};

export default function App() {
  const [currentAnalysis, setCurrentAnalysis] = useState(null);
  const [currentRepository, setCurrentRepository] = useState(null);
  const [history, setHistory] = useState([]);
  const [repositories, setRepositories] = useState([]);
  const [view, setView] = useState('upload'); // 'upload', 'repository', or 'report'

  useEffect(() => {
    loadHistory();
    loadRepositories();
  }, []);

  const loadHistory = async () => {
    try {
      const analyses = await listAnalyses();
      setHistory(analyses);
    } catch (err) {
      console.error('Failed to load history:', err);
    }
  };

  const loadRepositories = async () => {
    try {
      const repos = await listRepositories();
      setRepositories(repos);
    } catch (err) {
      console.error('Failed to load repositories:', err);
    }
  };

  const handleAnalysisStarted = (analysis) => {
    setCurrentAnalysis(analysis);
    setView('report');
    loadHistory();

    // If still processing, start polling for updates
    if (analysis.status === 'pending' || analysis.status === 'processing') {
      pollAnalysis(analysis.id, (updatedAnalysis) => {
        setCurrentAnalysis(updatedAnalysis);
        if (updatedAnalysis.status === 'completed' || updatedAnalysis.status === 'failed') {
          loadHistory();
        }
      });
    }
  };

  const handleRepositoryCreated = (repository) => {
    loadRepositories();
    setCurrentRepository(repository);
    setView('repository');
  };

  const handleRepositoryClick = (repository) => {
    setCurrentRepository(repository);
    setView('repository');
  };

  const handleHistoryClick = async (analysisId) => {
    try {
      const analysis = await getAnalysis(analysisId);
      setCurrentAnalysis(analysis);
      setView('report');

      // If still processing, start polling
      if (analysis.status === 'pending' || analysis.status === 'processing') {
        pollAnalysis(analysis.id, (updatedAnalysis) => {
          setCurrentAnalysis(updatedAnalysis);
        });
      }
    } catch (err) {
      console.error('Failed to load analysis:', err);
    }
  };

  const handleBack = () => {
    setCurrentAnalysis(null);
    setCurrentRepository(null);
    setView('upload');
    loadHistory();
    loadRepositories();
  };

  return (
    <div style={styles.app}>
      <header style={styles.header}>
        <h1 style={styles.headerTitle}>ERD Analysis Tool</h1>
        <p style={styles.headerSubtitle}>
          Upload a project folder or connect GitHub to analyze ERD coverage
        </p>
      </header>

      <main style={styles.main}>
        {view === 'upload' && (
          <>
            <UploadForm 
              onAnalysisStarted={handleAnalysisStarted}
              onRepositoryCreated={handleRepositoryCreated}
            />

            {/* Repositories List */}
            {repositories.length > 0 && (
              <div style={styles.repoList}>
                <h3 style={styles.historyTitle}>Your Repositories</h3>
                {repositories.slice(0, 10).map((repo) => (
                  <div
                    key={repo.id}
                    style={styles.repoItem}
                    onClick={() => handleRepositoryClick(repo)}
                  >
                    <div style={styles.repoInfo}>
                      <span style={styles.repoIcon}>
                        {repo.source_type === 'github' ? '🔗' : '📁'}
                      </span>
                      <div>
                        <div style={styles.repoName}>
                          {repo.name}
                          <span style={{
                            ...styles.sourceBadge,
                            ...(repo.source_type === 'github' ? styles.sourceGitHub : styles.sourceFolder)
                          }}>
                            {repo.source_type === 'github' ? 'GitHub' : 'Uploaded'}
                          </span>
                        </div>
                        <div style={styles.repoSource}>
                          {new Date(repo.created_at).toLocaleString()}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Analysis History */}
            {history.length > 0 && (
              <div style={styles.history}>
                <h3 style={styles.historyTitle}>Recent Analyses</h3>
                {history.slice(0, 5).map((item) => (
                  <div
                    key={item.id}
                    style={styles.historyItem}
                    onClick={() => handleHistoryClick(item.id)}
                  >
                    <span>
                      <span
                        style={{
                          ...styles.statusDot,
                          backgroundColor: statusColors[item.status],
                        }}
                      />
                      Analysis #{item.id}
                      {item.repository_id && (
                        <span style={{ color: '#666', fontSize: '12px', marginLeft: '8px' }}>
                          (Repository #{item.repository_id})
                        </span>
                      )}
                    </span>
                    <span style={{ color: '#666', fontSize: '14px' }}>
                      {new Date(item.created_at).toLocaleString()}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        {view === 'repository' && currentRepository && (
          <RepositoryBrowser
            repositoryId={currentRepository.id}
            onBack={handleBack}
            onAnalysisStarted={handleAnalysisStarted}
          />
        )}

        {view === 'report' && currentAnalysis && (
          <ReportView analysis={currentAnalysis} onBack={handleBack} />
        )}
      </main>
    </div>
  );
}
