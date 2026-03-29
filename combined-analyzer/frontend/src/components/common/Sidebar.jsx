import React from 'react';

const styles = {
  sidebar: {
    width: '300px',
    backgroundColor: '#fff',
    borderRight: '1px solid #e0e0e0',
    display: 'flex',
    flexDirection: 'column',
    height: 'calc(100vh - 70px)',
  },
  header: {
    padding: '16px',
    borderBottom: '1px solid #e0e0e0',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  title: {
    margin: 0,
    fontSize: '14px',
    fontWeight: '600',
    color: '#333',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  newButton: {
    backgroundColor: '#1e3a5f',
    color: '#fff',
    border: 'none',
    padding: '8px 16px',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: '500',
  },
  headerActions: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  compareButton: {
    backgroundColor: '#eef2f7',
    color: '#1e3a5f',
    border: '1px solid #d0d7de',
    padding: '8px 12px',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '12px',
    fontWeight: '600',
  },
  repoList: {
    flex: 1,
    overflowY: 'auto',
    padding: '8px',
  },
  repoItem: {
    padding: '12px 16px',
    borderRadius: '8px',
    cursor: 'pointer',
    marginBottom: '4px',
    transition: 'all 0.2s',
  },
  repoItemDefault: {
    backgroundColor: 'transparent',
  },
  repoItemSelected: {
    backgroundColor: '#e7f3ff',
  },
  repoName: {
    fontWeight: '500',
    fontSize: '14px',
    color: '#333',
    marginBottom: '4px',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  repoMeta: {
    fontSize: '12px',
    color: '#666',
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  sourceIcon: {
    fontSize: '14px',
  },
  badge: {
    fontSize: '10px',
    padding: '2px 6px',
    borderRadius: '4px',
    fontWeight: '500',
  },
  badgeGithub: {
    backgroundColor: '#24292e',
    color: '#fff',
  },
  badgeFolder: {
    backgroundColor: '#6c757d',
    color: '#fff',
  },
  emptyState: {
    padding: '40px 20px',
    textAlign: 'center',
    color: '#666',
  },
  emptyIcon: {
    fontSize: '40px',
    marginBottom: '12px',
  },
  analysisBadges: {
    display: 'flex',
    gap: '6px',
    marginTop: '6px',
    flexWrap: 'wrap',
  },
  analysisBadge: {
    fontSize: '10px',
    padding: '2px 6px',
    borderRadius: '10px',
  },
  erdBadge: {
    backgroundColor: '#e7f3ff',
    color: '#0066cc',
  },
  integrityBadge: {
    backgroundColor: '#e8f5e9',
    color: '#2e7d32',
  },
  complianceBadge: {
    backgroundColor: '#e3f2fd',
    color: '#1565c0',
  },
  correctnessBadge: {
    backgroundColor: '#f1f8e9',
    color: '#33691e',
  },
  usabilityBadge: {
    backgroundColor: '#f3e5f5',
    color: '#6a1b9a',
  },
  maintainabilityBadge: {
    backgroundColor: '#fff3e0',
    color: '#e65100',
  },
};

export default function Sidebar({ repositories, selectedRepo, onRepositorySelect, onNewAnalysis, onOpenComparison }) {
  return (
    <aside style={styles.sidebar}>
      <div style={styles.header}>
        <h2 style={styles.title}>Repositories</h2>
        <div style={styles.headerActions}>
          <button style={styles.compareButton} onClick={onOpenComparison}>
            Compare
          </button>
          <button style={styles.newButton} onClick={onNewAnalysis}>
            + New
          </button>
        </div>
      </div>

      <div style={styles.repoList}>
        {repositories.length === 0 ? (
          <div style={styles.emptyState}>
            <div style={styles.emptyIcon}>&#128193;</div>
            <p>No repositories yet</p>
            <p style={{ fontSize: '12px', marginTop: '8px' }}>
              Upload a folder or connect GitHub to get started
            </p>
          </div>
        ) : (
          repositories.slice(0, 5).map((repo) => (
            <div
              key={repo.id}
              style={{
                ...styles.repoItem,
                ...(selectedRepo?.id === repo.id ? styles.repoItemSelected : styles.repoItemDefault),
              }}
              onClick={() => onRepositorySelect(repo)}
            >
              <div style={styles.repoName}>
                <span style={styles.sourceIcon}>
                  {repo.source_type === 'github' ? '&#128279;' : '&#128193;'}
                </span>
                {repo.name}
                <span
                  style={{
                    ...styles.badge,
                    ...(repo.source_type === 'github' ? styles.badgeGithub : styles.badgeFolder),
                  }}
                >
                  {repo.source_type === 'github' ? 'GitHub' : 'Upload'}
                </span>
              </div>
              <div style={styles.repoMeta}>
                <span>{repo.file_count} files</span>
                <span>{new Date(repo.created_at).toLocaleDateString()}</span>
              </div>
              <div style={styles.analysisBadges}>
                {repo.erd_analysis_count > 0 && (
                  <span style={{ ...styles.analysisBadge, ...styles.erdBadge }}>
                    ERD
                  </span>
                )}
                {repo.integrity_analysis_count > 0 && (
                  <span style={{ ...styles.analysisBadge, ...styles.integrityBadge }}>
                    Integrity
                  </span>
                )}
                {repo.compliance_analysis_count > 0 && (
                  <span style={{ ...styles.analysisBadge, ...styles.complianceBadge }}>
                    Compliance
                  </span>
                )}
                {repo.correctness_analysis_count > 0 && (
                  <span style={{ ...styles.analysisBadge, ...styles.correctnessBadge }}>
                    Correctness
                  </span>
                )}
                {repo.usability_analysis_count > 0 && (
                  <span style={{ ...styles.analysisBadge, ...styles.usabilityBadge }}>
                    Usability
                  </span>
                )}
                {repo.maintainability_analysis_count > 0 && (
                  <span style={{ ...styles.analysisBadge, ...styles.maintainabilityBadge }}>
                    Maintainability
                  </span>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </aside>
  );
}
