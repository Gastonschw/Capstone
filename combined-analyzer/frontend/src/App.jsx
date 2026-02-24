import React, { useState, useEffect } from 'react';
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import AnalyzerPage from './pages/AnalyzerPage';
import { setCurrentUserId } from './api';
import { supabase, isSupabaseConfigured } from './lib/supabaseClient';

const LOGIN_ERROR_MESSAGE = 'Sign-in was cancelled or failed. Please try again.';

export default function App() {
  const [authUser, setAuthUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(isSupabaseConfigured);
  const [loginError, setLoginError] = useState(null);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (!isSupabaseConfigured || !supabase) {
      setAuthLoading(false);
      return;
    }
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setAuthUser(session?.user ?? null);
      setCurrentUserId(session?.user?.id ?? null);
    });
    supabase.auth.getSession().then(({ data: { session } }) => {
      setAuthUser(session?.user ?? null);
      setCurrentUserId(session?.user?.id ?? null);
      setAuthLoading(false);
    });
    return () => subscription.unsubscribe();
  }, []);

  useEffect(() => {
    if (authLoading) return;

    const pathname = location.pathname;
    const hash = window.location.hash;
    if (hash) {
      const params = new URLSearchParams(hash.slice(1));
      const error = params.get('error') || params.get('error_code');
      if (error) {
        window.history.replaceState({}, '', pathname + (window.location.search || ''));
        setLoginError(LOGIN_ERROR_MESSAGE);
        navigate('/', { replace: true });
        return;
      }
    }

    if (authUser && pathname === '/') {
      navigate('/analyzer', { replace: true });
      return;
    }

    if (!authUser && isSupabaseConfigured && pathname === '/analyzer') {
      if (!window.location.hash) {
        navigate('/', { replace: true });
      }
      return;
    }

    if (!isSupabaseConfigured && pathname === '/') {
      navigate('/analyzer', { replace: true });
    }
  }, [authLoading, authUser, location.pathname, navigate, isSupabaseConfigured]);

  if (authLoading && isSupabaseConfigured) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: '#f5f7fa' }}>
        <span style={{ color: '#666' }}>Loading…</span>
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/" element={<LandingPage loginError={loginError} onClearLoginError={() => setLoginError(null)} />} />
      <Route path="/analyzer" element={<AnalyzerPage />} />
    </Routes>
  );
}
