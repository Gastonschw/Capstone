import React, { useState, useEffect, useRef, lazy, Suspense } from 'react';
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import AnalyzerPage from './pages/AnalyzerPage';
import JoinClassPage from './pages/JoinClassPage';
import { listMyClasses, getGitHubAuthStatus, setSessionId } from './api';
import { supabase, isSupabaseConfigured } from './lib/supabaseClient';
import AppLoading from './components/common/AppLoading';

const ComparisonPage = lazy(() => import('./pages/ComparisonPage'));

export default function App() {
  const [authUser, setAuthUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(isSupabaseConfigured);
  const [loginError, setLoginError] = useState(null);
  const [classGate, setClassGate] = useState({ status: 'idle' });
  const [classVersion, setClassVersion] = useState(0);
  const [callbackPending, setCallbackPending] = useState(true);
  const callback = useRef(new URLSearchParams(window.location.search));
  const currentIdentity = useRef(null);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (!supabase) return;
    let active = true;
    const update = (session) => {
      if (!active) return;
      const user = session?.user ?? null;
      if (currentIdentity.current !== user?.id) {
        currentIdentity.current = user?.id;
        setClassGate({ status: 'idle' });
      }
      setAuthUser(user);
      setAuthLoading(false);
    };
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => update(session));
    supabase.auth.getSession().then(({ data: { session }, error }) => {
      if (error && active) setLoginError(error.message);
      update(session);
    }).catch((error) => {
      if (active) { setLoginError(error.message); setAuthLoading(false); }
    });
    return () => { active = false; subscription.unsubscribe(); };
  }, []);

  // Consume OAuth results before any route gate can replace the callback URL.
  useEffect(() => {
    if (authLoading) return;
    let active = true;
    const consume = async () => {
      const hash = new URLSearchParams(window.location.hash.slice(1));
      if (hash.get('error') || hash.get('error_code')) {
        setLoginError(hash.get('error_description') || 'Sign-in was cancelled or failed. Please try again.');
        window.history.replaceState({}, '', window.location.pathname + window.location.search);
      }
      const params = callback.current;
      const result = params.get('github_auth');
      try {
        if (result === 'success') {
          const sessionId = params.get('session_id');
          if (!authUser || !sessionId) throw new Error('Sign in with the account that connected GitHub, then reconnect GitHub.');
          const status = await getGitHubAuthStatus(sessionId);
          if (!status.authenticated) throw new Error('GitHub connection could not be verified for this account.');
          if (active && currentIdentity.current === authUser.id) setSessionId(sessionId);
        } else if (result === 'error') {
          throw new Error(params.get('message') || 'GitHub authentication failed.');
        }
      } catch (error) {
        if (active) setLoginError(error.message);
      } finally {
        if (active) {
          callback.current = new URLSearchParams();
          if (result) {
            const url = new URL(window.location.href);
            ['github_auth', 'session_id', 'message'].forEach((key) => url.searchParams.delete(key));
            window.history.replaceState({}, '', url.pathname + url.search + url.hash);
          }
          setCallbackPending(false);
        }
      }
    };
    consume();
    return () => { active = false; };
  }, [authLoading, authUser?.id]);

  useEffect(() => {
    const refresh = () => setClassVersion((value) => value + 1);
    window.addEventListener('combined-analyzer-classes-refresh', refresh);
    return () => window.removeEventListener('combined-analyzer-classes-refresh', refresh);
  }, []);

  useEffect(() => {
    if (authLoading || !authUser) return;
    let active = true;
    listMyClasses().then((data) => {
      if (!active || currentIdentity.current !== authUser.id) return;
      const allowed = data.role === 'admin' || (data.teaching || []).length > 0 || (data.enrolled || []).length > 0;
      setClassGate({ status: allowed ? 'allowed' : 'need-join' });
    }).catch(() => { if (active && currentIdentity.current === authUser.id) setClassGate({ status: 'error' }); });
    return () => { active = false; };
  }, [authLoading, authUser?.id, classVersion]);

  useEffect(() => {
    if (authLoading || callbackPending || !isSupabaseConfigured) return;
    const path = location.pathname;
    if (!authUser) {
      if (path !== '/') navigate('/', { replace: true });
      return;
    }
    if (classGate.status === 'idle' || classGate.status === 'error') return;
    const needsJoin = classGate.status === 'need-join';
    if (path === '/' || (needsJoin && path !== '/join-class') || (!needsJoin && path === '/join-class')) {
      navigate(needsJoin ? '/join-class' : '/analyzer', { replace: true });
    }
  }, [authLoading, callbackPending, authUser?.id, classGate.status, location.pathname, navigate]);

  if (!isSupabaseConfigured) return <div role="alert">Authentication configuration error: set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY. Anonymous access is disabled.</div>;
  if (authLoading || callbackPending) return <AppLoading message="Signing you in…" subMessage="Verifying your account and connections." />;
  if (authUser && classGate.status === 'idle') return <AppLoading message="Loading your classes…" />;
  if (authUser && classGate.status === 'error') return <div role="alert">Unable to verify class access. <button onClick={() => setClassVersion((value) => value + 1)}>Retry</button></div>;
  if (!authUser && location.pathname !== '/') return <AppLoading message="Returning to sign in…" />;
  if (authUser && classGate.status === 'need-join' && location.pathname !== '/join-class') return <AppLoading message="Opening class enrollment…" />;

  return (
    <Suspense fallback={<AppLoading message="Loading…" />}>
      {loginError && authUser && <div role="alert">{loginError}<button onClick={() => setLoginError(null)}>Dismiss</button></div>}
      <Routes key={authUser?.id || 'signed-out'}>
        <Route path="/" element={<LandingPage loginError={loginError} onClearLoginError={() => setLoginError(null)} />} />
        <Route path="/join-class" element={<JoinClassPage />} />
        <Route path="/analyzer" element={<AnalyzerPage />} />
        <Route path="/compare" element={<ComparisonPage />} />
      </Routes>
    </Suspense>
  );
}
