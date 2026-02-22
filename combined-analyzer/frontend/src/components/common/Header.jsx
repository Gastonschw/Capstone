import React, { useState } from 'react';
import { supabase } from '../../lib/supabaseClient';

const styles = {
  header: {
    background: 'linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%)',
    color: '#fff',
    padding: '16px 24px',
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: '16px',
    flexWrap: 'wrap',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
  },
  logo: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  logoIcon: {
    fontSize: '28px',
  },
  title: {
    margin: 0,
    fontSize: '22px',
    fontWeight: '600',
  },
  subtitle: {
    margin: 0,
    fontSize: '12px',
    opacity: 0.8,
    marginTop: '2px',
  },
  rightSection: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '16px',
    marginLeft: 'auto',
    flexWrap: 'wrap',
  },
  controls: {
    display: 'flex',
    gap: '12px',
    alignItems: 'flex-start',
    flexWrap: 'wrap',
  },
  controlGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    minWidth: '220px',
  },
  controlGroupWide: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    minWidth: '280px',
  },
  controlLabel: {
    fontSize: '11px',
    fontWeight: '600',
    letterSpacing: '0.03em',
    textTransform: 'uppercase',
    opacity: 0.9,
  },
  controlInput: {
    height: '34px',
    borderRadius: '8px',
    border: '1px solid rgba(255,255,255,0.35)',
    backgroundColor: 'rgba(255,255,255,0.92)',
    color: '#1f2937',
    padding: '0 10px',
    outline: 'none',
    fontSize: '13px',
    width: '100%',
  },
  selectInput: {
    cursor: 'pointer',
  },
  selectOption: {
    color: '#1f2937',
    backgroundColor: '#fff',
  },
  errorText: {
    fontSize: '11px',
    color: '#ffd6d6',
  },
  badge: {
    backgroundColor: 'rgba(255,255,255,0.2)',
    padding: '6px 12px',
    borderRadius: '16px',
    fontSize: '12px',
    fontWeight: '500',
    alignSelf: 'flex-end',
  },
  authSection: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  authUser: {
    fontSize: '12px',
    opacity: 0.95,
    maxWidth: '160px',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  authBtn: {
    padding: '8px 14px',
    borderRadius: '8px',
    border: '1px solid rgba(255,255,255,0.5)',
    background: 'rgba(255,255,255,0.15)',
    color: '#fff',
    fontSize: '13px',
    fontWeight: '500',
    cursor: 'pointer',
  },
  authBtnSignOut: {
    background: 'transparent',
    borderColor: 'rgba(255,255,255,0.4)',
  },
};

export default function Header({
  availableModels = [],
  selectedModel = '',
  onModelChange,
  apiKey = '',
  onApiKeyChange,
  modelsLoading = false,
  modelsError = '',
  authUser = null,
  authLoading = false,
  supabaseConfigured = false,
}) {
  const [signingIn, setSigningIn] = useState(false);
  const hasModels = availableModels.length > 0;

  const handleSignIn = async () => {
    if (!supabase?.auth) return;
    setSigningIn(true);
    try {
      await supabase.auth.signInWithOAuth({ provider: 'google' });
    } finally {
      setSigningIn(false);
    }
  };

  const handleSignOut = async () => {
    if (!supabase?.auth) return;
    await supabase.auth.signOut();
  };

  return (
    <header style={styles.header}>
      <div style={styles.logo}>
        <span style={styles.logoIcon}>&#128202;</span>
        <div>
          <h1 style={styles.title}>Combined Analyzer</h1>
          <p style={styles.subtitle}>ERD + Integrity Analysis Platform</p>
        </div>
      </div>

      <div style={styles.rightSection}>
        {supabaseConfigured && (
          <div style={styles.authSection}>
            {authLoading ? (
              <span style={styles.authUser}>Loading…</span>
            ) : authUser ? (
              <>
                <span style={styles.authUser} title={authUser.email}>
                  {authUser.email || authUser.user_metadata?.email || 'Signed in'}
                </span>
                <button
                  type="button"
                  style={{ ...styles.authBtn, ...styles.authBtnSignOut }}
                  onClick={handleSignOut}
                >
                  Sign out
                </button>
              </>
            ) : (
              <button
                type="button"
                style={styles.authBtn}
                onClick={handleSignIn}
                disabled={signingIn}
              >
                {signingIn ? 'Signing in…' : 'Sign in with Google'}
              </button>
            )}
          </div>
        )}
        <div style={styles.controls}>
          <div style={styles.controlGroup}>
            <label style={styles.controlLabel}>Chat Model</label>
            <select
              value={selectedModel}
              onChange={(e) => onModelChange?.(e.target.value)}
              style={{ ...styles.controlInput, ...styles.selectInput }}
              disabled={modelsLoading || !hasModels}
            >
              {modelsLoading ? (
                <option value="" style={styles.selectOption}>Loading models...</option>
              ) : (
                availableModels.map((model) => (
                  <option key={model.id} value={model.id} style={styles.selectOption}>
                    {model.name || model.id}
                  </option>
                ))
              )}
              {!modelsLoading && !hasModels && (
                <option value="" style={styles.selectOption}>No models available</option>
              )}
            </select>
            {modelsError && <span style={styles.errorText}>{modelsError}</span>}
          </div>

          <div style={styles.controlGroupWide}>
            <label style={styles.controlLabel}>TAMU API Key</label>
            <input
              type="password"
              value={apiKey}
              placeholder="Enter your TAMU API key"
              onChange={(e) => onApiKeyChange?.(e.target.value)}
              style={styles.controlInput}
              autoComplete="off"
            />
          </div>
        </div>

        <div style={styles.badge}>
          v1.0.0
        </div>
      </div>
    </header>
  );
}
