import React, { useState, useEffect } from 'react';
import Header from './components/common/Header';
import Sidebar from './components/common/Sidebar';
import UploadForm from './components/upload/UploadForm';
import RepositoryBrowser from './components/repository/RepositoryBrowser';
import ERDReportView from './components/erd/ERDReportView';
import IntegrityReportView from './components/integrity/IntegrityReportView';
import { listRepositories, listChatModels } from './api';

const CHAT_API_KEY_STORAGE = 'tamu_chat_api_key';
const CHAT_MODEL_STORAGE = 'tamu_chat_model';
const DEFAULT_CHAT_MODEL = 'protected.Claude Opus 4.5';

function readFromStorage(key, fallback = '') {
  if (typeof window === 'undefined') return fallback;
  return window.localStorage.getItem(key) || fallback;
}

const styles = {
  app: {
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column',
    backgroundColor: '#f5f7fa',
  },
  main: {
    display: 'flex',
    flex: 1,
  },
  content: {
    flex: 1,
    padding: '24px',
    overflowY: 'auto',
  },
  welcome: {
    textAlign: 'center',
    padding: '60px 20px',
    color: '#666',
  },
  welcomeTitle: {
    fontSize: '28px',
    color: '#1e3a5f',
    marginBottom: '12px',
  },
  welcomeText: {
    fontSize: '16px',
    maxWidth: '500px',
    margin: '0 auto',
    lineHeight: 1.6,
  },
  tabContainer: {
    display: 'flex',
    gap: '12px',
    marginBottom: '20px',
  },
  tab: {
    padding: '10px 20px',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: '500',
    transition: 'all 0.2s',
  },
  tabActive: {
    backgroundColor: '#1e3a5f',
    color: '#fff',
  },
  tabInactive: {
    backgroundColor: '#e0e0e0',
    color: '#333',
  },
};

export default function App() {
  const [repositories, setRepositories] = useState([]);
  const [selectedRepo, setSelectedRepo] = useState(null);
  const [view, setView] = useState('upload'); // 'upload', 'browser', 'erd-report', 'integrity-report'
  const [currentAnalysis, setCurrentAnalysis] = useState(null);
  const [analysisType, setAnalysisType] = useState(null);
  const [activeReportTab, setActiveReportTab] = useState('erd'); // 'erd' or 'integrity'
  const [chatApiKey, setChatApiKey] = useState(() => readFromStorage(CHAT_API_KEY_STORAGE));
  const [chatModel, setChatModel] = useState(() => readFromStorage(CHAT_MODEL_STORAGE, DEFAULT_CHAT_MODEL));
  const [availableModels, setAvailableModels] = useState([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [modelsError, setModelsError] = useState('');

  useEffect(() => {
    loadRepositories();

    // Check for GitHub OAuth callback
    const params = new URLSearchParams(window.location.search);
    if (params.get('github_auth')) {
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (chatApiKey) {
      window.localStorage.setItem(CHAT_API_KEY_STORAGE, chatApiKey);
    } else {
      window.localStorage.removeItem(CHAT_API_KEY_STORAGE);
    }
  }, [chatApiKey]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (chatModel) {
      window.localStorage.setItem(CHAT_MODEL_STORAGE, chatModel);
    } else {
      window.localStorage.removeItem(CHAT_MODEL_STORAGE);
    }
  }, [chatModel]);

  useEffect(() => {
    let cancelled = false;

    const loadModels = async () => {
      setModelsLoading(true);
      setModelsError('');

      try {
        const response = await listChatModels(chatApiKey);
        const models = Array.isArray(response?.models) ? response.models : [];
        const fallbackModel = response?.default_model || DEFAULT_CHAT_MODEL;

        if (cancelled) return;

        setAvailableModels(models);
        setChatModel((previousModel) => {
          const preferredModel = previousModel || fallbackModel;
          if (models.some((m) => m.id === preferredModel)) {
            return preferredModel;
          }
          return models[0]?.id || fallbackModel;
        });
      } catch (err) {
        if (cancelled) return;
        setAvailableModels([]);
        setModelsError('Unable to load models');
      } finally {
        if (!cancelled) {
          setModelsLoading(false);
        }
      }
    };

    const timeoutId = setTimeout(loadModels, 300);
    return () => {
      cancelled = true;
      clearTimeout(timeoutId);
    };
  }, [chatApiKey]);

  const loadRepositories = async () => {
    try {
      const repos = await listRepositories();
      setRepositories(repos);
    } catch (err) {
      console.error('Failed to load repositories:', err);
    }
  };

  const handleRepositoryCreated = (repository) => {
    loadRepositories();
    setSelectedRepo(repository);
    setView('browser');
  };

  const handleRepositorySelect = (repo) => {
    setSelectedRepo(repo);
    setView('browser');
  };

  const handleRepositoryDeleted = () => {
    loadRepositories();
    setSelectedRepo(null);
    setView('upload');
  };

  const handleAnalysisComplete = (analysis, type) => {
    setCurrentAnalysis(analysis);
    setAnalysisType(type);
    setActiveReportTab(type);
    setView(type === 'erd' ? 'erd-report' : 'integrity-report');
  };

  const handleBackToRepository = () => {
    setView('browser');
    setCurrentAnalysis(null);
  };

  const handleBackToUpload = () => {
    setSelectedRepo(null);
    setView('upload');
    loadRepositories();
  };

  const renderContent = () => {
    switch (view) {
      case 'upload':
        return (
          <div>
            <UploadForm onRepositoryCreated={handleRepositoryCreated} />
            {repositories.length === 0 && (
              <div style={styles.welcome}>
                <h2 style={styles.welcomeTitle}>Welcome to Combined Analyzer</h2>
                <p style={styles.welcomeText}>
                  Upload a project folder or connect to GitHub to analyze your codebase.
                  Run ERD analysis to check database design against user stories,
                  or run Integrity analysis to assess security characteristics.
                </p>
              </div>
            )}
          </div>
        );

      case 'browser':
        return selectedRepo ? (
          <RepositoryBrowser
            repositoryId={selectedRepo.id}
            onBack={handleBackToUpload}
            onAnalysisComplete={handleAnalysisComplete}
          />
        ) : null;

      case 'erd-report':
        return currentAnalysis ? (
          <div>
            <div style={styles.tabContainer}>
              <button
                style={{ ...styles.tab, ...(activeReportTab === 'erd' ? styles.tabActive : styles.tabInactive) }}
                onClick={() => setActiveReportTab('erd')}
              >
                ERD Analysis
              </button>
              <button
                style={{ ...styles.tab, ...(activeReportTab === 'integrity' ? styles.tabActive : styles.tabInactive) }}
                onClick={() => {
                  setActiveReportTab('integrity');
                  setView('integrity-report');
                }}
              >
                Integrity Analysis
              </button>
            </div>
            <ERDReportView
              analysisId={currentAnalysis.id}
              onBack={handleBackToRepository}
              chatModel={chatModel}
              chatApiKey={chatApiKey}
            />
          </div>
        ) : null;

      case 'integrity-report':
        return currentAnalysis ? (
          <div>
            <div style={styles.tabContainer}>
              <button
                style={{ ...styles.tab, ...(activeReportTab === 'erd' ? styles.tabActive : styles.tabInactive) }}
                onClick={() => {
                  setActiveReportTab('erd');
                  setView('erd-report');
                }}
              >
                ERD Analysis
              </button>
              <button
                style={{ ...styles.tab, ...(activeReportTab === 'integrity' ? styles.tabActive : styles.tabInactive) }}
                onClick={() => setActiveReportTab('integrity')}
              >
                Integrity Analysis
              </button>
            </div>
            <IntegrityReportView
              analysisId={currentAnalysis.id}
              onBack={handleBackToRepository}
              chatModel={chatModel}
              chatApiKey={chatApiKey}
            />
          </div>
        ) : null;

      default:
        return null;
    }
  };

  return (
    <div style={styles.app}>
      <Header
        availableModels={availableModels}
        selectedModel={chatModel}
        onModelChange={setChatModel}
        apiKey={chatApiKey}
        onApiKeyChange={setChatApiKey}
        modelsLoading={modelsLoading}
        modelsError={modelsError}
      />
      <div style={styles.main}>
        <Sidebar
          repositories={repositories}
          selectedRepo={selectedRepo}
          onRepositorySelect={handleRepositorySelect}
          onNewAnalysis={() => {
            setSelectedRepo(null);
            setView('upload');
          }}
        />
        <main style={styles.content}>
          {renderContent()}
        </main>
      </div>
    </div>
  );
}
