import axios from 'axios';
import { supabase } from './lib/supabaseClient';

const SESSION_ID_STORAGE_KEY = 'github_session_id';
let currentUserId = null;
let identityInitialized = false;
let userRequests = new AbortController();

export function getCurrentUserId() {
  return currentUserId;
}

function clearCredentials() {
  localStorage.removeItem(SESSION_ID_STORAGE_KEY);
  localStorage.removeItem('github_session_owner');
  localStorage.removeItem('supabase_user_id');
  localStorage.removeItem('tamu_chat_api_key');
  localStorage.removeItem('credential_owner');
}

supabase?.auth.onAuthStateChange((_event, session) => {
  const nextId = session?.user?.id ?? null;
  if (nextId !== currentUserId || !identityInitialized) {
    if (identityInitialized) {
      userRequests.abort();
      userRequests = new AbortController();
    }
    if (localStorage.getItem('credential_owner') !== nextId) clearCredentials();
    if (nextId) localStorage.setItem('credential_owner', nextId);
    currentUserId = nextId;
    identityInitialized = true;
  }
});

export function setSessionId(sessionId) {
  if (!sessionId || !currentUserId) {
    localStorage.removeItem(SESSION_ID_STORAGE_KEY);
    localStorage.removeItem('github_session_owner');
  } else {
    localStorage.setItem(SESSION_ID_STORAGE_KEY, sessionId);
    localStorage.setItem('github_session_owner', currentUserId);
  }
}

function getSessionId() {
  return currentUserId && localStorage.getItem('github_session_owner') === currentUserId
    ? localStorage.getItem(SESSION_ID_STORAGE_KEY) : null;
}

async function accessToken() {
  if (!supabase) throw new Error('Supabase authentication is not configured.');
  const { data: { session }, error } = await supabase.auth.getSession();
  if (error || !session?.access_token) throw new Error('Please sign in to continue.');
  return session.access_token;
}

export async function signOut() {
  try {
    await logoutGitHub();
  } finally {
    clearCredentials();
    userRequests.abort();
    userRequests = new AbortController();
    try {
      const result = await supabase?.auth.signOut();
      if (result?.error) throw result.error;
    } finally {
      clearCredentials();
      window.dispatchEvent(new Event('combined-analyzer-credentials-cleared'));
    }
  }
}

const API_BASE = import.meta.env.VITE_API_URL || '/api';
const api = axios.create({ baseURL: API_BASE, withCredentials: true });

api.interceptors.request.use(async (config) => {
  const signal = userRequests.signal;
  config.headers.Authorization = `Bearer ${await accessToken()}`;
  config.signal = signal;
  const sessionId = getSessionId();
  if (sessionId && !config.headers['X-Session-Id']) config.headers['X-Session-Id'] = sessionId;
  return config;
});

// ============== Repository Management ==============

export async function listRepositories(opts = {}) {
  const signal = userRequests.signal;
  const params = {};
  if (opts.classId && opts.studentUserId) {
    params.class_id = opts.classId;
    params.student_user_id = opts.studentUserId;
  }
  const explicitPage = opts.limit !== undefined || opts.offset !== undefined;
  const limit = opts.limit ?? 50;
  let offset = opts.offset ?? 0;
  const repositories = [];
  do {
    const response = await api.get('/repositories', { params: { ...params, limit, offset } });
    if (signal.aborted) throw new axios.CanceledError('Account changed');
    repositories.push(...response.data);
    if (explicitPage || response.data.length < limit) return repositories;
    offset += limit;
  } while (true);
}

export async function getRepository(repositoryId) {
  const response = await api.get(`/repository/${repositoryId}`);
  return response.data;
}

export async function deleteRepository(repositoryId) {
  const response = await api.delete(`/repository/${repositoryId}`);
  return response.data;
}

export async function updateFileSelection(repositoryId, fileIds, isSelected, analysisType) {
  const response = await api.put(`/repository/${repositoryId}/files/selection`, {
    file_ids: fileIds,
    is_selected: isSelected,
    analysis_type: analysisType,
  });
  return response.data;
}

export async function rediscoverFiles(repositoryId, apiKey = '') {
  const response = await api.post(`/repository/${repositoryId}/rediscover`, null, {
    headers: apiKey ? { 'X-TAMU-API-Key': apiKey } : {},
  });
  return response.data;
}

// ============== Folder Upload ==============

export async function uploadFolder(zipFile, name = null, apiKey = '') {
  const formData = new FormData();
  formData.append('file', zipFile);
  if (name) {
    formData.append('name', name);
  }

  const headers = { 'Content-Type': 'multipart/form-data' };
  if (apiKey) {
    headers['X-TAMU-API-Key'] = apiKey;
  }

  const response = await api.post('/upload-folder', formData, { headers });

  return response.data;
}

// ============== GitHub OAuth ==============

export async function initiateGitHubAuth() {
  const response = await api.post('/github/auth');
  window.location.assign(response.data.authorization_url);
}

export async function getGitHubAuthStatus(sessionId = null) {
  const response = await api.get('/github/status', {
    headers: sessionId ? { 'X-Session-Id': sessionId } : {},
  });
  return response.data;
}

export async function getGitHubRepos() {
  const response = await api.get('/github/repos');
  return response.data;
}

export async function importGitHubRepo(repoFullName, apiKey = '') {
  const body = { repo_full_name: repoFullName };
  if (apiKey) body.api_key = apiKey;
  const headers = {};
  if (apiKey) headers['X-TAMU-API-Key'] = apiKey;
  const response = await api.post('/github/import', body, { headers });
  return response.data;
}

export async function logoutGitHub() {
  const response = await api.post('/github/logout');
  return response.data;
}

// ============== ERD Analysis ==============

export async function startERDAnalysis(repositoryId, apiKey = '', model = '') {
  const body = {};
  if (apiKey) body.api_key = apiKey;
  if (model) body.model = model;
  const headers = {};
  if (apiKey) headers['X-TAMU-API-Key'] = apiKey;
  const response = await api.post(`/erd/repository/${repositoryId}/analyze`, body, { headers });
  return response.data;
}

export async function listERDAnalyses(repositoryId) {
  const response = await api.get(`/erd/repository/${repositoryId}/analyses`);
  return response.data;
}

export async function getERDAnalysis(analysisId) {
  const response = await api.get(`/erd/analysis/${analysisId}`);
  return response.data;
}

// ============== Integrity Analysis ==============

export async function startIntegrityAnalysis(repositoryId, apiKey = '', model = '') {
  const body = {};
  if (apiKey) body.api_key = apiKey;
  if (model) body.model = model;
  const headers = {};
  if (apiKey) headers['X-TAMU-API-Key'] = apiKey;
  const response = await api.post(`/integrity/repository/${repositoryId}/analyze`, body, { headers });
  return response.data;
}

export async function listIntegrityAnalyses(repositoryId) {
  const response = await api.get(`/integrity/repository/${repositoryId}/analyses`);
  return response.data;
}

export async function getIntegrityAnalysis(analysisId) {
  const response = await api.get(`/integrity/analysis/${analysisId}`);
  return response.data;
}

// ============== Compliance Analysis ==============

export async function startComplianceAnalysis(repositoryId, apiKey = '', model = '') {
  const body = {};
  if (apiKey) body.api_key = apiKey;
  if (model) body.model = model;
  const headers = {};
  if (apiKey) headers['X-TAMU-API-Key'] = apiKey;
  const response = await api.post(`/compliance/repository/${repositoryId}/analyze`, body, { headers });
  return response.data;
}

export async function listComplianceAnalyses(repositoryId) {
  const response = await api.get(`/compliance/repository/${repositoryId}/analyses`);
  return response.data;
}

export async function getComplianceAnalysis(analysisId) {
  const response = await api.get(`/compliance/analysis/${analysisId}`);
  return response.data;
}

// ============== Correctness Analysis ==============

export async function startCorrectnessAnalysis(repositoryId, apiKey = '', model = '') {
  const body = {};
  if (apiKey) body.api_key = apiKey;
  if (model) body.model = model;
  const headers = {};
  if (apiKey) headers['X-TAMU-API-Key'] = apiKey;
  const response = await api.post(`/correctness/repository/${repositoryId}/analyze`, body, { headers });
  return response.data;
}

export async function listCorrectnessAnalyses(repositoryId) {
  const response = await api.get(`/correctness/repository/${repositoryId}/analyses`);
  return response.data;
}

export async function getCorrectnessAnalysis(analysisId) {
  const response = await api.get(`/correctness/analysis/${analysisId}`);
  return response.data;
}

// ============== Usability Analysis ==============

export async function startUsabilityAnalysis(repositoryId, apiKey = '', model = '') {
  const body = {};
  if (apiKey) body.api_key = apiKey;
  if (model) body.model = model;
  const headers = {};
  if (apiKey) headers['X-TAMU-API-Key'] = apiKey;
  const response = await api.post(`/usability/repository/${repositoryId}/analyze`, body, { headers });
  return response.data;
}

export async function listUsabilityAnalyses(repositoryId) {
  const response = await api.get(`/usability/repository/${repositoryId}/analyses`);
  return response.data;
}

export async function getUsabilityAnalysis(analysisId) {
  const response = await api.get(`/usability/analysis/${analysisId}`);
  return response.data;
}

// ============== Maintainability Analysis ==============

export async function startMaintainabilityAnalysis(repositoryId, apiKey = '', model = '') {
  const body = {};
  if (apiKey) body.api_key = apiKey;
  if (model) body.model = model;
  const headers = {};
  if (apiKey) headers['X-TAMU-API-Key'] = apiKey;
  const response = await api.post(`/maintainability/repository/${repositoryId}/analyze`, body, { headers });
  return response.data;
}

export async function listMaintainabilityAnalyses(repositoryId) {
  const response = await api.get(`/maintainability/repository/${repositoryId}/analyses`);
  return response.data;
}

export async function getMaintainabilityAnalysis(analysisId) {
  const response = await api.get(`/maintainability/analysis/${analysisId}`);
  return response.data;
}

// ============== ISO Analysis Helpers ==============

export const ISO_ANALYSIS_TYPES = ['integrity', 'compliance', 'correctness', 'usability', 'maintainability'];

export const ISO_ANALYSIS_LABELS = {
  integrity: 'Integrity',
  compliance: 'Compliance',
  correctness: 'Correctness',
  usability: 'Usability',
  maintainability: 'Maintainability',
};

const isoListAnalysisMap = {
  integrity: listIntegrityAnalyses,
  compliance: listComplianceAnalyses,
  correctness: listCorrectnessAnalyses,
  usability: listUsabilityAnalyses,
  maintainability: listMaintainabilityAnalyses,
};

const isoGetAnalysisMap = {
  integrity: getIntegrityAnalysis,
  compliance: getComplianceAnalysis,
  correctness: getCorrectnessAnalysis,
  usability: getUsabilityAnalysis,
  maintainability: getMaintainabilityAnalysis,
};

export async function listIsoAnalysesByType(type, repositoryId) {
  const listFn = isoListAnalysisMap[type];
  if (!listFn) {
    throw new Error(`Unsupported ISO analysis type: ${type}`);
  }
  return listFn(repositoryId);
}

export async function getIsoAnalysisByType(type, analysisId) {
  const getFn = isoGetAnalysisMap[type];
  if (!getFn) {
    throw new Error(`Unsupported ISO analysis type: ${type}`);
  }
  return getFn(analysisId);
}

// ============== Polling ==============

const analysisGetters = {
  erd: getERDAnalysis,
  integrity: getIntegrityAnalysis,
  compliance: getComplianceAnalysis,
  correctness: getCorrectnessAnalysis,
  usability: getUsabilityAnalysis,
  maintainability: getMaintainabilityAnalysis,
};

export function pollAnalysis(type, analysisId, onUpdate, intervalMs = 5000, onError = () => {}) {
  const getAnalysis = analysisGetters[type];
  if (!getAnalysis) throw new Error(`Unsupported analysis type: ${type}`);
  let cancelled = false;
  let timer;
  let errorCount = 0;
  const signal = userRequests.signal;
  const cancel = () => {
    cancelled = true;
    clearTimeout(timer);
    signal.removeEventListener('abort', cancel);
  };
  signal.addEventListener('abort', cancel, { once: true });
  const poll = async () => {
    try {
      const analysis = await getAnalysis(analysisId);
      if (cancelled) return;
      errorCount = 0;
      onUpdate(analysis);
      if (analysis.status === 'pending' || analysis.status === 'processing') {
        timer = setTimeout(poll, intervalMs);
      } else {
        cancel();
        if (analysis.status === 'failed') onError(new Error(analysis.error_message || analysis.error || 'Analysis failed'));
      }
    } catch (err) {
      if (cancelled) return;
      if (++errorCount < 5) timer = setTimeout(poll, intervalMs * 2);
      else {
        cancel();
        onError(err);
      }
    }
  };
  poll();
  return cancel;
}

// ============== Chat ==============

export async function listChatModels(apiKey = '') {
  const headers = {};
  if (apiKey) {
    headers['X-TAMU-API-Key'] = apiKey;
  }

  const response = await api.get('/chat/models', { headers });
  return response.data;
}

// ============== Classes (Teacher/Student) ==============

export async function createClass(name, description = '') {
  const response = await api.post('/classes', { name, description });
  return response.data;
}

export async function joinClassByCode(joinCode) {
  const response = await api.post('/classes/join', { join_code: String(joinCode).trim() });
  return response.data;
}

export async function listMyClasses() {
  const response = await api.get('/classes');
  return response.data;
}

export async function deleteClass(classId) {
  const response = await api.delete(`/classes/${classId}`);
  return response.data;
}

export async function rotateClassJoinCode(classId) {
  const response = await api.post(`/classes/${classId}/rotate-join-code`);
  return response.data;
}

export async function listClassMembers(classId) {
  const response = await api.get(`/classes/${classId}/members`);
  return response.data;
}

export async function removeClassMember(classId, userId) {
  await api.delete(`/classes/${classId}/members/${userId}`);
}

export async function listClassAdmins(classId) {
  const response = await api.get(`/classes/${classId}/admins`);
  return response.data;
}

export async function promoteClassMember(classId, userId) {
  const response = await api.post(`/classes/${classId}/admins/${userId}`);
  return response.data;
}

export async function revokeClassAdmin(classId, userId) {
  await api.delete(`/classes/${classId}/admins/${userId}`);
}

export async function sendChatMessage(
  analysisType,
  analysisId,
  message,
  history,
  model,
  apiKey,
  onChunk,
  onDone,
  onError,
  requestSignal
) {
  const url = `${API_BASE}/chat/${analysisType}/${analysisId}`;
  const headers = {
    'Content-Type': 'application/json',
  };

  const identitySignal = userRequests.signal;
  const controller = new AbortController();
  const abort = () => controller.abort();
  identitySignal.addEventListener('abort', abort, { once: true });
  requestSignal?.addEventListener('abort', abort, { once: true });
  if (identitySignal.aborted || requestSignal?.aborted) abort();
  const signal = controller.signal;
  let reader;
  const sessionId = getSessionId();
  if (sessionId) headers['X-Session-Id'] = sessionId;
  if (apiKey) headers['X-TAMU-API-Key'] = apiKey;

  try {
    headers.Authorization = `Bearer ${await accessToken()}`;
    const decodeSseDataChunk = (data) => {
      try {
        return JSON.parse(data);
      } catch {
        return data;
      }
    };

    const body = {
      message,
      history: history.map(m => ({ role: m.role, content: m.content })),
    };
    if (model) body.model = model;
    if (apiKey) body.api_key = apiKey;

    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
      credentials: 'include',
      signal,
    });

    if (!response.ok) {
      let detail = `Request failed (${response.status})`;
      try {
        const data = await response.json();
        if (data?.detail) detail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
      } catch {
        // The body may already have been consumed by response.json().
      }
      throw new Error(detail);
    }

    reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });

      // Process complete SSE messages
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // Keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);

          if (data === '[DONE]') {
            onDone();
            return;
          }

          const chunk = decodeSseDataChunk(data);
          if (chunk && typeof chunk === 'object' && chunk.error) {
            throw new Error(typeof chunk.error === 'string' ? chunk.error : JSON.stringify(chunk.error));
          }
          onChunk(chunk);
        }
      }
    }

    throw new Error('The response stream ended before completion. Please retry.');
  } catch (err) {
    if (!signal.aborted) onError(err);
  } finally {
    identitySignal.removeEventListener('abort', abort);
    requestSignal?.removeEventListener('abort', abort);
    if (reader) {
      await reader.cancel().catch(() => {});
      reader.releaseLock();
    }
  }
}
