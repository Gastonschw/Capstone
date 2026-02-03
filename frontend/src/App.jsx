import React, { useState, useEffect } from 'react';
import UploadForm from './components/UploadForm';
import ReportView from './components/ReportView';
import { pollAnalysis, listAnalyses, getAnalysis } from './api';

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
    maxWidth: '900px',
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
};

const statusColors = {
  pending: '#ffc107',
  processing: '#007bff',
  completed: '#28a745',
  failed: '#dc3545',
};

export default function App() {
  const [currentAnalysis, setCurrentAnalysis] = useState(null);
  const [history, setHistory] = useState([]);
  const [view, setView] = useState('upload'); // 'upload' or 'report'

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      const analyses = await listAnalyses();
      setHistory(analyses);
    } catch (err) {
      console.error('Failed to load history:', err);
    }
  };

  const handleAnalysisStarted = (analysis) => {
    setCurrentAnalysis(analysis);
    setView('report');
    loadHistory();

    // Start polling for updates
    pollAnalysis(analysis.id, (updatedAnalysis) => {
      setCurrentAnalysis(updatedAnalysis);
      if (updatedAnalysis.status === 'completed' || updatedAnalysis.status === 'failed') {
        loadHistory();
      }
    });
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
    setView('upload');
    loadHistory();
  };

  return (
    <div style={styles.app}>
      <header style={styles.header}>
        <h1 style={styles.headerTitle}>ERD Analysis Tool</h1>
        <p style={styles.headerSubtitle}>
          Upload an ERD diagram and user stories to analyze coverage
        </p>
      </header>

      <main style={styles.main}>
        {view === 'upload' ? (
          <>
            <UploadForm onAnalysisStarted={handleAnalysisStarted} />

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
                    </span>
                    <span style={{ color: '#666', fontSize: '14px' }}>
                      {new Date(item.created_at).toLocaleString()}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </>
        ) : (
          <ReportView analysis={currentAnalysis} onBack={handleBack} />
        )}
      </main>
    </div>
  );
}
