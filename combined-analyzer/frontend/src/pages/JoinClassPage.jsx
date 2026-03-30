import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { joinClassByCode } from '../api';
import { supabase, isSupabaseConfigured } from '../lib/supabaseClient';

const styles = {
  page: {
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '24px',
    background: 'linear-gradient(160deg, #e8eef4 0%, #d4dce6 50%, #f0f4f8 100%)',
  },
  card: {
    background: 'rgba(255,255,255,0.95)',
    borderRadius: '20px',
    boxShadow: '0 8px 32px rgba(30,58,95,0.12), 0 2px 8px rgba(0,0,0,0.06)',
    padding: '40px 36px',
    maxWidth: '420px',
    width: '100%',
    border: '1px solid rgba(255,255,255,0.8)',
  },
  title: {
    margin: '0 0 8px',
    fontSize: '22px',
    fontWeight: '700',
    color: '#1e3a5f',
  },
  subtitle: {
    margin: '0 0 24px',
    fontSize: '14px',
    color: '#4b5563',
    lineHeight: 1.5,
  },
  formGroup: {
    display: 'flex',
    gap: '8px',
    marginBottom: '12px',
  },
  input: {
    flex: 1,
    padding: '10px 12px',
    borderRadius: '10px',
    border: '1px solid #d1d5db',
    fontSize: '15px',
  },
  button: {
    padding: '10px 18px',
    borderRadius: '10px',
    border: 'none',
    backgroundColor: '#1e3a5f',
    color: '#fff',
    fontSize: '14px',
    fontWeight: '600',
    cursor: 'pointer',
    whiteSpace: 'nowrap',
  },
  buttonSecondary: {
    marginTop: '16px',
    width: '100%',
    backgroundColor: '#e5e7eb',
    color: '#374151',
  },
  error: {
    marginTop: '12px',
    padding: '10px 12px',
    borderRadius: '8px',
    backgroundColor: '#fef2f2',
    border: '1px solid #fecaca',
    color: '#7f1d1d',
    fontSize: '13px',
  },
};

export default function JoinClassPage() {
  const navigate = useNavigate();
  const [code, setCode] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    const trimmed = code.trim();
    if (!trimmed) return;
    setError('');
    setSubmitting(true);
    try {
      await joinClassByCode(trimmed);
      navigate('/analyzer', { replace: true });
    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        (err?.response?.status === 404
          ? 'No class found for that code.'
          : 'Could not join the class. Try again.');
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setSubmitting(false);
    }
  };

  const handleSignOut = async () => {
    if (supabase) {
      await supabase.auth.signOut();
    }
    navigate('/', { replace: true });
  };

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <h1 style={styles.title}>Enter class code</h1>
        <p style={styles.subtitle}>
          Your instructor will give you a join code for this course. Enter it below to continue to the analyzer.
        </p>
        <form onSubmit={handleSubmit}>
          <div style={styles.formGroup}>
            <input
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              placeholder="6-digit code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              style={styles.input}
              disabled={submitting}
              aria-label="Class join code"
            />
            <button type="submit" style={styles.button} disabled={submitting || !code.trim()}>
              {submitting ? 'Joining…' : 'Join'}
            </button>
          </div>
        </form>
        {error ? <div style={styles.error}>{error}</div> : null}
        {isSupabaseConfigured ? (
          <button type="button" style={{ ...styles.button, ...styles.buttonSecondary }} onClick={handleSignOut}>
            Sign out
          </button>
        ) : null}
      </div>
    </div>
  );
}
