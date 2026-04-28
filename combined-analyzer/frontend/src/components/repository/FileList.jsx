import React, { useMemo, useState } from 'react';

const styles = {
  container: {
    maxHeight: '350px',
    overflowY: 'auto',
    border: '1px solid #e0e0e0',
    borderRadius: '8px',
  },
  searchRow: {
    padding: '10px 16px',
    borderBottom: '1px solid #e0e0e0',
    backgroundColor: '#fff',
  },
  searchInput: {
    width: '100%',
    padding: '8px 10px',
    borderRadius: '6px',
    border: '1px solid #d7dce1',
    fontSize: '12px',
    outline: 'none',
  },
  selectAllRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '10px 16px',
    backgroundColor: '#f8f9fa',
    borderBottom: '1px solid #e0e0e0',
    position: 'sticky',
    top: 0,
  },
  selectAllLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    cursor: 'pointer',
    fontSize: '13px',
    color: '#333',
  },
  checkbox: {
    width: '16px',
    height: '16px',
    cursor: 'pointer',
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
  fileInfo: {
    flex: 1,
    minWidth: 0,
  },
  fileName: {
    fontSize: '13px',
    fontWeight: '500',
    color: '#333',
    wordBreak: 'break-all',
    marginBottom: '4px',
  },
  fileMeta: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '12px',
    color: '#666',
  },
  badge: {
    fontSize: '10px',
    padding: '2px 6px',
    borderRadius: '4px',
    fontWeight: '500',
  },
  typeBadge: {
    backgroundColor: '#e0e0e0',
    color: '#333',
  },
  languageBadge: {
    backgroundColor: '#e7f3ff',
    color: '#0066cc',
  },
  scoreBadge: {
    borderRadius: '10px',
    padding: '2px 8px',
  },
  scoreHigh: {
    backgroundColor: '#d4edda',
    color: '#155724',
  },
  scoreMedium: {
    backgroundColor: '#fff3cd',
    color: '#856404',
  },
  scoreLow: {
    backgroundColor: '#f8d7da',
    color: '#721c24',
  },
  preview: {
    fontSize: '11px',
    color: '#888',
    marginTop: '6px',
    backgroundColor: '#f8f9fa',
    padding: '6px 8px',
    borderRadius: '4px',
    whiteSpace: 'pre-wrap',
    maxHeight: '60px',
    overflow: 'hidden',
  },
  emptyState: {
    padding: '40px 20px',
    textAlign: 'center',
    color: '#666',
  },
  emptyIcon: {
    fontSize: '32px',
    marginBottom: '8px',
  },
};

function getScoreStyle(score) {
  if (score >= 70) return styles.scoreHigh;
  if (score >= 50) return styles.scoreMedium;
  return styles.scoreLow;
}

function getFileTypeLabel(fileType) {
  const labels = {
    erd_image: 'ERD Image',
    user_story: 'User Story',
    code: 'Code',
    config: 'Config',
  };
  return labels[fileType] || fileType;
}

export default function FileList({ files, selectionField, onToggle, onSelectAll, scoreField, scoreLabel }) {
  const [searchValue, setSearchValue] = useState('');

  if (!files || files.length === 0) {
    return (
      <div style={styles.emptyState}>
        <div style={styles.emptyIcon}>&#128193;</div>
        <p>No files discovered</p>
      </div>
    );
  }

  const filteredFiles = useMemo(() => {
    let result = [...files];
    const query = searchValue.trim().toLowerCase();
    if (query) {
      result = result.filter((f) => {
        const path = (f.file_path || '').toLowerCase();
        const language = (f.language || '').toLowerCase();
        return path.includes(query) || language.includes(query);
      });
    }
    // Sort: selected first, then by score descending
    const sf = selectionField;
    const scf = scoreField;
    result.sort((a, b) => {
      const aSelected = a[sf] ? 1 : 0;
      const bSelected = b[sf] ? 1 : 0;
      if (aSelected !== bSelected) return bSelected - aSelected;
      return (b[scf] || 0) - (a[scf] || 0);
    });
    return result;
  }, [files, searchValue, selectionField, scoreField]);

  const allSelected = filteredFiles.length > 0 && filteredFiles.every((f) => f[selectionField]);
  const someSelected = filteredFiles.some((f) => f[selectionField]);

  return (
    <div style={styles.container}>
      <div style={styles.searchRow}>
        <input
          type="text"
          value={searchValue}
          onChange={(e) => setSearchValue(e.target.value)}
          placeholder="Filter files by path, type, or language..."
          style={styles.searchInput}
        />
      </div>
      <div style={styles.selectAllRow}>
        <label style={styles.selectAllLabel}>
          <input
            type="checkbox"
            checked={allSelected}
            ref={(el) => {
              if (el) el.indeterminate = someSelected && !allSelected;
            }}
            onChange={(e) => {
              if (filteredFiles.length === 0) return;
              onSelectAll(e.target.checked, filteredFiles.map((f) => f.id));
            }}
            style={styles.checkbox}
          />
          Select visible ({filteredFiles.filter((f) => f[selectionField]).length}/{filteredFiles.length})
        </label>
      </div>

      {filteredFiles.length === 0 ? (
        <div style={styles.emptyState}>
          <div style={styles.emptyIcon}>&#128269;</div>
          <p>No files match the current filter</p>
        </div>
      ) : (
        filteredFiles.map((file, idx) => (
          <div
            key={file.id}
            style={{
              ...styles.fileItem,
              ...(idx === filteredFiles.length - 1 ? styles.fileItemLast : {}),
            }}
          >
            <input
              type="checkbox"
              checked={file[selectionField]}
              onChange={() => onToggle(file.id, selectionField, file[selectionField])}
              style={styles.checkbox}
            />
            <div style={styles.fileInfo}>
              <div style={styles.fileName}>{file.file_path}</div>
              <div style={styles.fileMeta}>
                <span style={{ ...styles.badge, ...styles.typeBadge }}>
                  {getFileTypeLabel(file.file_type)}
                </span>
                {file.language && (
                  <span style={{ ...styles.badge, ...styles.languageBadge }}>{file.language}</span>
                )}
                <span style={{ ...styles.badge, ...styles.scoreBadge, ...getScoreStyle(file[scoreField]) }}>
                  {file[scoreField]}% {scoreLabel}
                </span>
              </div>
              {file.content_preview && (
                <div style={styles.preview}>{file.content_preview}</div>
              )}
            </div>
          </div>
        ))
      )}
    </div>
  );
}
