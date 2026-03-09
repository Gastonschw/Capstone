import React, { useEffect, useState } from 'react';
import { listMyClasses, createClass, joinClassByCode, deleteClass } from '../../api';

const styles = {
  container: {
    backgroundColor: '#fff',
    borderRadius: '12px',
    padding: '20px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
    marginBottom: '24px',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '16px',
  },
  title: {
    margin: 0,
    fontSize: '16px',
    color: '#1e3a5f',
    fontWeight: '600',
  },
  roleBadge: {
    fontSize: '12px',
    padding: '4px 10px',
    borderRadius: '999px',
    backgroundColor: '#e3f2fd',
    color: '#0d47a1',
    fontWeight: '500',
  },
  content: {
    display: 'grid',
    gridTemplateColumns: 'minmax(0, 1.4fr) minmax(0, 1fr)',
    gap: '20px',
  },
  column: {},
  columnTitle: {
    fontSize: '13px',
    fontWeight: '600',
    color: '#374151',
    marginBottom: '8px',
  },
  formGroup: {
    display: 'flex',
    gap: '8px',
    marginBottom: '10px',
  },
  input: {
    flex: 1,
    padding: '8px 10px',
    borderRadius: '8px',
    border: '1px solid #d1d5db',
    fontSize: '13px',
  },
  button: {
    padding: '8px 14px',
    borderRadius: '8px',
    border: 'none',
    backgroundColor: '#1e3a5f',
    color: '#fff',
    fontSize: '13px',
    fontWeight: '500',
    cursor: 'pointer',
    whiteSpace: 'nowrap',
  },
  buttonSecondary: {
    backgroundColor: '#6b7280',
  },
  helperText: {
    fontSize: '12px',
    color: '#6b7280',
    marginBottom: '10px',
  },
  list: {
    borderTop: '1px solid #e5e7eb',
    paddingTop: '10px',
    marginTop: '12px',
  },
  listHeader: {
    fontSize: '11px',
    fontWeight: '600',
    color: '#6b7280',
    marginBottom: '8px',
    textTransform: 'uppercase',
    letterSpacing: '0.04em',
  },
  classItem: {
    padding: '10px 12px',
    borderRadius: '10px',
    border: '1px solid #e5e7eb',
    backgroundColor: '#f9fafb',
    marginBottom: '10px',
  },
  className: {
    fontSize: '14px',
    fontWeight: '500',
    color: '#111827',
  },
  classItemHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: '12px',
  },
  classItemMain: {
    minWidth: 0,
  },
  classItemFooter: {
    marginTop: '8px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: '8px',
    flexWrap: 'wrap',
  },
  classItemActions: {
    display: 'flex',
    gap: '8px',
    flexWrap: 'wrap',
  },
  classMeta: {
    fontSize: '12px',
    color: '#6b7280',
    marginTop: '2px',
  },
  codeBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '12px',
    padding: '4px 8px',
    borderRadius: '999px',
    backgroundColor: '#fef3c7',
    color: '#92400e',
  },
  copyButton: {
    border: 'none',
    backgroundColor: 'transparent',
    color: '#92400e',
    fontSize: '11px',
    cursor: 'pointer',
    textDecoration: 'underline',
    padding: 0,
  },
  toastContainer: {
    position: 'fixed',
    bottom: '20px',
    right: '24px',
    zIndex: 50,
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  toast: {
    minWidth: '260px',
    maxWidth: '360px',
    padding: '10px 12px',
    borderRadius: '10px',
    display: 'flex',
    alignItems: 'flex-start',
    gap: '8px',
    boxShadow: '0 10px 25px rgba(0,0,0,0.18)',
    fontSize: '13px',
  },
  toastSuccess: {
    backgroundColor: '#ecfdf3',
    border: '1px solid #bbf7d0',
    color: '#14532d',
  },
  toastError: {
    backgroundColor: '#fef2f2',
    border: '1px solid #fecaca',
    color: '#7f1d1d',
  },
  toastTitle: {
    fontWeight: 600,
    marginBottom: '2px',
  },
  toastCloseButton: {
    marginLeft: 'auto',
    border: 'none',
    background: 'transparent',
    cursor: 'pointer',
    padding: '0 2px',
    color: 'inherit',
    fontSize: '14px',
    lineHeight: 1,
  },
  modalBackdrop: {
    position: 'fixed',
    inset: 0,
    backgroundColor: 'rgba(15,23,42,0.35)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 40,
  },
  modal: {
    backgroundColor: '#fff',
    borderRadius: '12px',
    padding: '20px 22px',
    width: '100%',
    maxWidth: '420px',
    boxShadow: '0 18px 45px rgba(15,23,42,0.45)',
  },
  modalTitle: {
    margin: 0,
    fontSize: '16px',
    fontWeight: 600,
    color: '#111827',
  },
  modalBody: {
    marginTop: '10px',
    fontSize: '13px',
    color: '#4b5563',
  },
  modalHighlight: {
    fontWeight: 600,
    color: '#111827',
  },
  modalActions: {
    marginTop: '18px',
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '8px',
  },
  modalButton: {
    padding: '7px 14px',
    borderRadius: '8px',
    fontSize: '13px',
    fontWeight: 500,
    border: 'none',
    cursor: 'pointer',
  },
  modalButtonSecondary: {
    backgroundColor: '#e5e7eb',
    color: '#111827',
  },
  modalButtonDanger: {
    backgroundColor: '#b91c1c',
    color: '#fff',
  },
};

function Toast({ message, type, onClose }) {
  if (!message) return null;

  const isError = type === 'error';

  return (
    <div style={styles.toastContainer}>
      <div
        style={{
          ...styles.toast,
          ...(isError ? styles.toastError : styles.toastSuccess),
        }}
      >
        <div>
          <div style={styles.toastTitle}>{isError ? 'Something went wrong' : 'Success'}</div>
          <div>{message}</div>
        </div>
        <button type="button" style={styles.toastCloseButton} onClick={onClose} aria-label="Close message">
          ×
        </button>
      </div>
    </div>
  );
}

function DeleteClassModal({ classToDelete, onCancel, onConfirm, loading }) {
  if (!classToDelete) return null;

  return (
    <div style={styles.modalBackdrop} role="dialog" aria-modal="true" aria-labelledby="delete-class-title">
      <div style={styles.modal}>
        <h3 id="delete-class-title" style={styles.modalTitle}>
          Delete class?
        </h3>
        <p style={styles.modalBody}>
          You are about to permanently delete{' '}
          <span style={styles.modalHighlight}>{classToDelete.name}</span>. Students will no longer be able to use this
          join code.
        </p>
        <div style={styles.modalActions}>
          <button
            type="button"
            style={{ ...styles.modalButton, ...styles.modalButtonSecondary }}
            onClick={onCancel}
            disabled={loading}
          >
            Cancel
          </button>
          <button
            type="button"
            style={{ ...styles.modalButton, ...styles.modalButtonDanger }}
            onClick={onConfirm}
            disabled={loading}
          >
            {loading ? 'Deleting…' : 'Delete'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function ClassesPanel() {
  const [loading, setLoading] = useState(true);
  const [role, setRole] = useState('general');
  const [teaching, setTeaching] = useState([]);
  const [enrolled, setEnrolled] = useState([]);

  const [newClassName, setNewClassName] = useState('');
  const [newClassDescription, setNewClassDescription] = useState('');
  const [joinCode, setJoinCode] = useState('');

  const [statusMessage, setStatusMessage] = useState('');
  const [statusType, setStatusType] = useState(''); // 'error' | 'success'
  const [copiedClassId, setCopiedClassId] = useState(null);
  const [classToDelete, setClassToDelete] = useState(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  useEffect(() => {
    if (!statusMessage) return;
    const timeoutId = setTimeout(() => {
      setStatusMessage('');
      setStatusType('');
    }, 3000);
    return () => clearTimeout(timeoutId);
  }, [statusMessage]);

  useEffect(() => {
    if (!copiedClassId) return;
    const timeoutId = setTimeout(() => {
      setCopiedClassId(null);
    }, 3000);
    return () => clearTimeout(timeoutId);
  }, [copiedClassId]);

  const showStatus = (message, type) => {
    setStatusMessage(message);
    setStatusType(type);
  };

  useEffect(() => {
    let cancelled = false;

    const fetchClasses = async () => {
      try {
        const data = await listMyClasses();
        if (cancelled) return;
        setRole(data.role || 'general');
        setTeaching(data.teaching || []);
        setEnrolled(data.enrolled || []);
      } catch (err) {
        if (cancelled) return;
        console.error('Failed to load classes', err);
        setStatusMessage('Unable to load classes. Make sure you are signed in.');
        setStatusType('error');
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    fetchClasses();

    return () => {
      cancelled = true;
    };
  }, []);

  const handleCreateClass = async (e) => {
    e.preventDefault();
    if (!newClassName.trim()) return;
    setStatusMessage('');
    setStatusType('');
    try {
      const created = await createClass(newClassName.trim(), newClassDescription.trim());
      setTeaching((prev) => [created, ...prev]);
      setNewClassName('');
      setNewClassDescription('');
      setStatusMessage(`Class created. Join code: ${created.join_code}`);
      setStatusType('success');
    } catch (err) {
      console.error('Create class failed', err);
      const msg =
        err?.response?.data?.detail ||
        (err?.response?.status === 403
          ? 'Only admin users can create classes.'
          : 'Failed to create class.');
      showStatus(msg, 'error');
    }
  };

  const handleJoinClass = async (e) => {
    e.preventDefault();
    if (!joinCode.trim()) return;
    setStatusMessage('');
    setStatusType('');
    try {
      const joined = await joinClassByCode(joinCode.trim());
      setEnrolled((prev) => {
        if (prev.some((c) => c.id === joined.id)) return prev;
        return [joined, ...prev];
      });
      setJoinCode('');
      showStatus(`Joined class: ${joined.name}`, 'success');
    } catch (err) {
      console.error('Join class failed', err);
      const msg =
        err?.response?.data?.detail ||
        (err?.response?.status === 404 ? 'No class found for that code.' : 'Failed to join class.');
      showStatus(msg, 'error');
    }
  };

  const roleLabel = role === 'admin' ? 'Admin (Teacher)' : 'General User (Student)';

  return (
    <section style={styles.container}>
      <div style={styles.header}>
        <h2 style={styles.title}>Classes</h2>
        {!loading && (
          <span style={styles.roleBadge}>
            Role: {roleLabel}
          </span>
        )}
      </div>

      <div style={styles.content}>
        {role === 'admin' && (
          <div style={styles.column}>
          <div style={styles.columnTitle}>Create a Class</div>
          <p style={styles.helperText}>
            Teachers (admins) can create classes and share the 6-digit join code with students.
          </p>
          <form onSubmit={handleCreateClass}>
            <div style={styles.formGroup}>
              <input
                type="text"
                placeholder="Class name (e.g., CSCE 606 – Spring)"
                value={newClassName}
                onChange={(e) => setNewClassName(e.target.value)}
                style={styles.input}
              />
            </div>
            <div style={styles.formGroup}>
              <input
                type="text"
                placeholder="Optional description"
                value={newClassDescription}
                onChange={(e) => setNewClassDescription(e.target.value)}
                style={styles.input}
              />
              <button type="submit" style={styles.button}>
                Create Class
              </button>
            </div>
          </form>

          <div style={styles.list}>
            <div style={styles.listHeader}>My Classes (Teaching)</div>
            {teaching.length === 0 ? (
              <p style={styles.helperText}>
                {role === 'admin'
                  ? 'You have not created any classes yet. When you create one, it will appear here with its join code.'
                  : 'Sign in as an admin to create and manage classes.'}
              </p>
            ) : (
              teaching.map((cls) => (
                <div key={cls.id} style={styles.classItem}>
                  <div style={styles.classItemHeader}>
                    <div style={styles.classItemMain}>
                      <div style={styles.className}>{cls.name}</div>
                      {cls.description && <div style={styles.classMeta}>{cls.description}</div>}
                    </div>
                    {cls.join_code && (
                      <div style={styles.codeBadge}>
                        <span>Join code:</span>
                        <strong>{cls.join_code}</strong>
                      </div>
                    )}
                  </div>
                  <div style={styles.classItemFooter}>
                    <div style={{ fontSize: '11px', color: '#6b7280' }}>Share this join code with your students.</div>
                    <div style={styles.classItemActions}>
                      {cls.join_code && (
                        <button
                          type="button"
                          style={styles.copyButton}
                          onClick={async () => {
                            try {
                              if (navigator.clipboard && navigator.clipboard.writeText) {
                                await navigator.clipboard.writeText(cls.join_code);
                                setCopiedClassId(cls.id);
                                showStatus('Join code copied to clipboard.', 'success');
                              }
                            } catch (err) {
                              console.error('Copy join code failed', err);
                              showStatus('Unable to copy join code. You can copy it manually.', 'error');
                            }
                          }}
                        >
                          {copiedClassId === cls.id ? 'Copied' : 'Copy code'}
                        </button>
                      )}
                      <button
                        type="button"
                        style={{ ...styles.copyButton, color: '#b91c1c' }}
                        onClick={() => setClassToDelete(cls)}
                      >
                        Delete class
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
          </div>
        )}

        {role !== 'admin' && (
          <div style={styles.column}>
            <div style={styles.columnTitle}>Join a Class</div>
            <p style={styles.helperText}>
              Enter the 6-digit code provided by your instructor to join their class.
            </p>
            <form onSubmit={handleJoinClass}>
              <div style={styles.formGroup}>
                <input
                  type="text"
                  placeholder="6-digit code"
                  value={joinCode}
                  onChange={(e) => setJoinCode(e.target.value)}
                  style={styles.input}
                />
                <button type="submit" style={{ ...styles.button, ...styles.buttonSecondary }}>
                  Join
                </button>
              </div>
            </form>

            <div style={styles.list}>
              {enrolled.length === 0 ? (
                <>
                  <div style={styles.listHeader}>My Enrolled Classes</div>
                  <p style={styles.helperText}>
                    You have not joined any classes yet. Once you join with a code, they will be listed here.
                  </p>
                </>
              ) : (
                enrolled.map((cls) => (
                  <div key={cls.id} style={styles.classItem}>
                    <div style={styles.className}>{cls.name}</div>
                    {cls.description && <div style={styles.classMeta}>{cls.description}</div>}
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>

      <DeleteClassModal
        classToDelete={classToDelete}
        loading={deleteLoading}
        onCancel={() => {
          if (deleteLoading) return;
          setClassToDelete(null);
        }}
        onConfirm={async () => {
          if (!classToDelete) return;
          try {
            setDeleteLoading(true);
            await deleteClass(classToDelete.id);
            setTeaching((prev) => prev.filter((c) => c.id !== classToDelete.id));
            showStatus('Class deleted.', 'success');
          } catch (err) {
            console.error('Delete class failed', err);
            const msg = err?.response?.data?.detail || 'Failed to delete class. Please try again.';
            showStatus(msg, 'error');
          } finally {
            setDeleteLoading(false);
            setClassToDelete(null);
          }
        }}
      />
      <Toast message={statusMessage} type={statusType} onClose={() => showStatus('', '')} />
    </section>
  );
}

