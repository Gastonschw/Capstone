import React from 'react';

const styles = {
  container: {
    maxHeight: '350px',
    overflowY: 'auto',
    border: '1px solid #e0e0e0',
    borderRadius: '8px',
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
  if (!files || files.length === 0) {
    return (
      <div style={styles.emptyState}>
        <div style={styles.emptyIcon}>&#128193;</div>
        <p>No files discovered</p>
      </div>
    );
  }

  const allSelected = files.every((f) => f[selectionField]);
  const someSelected = files.some((f) => f[selectionField]);

  return (
    <div style={styles.container}>
      <div style={styles.selectAllRow}>
        <label style={styles.selectAllLabel}>
          <input
            type="checkbox"
            checked={allSelected}
            ref={(el) => {
              if (el) el.indeterminate = someSelected && !allSelected;
            }}
            onChange={(e) => onSelectAll(e.target.checked)}
            style={styles.checkbox}
          />
          Select all ({files.filter((f) => f[selectionField]).length}/{files.length})
        </label>
      </div>

      {files.map((file, idx) => (
        <div
          key={file.id}
          style={{
            ...styles.fileItem,
            ...(idx === files.length - 1 ? styles.fileItemLast : {}),
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
      ))}
    </div>
  );
}
