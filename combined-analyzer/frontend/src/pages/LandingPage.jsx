import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase, isSupabaseConfigured } from '../lib/supabaseClient';

function GoogleIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" style={{ flexShrink: 0 }} aria-hidden>
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
    </svg>
  );
}

const styles = {
  page: {
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '24px',
    background: 'linear-gradient(160deg, #e8eef4 0%, #d4dce6 50%, #f0f4f8 100%)',
    position: 'relative',
    overflow: 'hidden',
  },
  pageDecoration: {
    position: 'absolute',
    borderRadius: '50%',
    opacity: 0.4,
    pointerEvents: 'none',
  },
  card: {
    background: 'rgba(255,255,255,0.95)',
    borderRadius: '20px',
    boxShadow: '0 8px 32px rgba(30,58,95,0.12), 0 2px 8px rgba(0,0,0,0.06)',
    padding: '56px 48px',
    maxWidth: '440px',
    width: '100%',
    textAlign: 'center',
    position: 'relative',
    backdropFilter: 'blur(10px)',
    border: '1px solid rgba(255,255,255,0.8)',
  },
  logoWrap: {
    width: '72px',
    height: '72px',
    margin: '0 auto 24px',
    borderRadius: '18px',
    background: 'linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '36px',
    boxShadow: '0 4px 14px rgba(30,58,95,0.35)',
  },
  badge: {
    display: 'inline-block',
    fontSize: '11px',
    fontWeight: '600',
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    color: '#2d5a87',
    backgroundColor: 'rgba(45,90,135,0.1)',
    padding: '6px 12px',
    borderRadius: '20px',
    marginBottom: '16px',
  },
  title: {
    margin: '0 0 12px',
    fontSize: '28px',
    fontWeight: '700',
    color: '#1e3a5f',
    letterSpacing: '-0.02em',
    lineHeight: 1.2,
  },
  subtitle: {
    margin: '0 0 32px',
    fontSize: '15px',
    color: '#5a6c7d',
    lineHeight: 1.6,
    maxWidth: '320px',
    marginLeft: 'auto',
    marginRight: 'auto',
  },
  error: {
    padding: '14px 16px',
    marginBottom: '24px',
    backgroundColor: 'rgba(220,53,69,0.08)',
    color: '#721c24',
    borderRadius: '12px',
    fontSize: '14px',
    lineHeight: 1.4,
    border: '1px solid rgba(220,53,69,0.2)',
  },
  btn: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '12px',
    padding: '14px 24px',
    borderRadius: '12px',
    border: 'none',
    fontSize: '15px',
    fontWeight: '600',
    cursor: 'pointer',
    width: '100%',
    transition: 'box-shadow 0.2s, transform 0.1s',
  },
  btnGoogle: {
    background: '#fff',
    color: '#3c4043',
    border: '1px solid #dadce0',
    boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
  },
  btnPrimary: {
    background: 'linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%)',
    color: '#fff',
    boxShadow: '0 4px 14px rgba(30,58,95,0.35)',
  },
};

export default function LandingPage({ loginError = null, onClearLoginError }) {
  const [signingIn, setSigningIn] = useState(false);
  const navigate = useNavigate();

  const handleSignIn = async () => {
    if (!supabase?.auth) return;
    onClearLoginError?.();
    setSigningIn(true);
    try {
      await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: { redirectTo: `${window.location.origin}/analyzer` },
      });
    } finally {
      setSigningIn(false);
    }
  };

  const handleContinueToAnalyzer = () => {
    navigate('/analyzer');
  };

  const pageDecorations = (
    <>
      <div
        style={{
          ...styles.pageDecoration,
          width: '400px',
          height: '400px',
          background: 'radial-gradient(circle, rgba(45,90,135,0.1) 0%, transparent 70%)',
          top: '-150px',
          right: '-100px',
        }}
      />
      <div
        style={{
          ...styles.pageDecoration,
          width: '300px',
          height: '300px',
          background: 'radial-gradient(circle, rgba(30,58,95,0.06) 0%, transparent 70%)',
          bottom: '-80px',
          left: '-80px',
        }}
      />
    </>
  );

  const cardContent = (isGoogleAuth) => (
    <>
      <div style={styles.logoWrap}>&#128202;</div>
      <div style={styles.badge}>ERD + Integrity Analysis</div>
      <h1 style={styles.title}>Combined Analyzer</h1>
      <p style={styles.subtitle}>
        {isGoogleAuth
          ? 'Sign in to analyze your codebase with ERD and Integrity reports.'
          : 'Sign-in is not configured; continue to use the app.'}
      </p>
      {isGoogleAuth && loginError && (
        <div style={styles.error}>{loginError}</div>
      )}
      {isGoogleAuth ? (
        <button
          type="button"
          style={{ ...styles.btn, ...styles.btnGoogle }}
          onClick={handleSignIn}
          disabled={signingIn}
          onMouseEnter={(e) => {
            if (!signingIn) {
              e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)';
              e.currentTarget.style.transform = 'translateY(-1px)';
            }
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.boxShadow = '0 1px 2px rgba(0,0,0,0.05)';
            e.currentTarget.style.transform = 'translateY(0)';
          }}
        >
          <GoogleIcon />
          {signingIn ? 'Signing in…' : 'Sign in with Google'}
        </button>
      ) : (
        <button
          type="button"
          style={{ ...styles.btn, ...styles.btnPrimary }}
          onClick={handleContinueToAnalyzer}
          onMouseEnter={(e) => {
            e.currentTarget.style.boxShadow = '0 6px 20px rgba(30,58,95,0.4)';
            e.currentTarget.style.transform = 'translateY(-1px)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.boxShadow = '0 4px 14px rgba(30,58,95,0.35)';
            e.currentTarget.style.transform = 'translateY(0)';
          }}
        >
          Continue to Analyzer
        </button>
      )}
    </>
  );

  if (!isSupabaseConfigured) {
    return (
      <div style={styles.page}>
        {pageDecorations}
        <div style={styles.card}>{cardContent(false)}</div>
      </div>
    );
  }

  return (
    <div style={styles.page}>
      {pageDecorations}
      <div style={styles.card}>{cardContent(true)}</div>
    </div>
  );
}
