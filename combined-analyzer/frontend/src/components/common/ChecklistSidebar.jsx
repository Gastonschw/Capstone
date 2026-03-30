import React, { useCallback, useEffect, useId, useRef, useState } from 'react';
import { supabase } from '../../lib/supabaseClient';

const STORAGE_PREFIX = 'combined_analyzer_checklist_v1';
const PANEL_WIDTH = 320;
const REMOTE_SAVE_DEBOUNCE_MS = 400;

function cacheStorageKey(userId) {
  return `${STORAGE_PREFIX}:${userId ?? 'local'}`;
}

function makeId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `chk-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function normalizeItems(raw) {
  if (!Array.isArray(raw)) return [];
  return raw
    .filter((x) => x && typeof x.text === 'string')
    .map((x) => ({
      id: typeof x.id === 'string' ? x.id : makeId(),
      text: x.text.slice(0, 2000),
      done: Boolean(x.done),
    }));
}

function loadItemsFromCache(userId) {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(cacheStorageKey(userId));
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return normalizeItems(parsed);
  } catch {
    return [];
  }
}

function saveItemsToCache(userId, items) {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(cacheStorageKey(userId), JSON.stringify(items));
  } catch {
    /* ignore quota / private mode */
  }
}

const styles = {
  root: {
    position: 'fixed',
    top: 0,
    right: 0,
    height: '100vh',
    zIndex: 200,
    display: 'flex',
    alignItems: 'stretch',
    pointerEvents: 'none',
  },
  tab: {
    pointerEvents: 'auto',
    alignSelf: 'center',
    marginRight: 0,
    writingMode: 'vertical-rl',
    textOrientation: 'mixed',
    transform: 'rotate(180deg)',
    backgroundColor: '#1e3a5f',
    color: '#fff',
    border: 'none',
    borderRadius: '8px 0 0 8px',
    padding: '14px 10px',
    fontSize: '13px',
    fontWeight: 600,
    letterSpacing: '0.06em',
    textTransform: 'uppercase',
    cursor: 'pointer',
    boxShadow: '-2px 0 8px rgba(0, 0, 0, 0.12)',
    fontFamily: 'inherit',
  },
  tabOpen: {
    borderRadius: 0,
    alignSelf: 'stretch',
    transform: 'none',
    writingMode: 'horizontal-tb',
    textOrientation: 'mixed',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '44px',
    minWidth: '44px',
    padding: '8px 6px',
  },
  panel: {
    width: PANEL_WIDTH,
    maxWidth: 'min(100vw, 360px)',
    backgroundColor: '#fff',
    borderLeft: '1px solid #e0e0e0',
    boxShadow: '-4px 0 24px rgba(0, 0, 0, 0.08)',
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    pointerEvents: 'auto',
    flexShrink: 0,
    transition: 'transform 0.22s ease, opacity 0.22s ease, visibility 0.22s ease',
  },
  panelClosed: {
    transform: `translateX(${PANEL_WIDTH}px)`,
    opacity: 0,
    visibility: 'hidden',
    width: 0,
    minWidth: 0,
    overflow: 'hidden',
    border: 'none',
    boxShadow: 'none',
  },
  panelHeader: {
    padding: '16px',
    borderBottom: '1px solid #e0e0e0',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '12px',
    flexShrink: 0,
  },
  panelTitle: {
    margin: 0,
    fontSize: '14px',
    fontWeight: 600,
    color: '#333',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  closeBtn: {
    background: '#eef2f7',
    border: '1px solid #d0d7de',
    color: '#1e3a5f',
    borderRadius: '6px',
    padding: '6px 12px',
    fontSize: '12px',
    fontWeight: 600,
    cursor: 'pointer',
    fontFamily: 'inherit',
  },
  form: {
    display: 'flex',
    gap: '8px',
    padding: '12px 16px',
    borderBottom: '1px solid #e0e0e0',
    flexShrink: 0,
  },
  input: {
    flex: 1,
    minWidth: 0,
    padding: '10px 12px',
    borderRadius: '8px',
    border: '1px solid #d0d7de',
    fontSize: '14px',
    fontFamily: 'inherit',
    outline: 'none',
  },
  addBtn: {
    backgroundColor: '#1e3a5f',
    color: '#fff',
    border: 'none',
    padding: '10px 14px',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: 500,
    fontFamily: 'inherit',
    whiteSpace: 'nowrap',
  },
  list: {
    flex: 1,
    overflowY: 'auto',
    padding: '8px',
    margin: 0,
    listStyle: 'none',
  },
  row: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '10px',
    padding: '10px 12px',
    borderRadius: '8px',
    marginBottom: '6px',
    backgroundColor: '#f8fafc',
    border: '1px solid #e8eef4',
  },
  rowDone: {
    opacity: 0.72,
  },
  checkbox: {
    marginTop: '2px',
    width: '18px',
    height: '18px',
    cursor: 'pointer',
    flexShrink: 0,
  },
  label: {
    flex: 1,
    fontSize: '14px',
    color: '#333',
    lineHeight: 1.45,
    cursor: 'pointer',
    wordBreak: 'break-word',
  },
  labelDone: {
    textDecoration: 'line-through',
    color: '#666',
  },
  removeBtn: {
    flexShrink: 0,
    background: 'transparent',
    border: 'none',
    color: '#94a3b8',
    cursor: 'pointer',
    padding: '4px 6px',
    fontSize: '18px',
    lineHeight: 1,
    borderRadius: '4px',
    fontFamily: 'inherit',
  },
  empty: {
    padding: '32px 20px',
    textAlign: 'center',
    color: '#666',
    fontSize: '14px',
  },
};

export default function ChecklistSidebar({ userId = null, supabaseConfigured = false }) {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState(() => loadItemsFromCache(userId));
  const [draft, setDraft] = useState('');
  const formId = useId();
  const allowRemoteSaveRef = useRef(!userId || !supabaseConfigured);
  const itemsRef = useRef(items);
  itemsRef.current = items;

  useEffect(() => {
    setItems(loadItemsFromCache(userId));
  }, [userId]);

  useEffect(() => {
    saveItemsToCache(userId, items);
  }, [userId, items]);

  useEffect(() => {
    if (!supabaseConfigured || !supabase || !userId) {
      allowRemoteSaveRef.current = true;
      return;
    }

    allowRemoteSaveRef.current = false;
    let cancelled = false;

    (async () => {
      try {
        const { data, error } = await supabase
          .from('user_checklists')
          .select('items')
          .eq('user_id', userId)
          .maybeSingle();

        if (cancelled) return;
        if (error) {
          console.warn('Checklist fetch failed:', error.message);
          return;
        }

        if (data && data.items !== undefined && data.items !== null) {
          const normalized = normalizeItems(data.items);
          setItems(normalized);
          saveItemsToCache(userId, normalized);
        }
      } finally {
        if (!cancelled) {
          allowRemoteSaveRef.current = true;
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [userId, supabaseConfigured]);

  useEffect(() => {
    if (!userId || !supabaseConfigured || !supabase) return;

    const handle = setTimeout(() => {
      if (!allowRemoteSaveRef.current) return;
      const payload = itemsRef.current;
      supabase
        .from('user_checklists')
        .upsert({ user_id: userId, items: payload }, { onConflict: 'user_id' })
        .then(({ error }) => {
          if (error) console.warn('Checklist save failed:', error.message);
        });
    }, REMOTE_SAVE_DEBOUNCE_MS);

    return () => clearTimeout(handle);
  }, [userId, supabaseConfigured, items]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e) => {
      if (e.key === 'Escape') setOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  const addItem = useCallback(() => {
    const text = draft.trim();
    if (!text) return;
    setItems((prev) => [...prev, { id: makeId(), text, done: false }]);
    setDraft('');
  }, [draft]);

  const toggleDone = useCallback((id) => {
    setItems((prev) =>
      prev.map((item) => (item.id === id ? { ...item, done: !item.done } : item)),
    );
  }, []);

  const removeItem = useCallback((id) => {
    setItems((prev) => prev.filter((item) => item.id !== id));
  }, []);

  return (
    <div className="checklist-sidebar-root" style={styles.root}>
      {!open && (
        <button
          type="button"
          style={styles.tab}
          onClick={() => setOpen(true)}
          aria-expanded={false}
          aria-controls={formId}
        >
          Checklist
        </button>
      )}
      <div
        id={formId}
        style={{
          ...styles.panel,
          ...(!open ? styles.panelClosed : {}),
          display: 'flex',
        }}
        aria-hidden={!open}
      >
        <div style={styles.panelHeader}>
          <h2 style={styles.panelTitle}>Checklist</h2>
          <button
            type="button"
            style={styles.closeBtn}
            onClick={() => setOpen(false)}
            aria-label="Close checklist"
          >
            Close
          </button>
        </div>
        <form
          style={styles.form}
          onSubmit={(e) => {
            e.preventDefault();
            addItem();
          }}
        >
          <input
            type="text"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Add a task…"
            style={styles.input}
            autoComplete="off"
            maxLength={2000}
            aria-label="New checklist item"
          />
          <button type="submit" style={styles.addBtn}>
            Add
          </button>
        </form>
        {open && items.length === 0 ? (
          <p style={styles.empty}>No items yet. Add something above.</p>
        ) : (
          <ul style={styles.list}>
            {items.map((item) => (
              <li
                key={item.id}
                style={{
                  ...styles.row,
                  ...(item.done ? styles.rowDone : {}),
                }}
              >
                <input
                  type="checkbox"
                  id={`${formId}-${item.id}`}
                  checked={item.done}
                  onChange={() => toggleDone(item.id)}
                  style={styles.checkbox}
                />
                <label
                  htmlFor={`${formId}-${item.id}`}
                  style={{
                    ...styles.label,
                    ...(item.done ? styles.labelDone : {}),
                  }}
                >
                  {item.text}
                </label>
                <button
                  type="button"
                  style={styles.removeBtn}
                  onClick={() => removeItem(item.id)}
                  aria-label={`Remove: ${item.text.slice(0, 80)}`}
                  title="Remove"
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
      {open && (
        <button
          type="button"
          style={{ ...styles.tab, ...styles.tabOpen }}
          onClick={() => setOpen(false)}
          aria-expanded
          aria-controls={formId}
          title="Collapse checklist tab"
        >
          ‹
        </button>
      )}
    </div>
  );
}
