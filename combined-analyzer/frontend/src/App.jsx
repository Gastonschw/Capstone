import React, { useState, useEffect } from 'react';
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import AnalyzerPage from './pages/AnalyzerPage';
import ComparisonPage from './pages/ComparisonPage';
import JoinClassPage from './pages/JoinClassPage';
import { setCurrentUserId, listMyClasses } from './api';
import { supabase, isSupabaseConfigured } from './lib/supabaseClient';

const LOGIN_ERROR_MESSAGE = 'Sign-in was cancelled or failed. Please try again.';

export default function App() {
  const [authUser, setAuthUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(isSupabaseConfigured);
  const [loginError, setLoginError] = useState(null);
  const [classGate, setClassGate] = useState({ status: 'idle' });
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
    if (!isSupabaseConfigured || !authUser) {
      setClassGate({ status: 'skipped' });
      return;
    }
    let cancelled = false;
    setClassGate({ status: 'loading' });
    listMyClasses()
      .then((data) => {
        if (cancelled) return;
        const role = data.role || 'general';
        const enrolled = data.enrolled || [];
        if (role === 'admin') {
          setClassGate({ status: 'admin' });
        } else if (enrolled.length === 0) {
          setClassGate({ status: 'need-join' });
        } else {
          setClassGate({ status: 'student-ok' });
        }
      })
      .catch(() => {
        if (cancelled) return;
        setClassGate({ status: 'error' });
      });
    return () => {
      cancelled = true;
    };
  }, [authLoading, authUser, isSupabaseConfigured, location.pathname]);

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
      if (!isSupabaseConfigured) {
        navigate('/analyzer', { replace: true });
        return;
      }
      return;
    }

    if (!authUser && isSupabaseConfigured && (pathname === '/analyzer' || pathname === '/compare' || pathname === '/join-class')) {
      if (!window.location.hash) {
        navigate('/', { replace: true });
      }
      return;
    }

    if (!isSupabaseConfigured && pathname === '/') {
      navigate('/analyzer', { replace: true });
    }
  }, [authLoading, authUser, location.pathname, navigate, isSupabaseConfigured]);

  useEffect(() => {
    if (authLoading) return;
    if (!authUser || !isSupabaseConfigured) return;
    if (classGate.status === 'idle' || classGate.status === 'loading') return;
    if (classGate.status !== 'need-join' && classGate.status !== 'admin' && classGate.status !== 'student-ok' && classGate.status !== 'error') return;

    const pathname = location.pathname;
    const needsJoin = classGate.status === 'need-join';

    if (pathname === '/' && authUser) {
      navigate(needsJoin ? '/join-class' : '/analyzer', { replace: true });
      return;
    }

    if ((pathname === '/analyzer' || pathname === '/compare') && needsJoin) {
      navigate('/join-class', { replace: true });
      return;
    }

    if (pathname === '/join-class' && !needsJoin) {
      navigate('/analyzer', { replace: true });
    }
  }, [authLoading, authUser, isSupabaseConfigured, location.pathname, classGate.status, navigate]);

  const gatePending =
    isSupabaseConfigured && authUser && (classGate.status === 'idle' || classGate.status === 'loading');

  if ((authLoading && isSupabaseConfigured) || gatePending) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: '#f5f7fa' }}>
        <span style={{ color: '#666' }}>Loading…</span>
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/" element={<LandingPage loginError={loginError} onClearLoginError={() => setLoginError(null)} />} />
      <Route path="/join-class" element={<JoinClassPage />} />
      <Route path="/analyzer" element={<AnalyzerPage />} />
      <Route path="/compare" element={<ComparisonPage />} />
    </Routes>
  );
}
