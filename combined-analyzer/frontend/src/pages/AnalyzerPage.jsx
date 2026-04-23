import React, { useState, useEffect, useMemo, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import Header from '../components/common/Header';
import Sidebar from '../components/common/Sidebar';
import ChecklistSidebar from '../components/common/ChecklistSidebar';
import UploadForm from '../components/upload/UploadForm';
import RepositoryBrowser from '../components/repository/RepositoryBrowser';
import ERDReportView from '../components/erd/ERDReportView';
import IntegrityReportView from '../components/integrity/IntegrityReportView';
import ComplianceReportView from '../components/compliance/ComplianceReportView';
import CorrectnessReportView from '../components/correctness/CorrectnessReportView';
import UsabilityReportView from '../components/usability/UsabilityReportView';
import MaintainabilityReportView from '../components/maintainability/MaintainabilityReportView';
import ClassesPanel from '../components/classes/ClassesPanel';
import { listRepositories, listChatModels, setCurrentUserId } from '../api';
import { supabase, isSupabaseConfigured } from '../lib/supabaseClient';

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
  reportActionsRow: {
    display: 'flex',
    justifyContent: 'flex-end',
    marginBottom: '12px',
  },
  exportButton: {
    padding: '8px 14px',
    borderRadius: '8px',
    border: '1px solid #1e3a5f',
    backgroundColor: '#fff',
    color: '#1e3a5f',
    fontSize: '13px',
    fontWeight: 600,
    cursor: 'pointer',
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

export default function AnalyzerPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const inspectCtx = useMemo(() => {
    const c = searchParams.get('inspectClass');
    const s = searchParams.get('inspectStudent');
    const n = searchParams.get('inspectName');
    if (c && s) {
      return {
        classId: c,
        studentId: s,
        label: n ? decodeURIComponent(n) : 'Student',
      };
    }
    return null;
  }, [searchParams]);

  const [repositories, setRepositories] = useState([]);
  const [repositoriesLoading, setRepositoriesLoading] = useState(true);
  const [selectedRepo, setSelectedRepo] = useState(null);
  const [view, setView] = useState('upload');
  const [analysisMap, setAnalysisMap] = useState({});
  const [analysisType, setAnalysisType] = useState(null);
  const [activeReportTab, setActiveReportTab] = useState('erd');
  const [chatApiKey, setChatApiKey] = useState(() => readFromStorage(CHAT_API_KEY_STORAGE));
  const [chatModel, setChatModel] = useState(() => readFromStorage(CHAT_MODEL_STORAGE, DEFAULT_CHAT_MODEL));
  const [availableModels, setAvailableModels] = useState([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [modelsError, setModelsError] = useState('');
  const [authUser, setAuthUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(isSupabaseConfigured);
  const modelsDebounceIsFirst = useRef(true);
  const reportExportRef = useRef(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('github_auth')) {
      const sid = params.get('session_id');
      if (sid) {
        import('../api').then(({ setSessionId }) => setSessionId(sid));
      }
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setRepositoriesLoading(true);
      try {
        if (!inspectCtx) {
          const repos = await listRepositories();
          if (cancelled) return;
          const list = Array.isArray(repos) ? repos : [];
          setRepositories(list);
          setSelectedRepo((prevSelected) => {
            if (!prevSelected?.id) return prevSelected;
            const refreshed = list.find((repo) => repo.id === prevSelected.id);
            if (refreshed) return refreshed;
            setView('upload');
            return null;
          });
          return;
        }
        const repos = await listRepositories({
          classId: inspectCtx.classId,
          studentUserId: inspectCtx.studentId,
        });
        if (cancelled) return;
        const list = Array.isArray(repos) ? repos : [];
        setRepositories(list);
        setSelectedRepo(list[0] ?? null);
        setView(list.length > 0 ? 'browser' : 'upload');
      } catch (err) {
        if (!cancelled) console.error('Failed to load repositories:', err);
      } finally {
        if (!cancelled) setRepositoriesLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [inspectCtx]);

  useEffect(() => {
    if (!isSupabaseConfigured || !supabase) {
      setAuthLoading(false);
      return;
    }
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setAuthUser(session?.user ?? null);
      setCurrentUserId(session?.user?.id ?? null);
    });
    supabase.auth.getSession().then(({ data: { session } }) => {
      setAuthUser(session?.user ?? null);
      setCurrentUserId(session?.user?.id ?? null);
      setAuthLoading(false);
    });
    return () => subscription.unsubscribe();
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

    const delayMs = modelsDebounceIsFirst.current ? 0 : 300;
    modelsDebounceIsFirst.current = false;
    const timeoutId = setTimeout(loadModels, delayMs);
    return () => {
      cancelled = true;
      clearTimeout(timeoutId);
    };
  }, [chatApiKey]);

  const loadRepositories = async () => {
    setRepositoriesLoading(true);
    try {
      const repos = inspectCtx
        ? await listRepositories({ classId: inspectCtx.classId, studentUserId: inspectCtx.studentId })
        : await listRepositories();
      setRepositories(Array.isArray(repos) ? repos : []);
    } catch (err) {
      console.error('Failed to load repositories:', err);
    } finally {
      setRepositoriesLoading(false);
    }
  };

  const handleRepositoryCreated = (repository) => {
    if (inspectCtx) return;
    setSelectedRepo(repository);
    setView('browser');
    loadRepositories();
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

  const handleExitInspect = () => {
    navigate('/analyzer', { replace: true });
  };

  const handleAnalysisComplete = (analysis, type) => {
    setAnalysisMap(prev => ({ ...prev, [type]: analysis }));
    setAnalysisType(type);
    setActiveReportTab(type);
    setView(`${type}-report`);
  };

  const handleBackToRepository = () => {
    setView('browser');
    setAnalysisMap({});
  };

  const handleBackToUpload = () => {
    setSelectedRepo(null);
    setView('upload');
    loadRepositories();
  };

  const handleDownloadPdf = () => {
    const reportNode = reportExportRef.current;
    if (!reportNode || typeof window === 'undefined') return;

    const title = `${activeReportTab || 'analysis'}-report`;
    const printWindow = window.open('', '_blank', 'width=1200,height=800');
    if (!printWindow) return;

    const html = reportNode.innerHTML;
    printWindow.document.write(`
      <!doctype html>
      <html>
        <head>
          <meta charset="utf-8" />
          <title>${title}</title>
          <style>
            body { font-family: Arial, sans-serif; margin: 24px; color: #1a1a1a; }
            h1, h2, h3, h4, h5, h6 { page-break-after: avoid; }
            table { border-collapse: collapse; width: 100%; }
            td, th { padding: 6px 10px; border: 1px solid #ddd; text-align: left; }
            img { max-width: 100%; height: auto; }
            * { box-sizing: border-box; }
            @media print {
              body { margin: 0; }
              button, .no-print { display: none !important; }
            }
          </style>
        </head>
        <body>
          ${html}
        </body>
      </html>
    `);
    printWindow.document.close();
    setTimeout(() => {
      printWindow.focus();
      printWindow.print();
    }, 250);
  };

  const renderContent = () => {
    switch (view) {
      case 'upload':
        return (
          <div>
            {!inspectCtx && (
              <UploadForm onRepositoryCreated={handleRepositoryCreated} tamuApiKey={chatApiKey} />
            )}
            <ClassesPanel />
            {!repositoriesLoading && repositories.length === 0 && (
              <div style={styles.welcome}>
                <h2 style={styles.welcomeTitle}>
                  {inspectCtx ? "This student has no repositories yet" : 'Welcome to Combined Analyzer'}
                </h2>
                <p style={styles.welcomeText}>
                  {inspectCtx
                    ? 'They have not uploaded or imported a project linked to their account.'
                    : 'Upload a project folder or connect to GitHub to analyze your codebase. Run ERD analysis to check database design against user stories, or run Integrity analysis to assess security characteristics.'}
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
            tamuApiKey={chatApiKey}
            tamuModel={chatModel}
          />
        ) : null;

      case 'erd-report':
      case 'integrity-report':
      case 'compliance-report':
      case 'correctness-report':
      case 'usability-report':
      case 'maintainability-report': {
        if (Object.keys(analysisMap).length === 0) return null;
        const ReportComponents = {
          erd: ERDReportView,
          integrity: IntegrityReportView,
          compliance: ComplianceReportView,
          correctness: CorrectnessReportView,
          usability: UsabilityReportView,
          maintainability: MaintainabilityReportView,
        };
        // Only show tabs for types that have results
        const availableTabs = Object.keys(analysisMap).map((key) => ({
          key,
          label: key.charAt(0).toUpperCase() + key.slice(1),
        }));
        const activeAnalysis = analysisMap[activeReportTab];
        const ActiveReport = ReportComponents[activeReportTab] || IntegrityReportView;
        return (
          <div>
            <div style={styles.tabContainer}>
              {availableTabs.map((t) => (
                <button
                  key={t.key}
                  style={{ ...styles.tab, ...(activeReportTab === t.key ? styles.tabActive : styles.tabInactive) }}
                  onClick={() => {
                    setActiveReportTab(t.key);
                    setView(`${t.key}-report`);
                  }}
                >
                  {t.label}
                </button>
              ))}
            </div>
            {activeAnalysis && (
              <div style={styles.reportActionsRow}>
                <button type="button" style={styles.exportButton} onClick={handleDownloadPdf}>
                  Download PDF
                </button>
              </div>
            )}
            {activeAnalysis ? (
              <div ref={reportExportRef}>
                <ActiveReport
                  analysisId={activeAnalysis.id}
                  onBack={handleBackToRepository}
                  chatModel={chatModel}
                  chatApiKey={chatApiKey}
                />
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
                <p>No {activeReportTab} analysis results available.</p>
              </div>
            )}
          </div>
        );
      }

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
        authUser={authUser}
        authLoading={authLoading}
        supabaseConfigured={isSupabaseConfigured}
      />
      <div style={styles.main}>
        <Sidebar
          repositories={repositories}
          repositoriesLoading={repositoriesLoading}
          selectedRepo={selectedRepo}
          onRepositorySelect={handleRepositorySelect}
          onOpenComparison={() => {
            if (inspectCtx) {
              const params = new URLSearchParams({
                inspectClass: inspectCtx.classId,
                inspectStudent: inspectCtx.studentId,
              });
              if (inspectCtx.label) {
                params.set('inspectName', inspectCtx.label);
              }
              navigate(`/compare?${params.toString()}`);
              return;
            }
            navigate('/compare');
          }}
          onNewAnalysis={() => {
            setSelectedRepo(null);
            setView('upload');
          }}
          inspectMode={Boolean(inspectCtx)}
          inspectLabel={inspectCtx?.label}
          onExitInspect={handleExitInspect}
          disableNewAnalysis={Boolean(inspectCtx)}
        />
        <main style={styles.content}>
          {renderContent()}
        </main>
      </div>
      <ChecklistSidebar
        userId={authUser?.id ?? null}
        supabaseConfigured={isSupabaseConfigured}
      />
    </div>
  );
}
