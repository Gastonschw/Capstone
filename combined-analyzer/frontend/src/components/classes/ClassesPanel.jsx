import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  listMyClasses,
  createClass,
  deleteClass,
  listClassMembers,
  removeClassMember,
  rotateClassJoinCode,
} from '../../api';

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
    gridTemplateColumns: 'minmax(0, 1fr)',
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
  modalButtonPrimary: {
    backgroundColor: '#1e3a5f',
    color: '#fff',
  },
  rosterBlock: {
    marginTop: '12px',
    paddingTop: '12px',
    borderTop: '1px dashed #e5e7eb',
  },
  rosterToggle: {
    padding: '6px 10px',
    borderRadius: '8px',
    border: '1px solid #d1d5db',
    backgroundColor: '#fff',
    fontSize: '12px',
    fontWeight: 500,
    cursor: 'pointer',
    color: '#1e3a5f',
  },
  memberRow: {
    display: 'flex',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: '8px',
    padding: '8px 0',
    borderBottom: '1px solid #f3f4f6',
    fontSize: '13px',
  },
  memberMain: {
    flex: '1 1 160px',
    minWidth: 0,
  },
  smallBtn: {
    padding: '4px 8px',
    borderRadius: '6px',
    border: '1px solid #d1d5db',
    backgroundColor: '#fff',
    fontSize: '11px',
    cursor: 'pointer',
  },
  smallBtnDanger: {
    borderColor: '#fecaca',
    color: '#b91c1c',
  },
  rosterSearchWrap: {
    marginBottom: '10px',
  },
  rosterSearchLabel: {
    display: 'block',
    fontSize: '11px',
    fontWeight: 600,
    color: '#6b7280',
    marginBottom: '4px',
    textTransform: 'uppercase',
    letterSpacing: '0.04em',
  },
  rosterSearchInput: {
    width: '100%',
    boxSizing: 'border-box',
    padding: '8px 10px',
    borderRadius: '8px',
    border: '1px solid #d1d5db',
    fontSize: '13px',
  },
};

function filterRosterMembers(members, query) {
  const q = (query || '').trim().toLowerCase();
  if (!q) return members;
  return members.filter((m) => {
    const blob = [m.full_name, m.email, m.user_id].filter(Boolean).join(' ').toLowerCase();
    return blob.includes(q);
  });
}

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

function RotateJoinCodeModal({ classToRotate, onCancel, onConfirm, loading }) {
  if (!classToRotate) return null;

  return (
    <div style={styles.modalBackdrop} role="dialog" aria-modal="true" aria-labelledby="rotate-code-title">
      <div style={styles.modal}>
        <h3 id="rotate-code-title" style={styles.modalTitle}>
          Generate a new join code?
        </h3>
        <p style={styles.modalBody}>
          For <span style={styles.modalHighlight}>{classToRotate.name}</span>, the current code{' '}
          {classToRotate.join_code ? (
            <>
              (<span style={styles.modalHighlight}>{classToRotate.join_code}</span>){' '}
            </>
          ) : null}
          will stop working for new sign-ups. Students already in the class stay enrolled; share the new code only with
          people who still need to join.
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
            style={{ ...styles.modalButton, ...styles.modalButtonPrimary }}
            onClick={onConfirm}
            disabled={loading}
          >
            {loading ? 'Generating…' : 'New join code'}
          </button>
        </div>
      </div>
    </div>
  );
}

function RemoveMemberModal({ pending, onCancel, onConfirm, loading }) {
  if (!pending) return null;

  const { className, member } = pending;
  const studentLabel = member.full_name || member.email || member.user_id;

  return (
    <div style={styles.modalBackdrop} role="dialog" aria-modal="true" aria-labelledby="remove-member-title">
      <div style={styles.modal}>
        <h3 id="remove-member-title" style={styles.modalTitle}>
          Remove student from class?
        </h3>
        <p style={styles.modalBody}>
          Remove <span style={styles.modalHighlight}>{studentLabel}</span> from{' '}
          <span style={styles.modalHighlight}>{className}</span>? They will need the join code again to re-enroll.
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
            {loading ? 'Removing…' : 'Remove student'}
          </button>
        </div>
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
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [role, setRole] = useState('general');
  const [teaching, setTeaching] = useState([]);
  const [enrolled, setEnrolled] = useState([]);

  const [newClassName, setNewClassName] = useState('');
  const [newClassDescription, setNewClassDescription] = useState('');
  const [expandedClassId, setExpandedClassId] = useState(null);
  const [rosterByClass, setRosterByClass] = useState({});
  const [rosterLoading, setRosterLoading] = useState({});
  const [rosterSearchByClass, setRosterSearchByClass] = useState({});

  const [statusMessage, setStatusMessage] = useState('');
  const [statusType, setStatusType] = useState(''); // 'error' | 'success'
  const [copiedClassId, setCopiedClassId] = useState(null);
  const [classToDelete, setClassToDelete] = useState(null);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [memberRemovePending, setMemberRemovePending] = useState(null);
  const [removeMemberLoading, setRemoveMemberLoading] = useState(false);
  const [joinCodeRotateClass, setJoinCodeRotateClass] = useState(null);
  const [joinCodeRotateLoading, setJoinCodeRotateLoading] = useState(false);

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

  const ensureRosterLoaded = async (classId) => {
    if (rosterByClass[classId]) return;
    setRosterLoading((m) => ({ ...m, [classId]: true }));
    try {
      const data = await listClassMembers(classId);
      setRosterByClass((prev) => ({ ...prev, [classId]: data.members || [] }));
    } catch (err) {
      console.error('Load roster failed', err);
      showStatus(err?.response?.data?.detail || 'Could not load class roster.', 'error');
    } finally {
      setRosterLoading((m) => ({ ...m, [classId]: false }));
    }
  };

  const toggleRoster = async (classId) => {
    if (expandedClassId === classId) {
      setExpandedClassId(null);
      setRosterSearchByClass((prev) => {
        const next = { ...prev };
        delete next[classId];
        return next;
      });
      return;
    }
    setExpandedClassId(classId);
    await ensureRosterLoaded(classId);
  };

  const openRemoveMemberModal = (classId, className, member) => {
    setMemberRemovePending({ classId, className, member });
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
          <div style={styles.columnTitle}>Create a class</div>
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
                        style={styles.copyButton}
                        onClick={() => setJoinCodeRotateClass(cls)}
                      >
                        New join code
                      </button>
                      <button
                        type="button"
                        style={{ ...styles.copyButton, color: '#b91c1c' }}
                        onClick={() => setClassToDelete(cls)}
                      >
                        Delete class
                      </button>
                      <button type="button" style={styles.rosterToggle} onClick={() => toggleRoster(cls.id)}>
                        {expandedClassId === cls.id ? 'Hide roster' : 'Roster'}
                      </button>
                    </div>
                  </div>
                  {expandedClassId === cls.id ? (
                    <div style={styles.rosterBlock}>
                      {rosterLoading[cls.id] ? (
                        <p style={styles.helperText}>Loading roster…</p>
                      ) : (() => {
                          const allMembers = rosterByClass[cls.id] || [];
                          const searchText = rosterSearchByClass[cls.id] || '';
                          const filteredMembers = filterRosterMembers(allMembers, searchText);
                          if (allMembers.length === 0) {
                            return <p style={styles.helperText}>No students have joined this class yet.</p>;
                          }
                          return (
                            <>
                              <div style={styles.rosterSearchWrap}>
                                <label htmlFor={`roster-search-${cls.id}`} style={styles.rosterSearchLabel}>
                                  Search roster
                                </label>
                                <input
                                  id={`roster-search-${cls.id}`}
                                  type="search"
                                  placeholder="Name, email, or user id"
                                  value={searchText}
                                  onChange={(e) =>
                                    setRosterSearchByClass((prev) => ({ ...prev, [cls.id]: e.target.value }))
                                  }
                                  style={styles.rosterSearchInput}
                                  autoComplete="off"
                                />
                              </div>
                              {filteredMembers.length === 0 ? (
                                <p style={styles.helperText}>No students match that search.</p>
                              ) : (
                                filteredMembers.map((m) => (
                                  <div key={m.user_id} style={styles.memberRow}>
                                    <div style={styles.memberMain}>
                                      <strong>{m.full_name || m.email || m.user_id}</strong>
                                      {m.email && m.full_name ? (
                                        <div style={styles.classMeta}>{m.email}</div>
                                      ) : null}
                                    </div>
                                    <button
                                      type="button"
                                      style={styles.smallBtn}
                                      onClick={() => {
                                        const label = encodeURIComponent(m.full_name || m.email || 'Student');
                                        navigate(
                                          `/analyzer?inspectClass=${encodeURIComponent(cls.id)}&inspectStudent=${encodeURIComponent(m.user_id)}&inspectName=${label}`
                                        );
                                      }}
                                    >
                                      View recent runs
                                    </button>
                                    <button
                                      type="button"
                                      style={{ ...styles.smallBtn, ...styles.smallBtnDanger }}
                                      onClick={() => openRemoveMemberModal(cls.id, cls.name, m)}
                                    >
                                      Remove
                                    </button>
                                  </div>
                                ))
                              )}
                            </>
                          );
                        })()}
                    </div>
                  ) : null}
                </div>
              ))
            )}
          </div>
          </div>
        )}

        {role !== 'admin' && (
          <div style={styles.column}>
            <div style={styles.list}>
              <div style={styles.listHeader}>My enrolled classes</div>
              {enrolled.length === 0 ? (
                <p style={styles.helperText}>
                  You are not enrolled in any class yet. Enter the join code from your instructor on the class code
                  page after sign-in.
                </p>
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

      <RotateJoinCodeModal
        classToRotate={joinCodeRotateClass}
        loading={joinCodeRotateLoading}
        onCancel={() => {
          if (joinCodeRotateLoading) return;
          setJoinCodeRotateClass(null);
        }}
        onConfirm={async () => {
          if (!joinCodeRotateClass) return;
          try {
            setJoinCodeRotateLoading(true);
            const updated = await rotateClassJoinCode(joinCodeRotateClass.id);
            setTeaching((prev) =>
              prev.map((c) => (c.id === updated.id ? { ...c, join_code: updated.join_code } : c))
            );
            showStatus(`New join code: ${updated.join_code}`, 'success');
          } catch (err) {
            console.error('Rotate join code failed', err);
            showStatus(err?.response?.data?.detail || 'Could not generate a new join code.', 'error');
          } finally {
            setJoinCodeRotateLoading(false);
            setJoinCodeRotateClass(null);
          }
        }}
      />
      <RemoveMemberModal
        pending={memberRemovePending}
        loading={removeMemberLoading}
        onCancel={() => {
          if (removeMemberLoading) return;
          setMemberRemovePending(null);
        }}
        onConfirm={async () => {
          if (!memberRemovePending) return;
          const { classId, member } = memberRemovePending;
          try {
            setRemoveMemberLoading(true);
            await removeClassMember(classId, member.user_id);
            setRosterByClass((prev) => ({
              ...prev,
              [classId]: (prev[classId] || []).filter((x) => x.user_id !== member.user_id),
            }));
            showStatus('Student removed from class.', 'success');
          } catch (err) {
            console.error('Remove member failed', err);
            showStatus(err?.response?.data?.detail || 'Could not remove student.', 'error');
          } finally {
            setRemoveMemberLoading(false);
            setMemberRemovePending(null);
          }
        }}
      />
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

