import axios from 'axios';

const USER_ID_STORAGE_KEY = 'supabase_user_id';
const SESSION_ID_STORAGE_KEY = 'github_session_id';

/** Call this when the user logs in with Supabase (e.g. Google). Pass null to clear. */
export function setCurrentUserId(userId) {
  if (userId == null || userId === '') {
    localStorage.removeItem(USER_ID_STORAGE_KEY);
  } else {
    localStorage.setItem(USER_ID_STORAGE_KEY, String(userId));
  }
}

/** Current Supabase user id, if set. Used to link GitHub and repos to the user. */
export function getCurrentUserId() {
  return localStorage.getItem(USER_ID_STORAGE_KEY) || null;
}

/** Store session_id received from the OAuth callback redirect.
 *  Needed for cross-origin deployments where third-party cookies are blocked. */
export function setSessionId(sessionId) {
  if (sessionId == null || sessionId === '') {
    localStorage.removeItem(SESSION_ID_STORAGE_KEY);
  } else {
    localStorage.setItem(SESSION_ID_STORAGE_KEY, String(sessionId));
  }
}

export function getSessionId() {
  return localStorage.getItem(SESSION_ID_STORAGE_KEY) || null;
}

const API_BASE = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
});

api.interceptors.request.use((config) => {
  const userId = getCurrentUserId();
  if (userId) {
    config.headers['X-User-Id'] = userId;
  }
  const sessionId = getSessionId();
  if (sessionId) {
    config.headers['X-Session-Id'] = sessionId;
  }
  return config;
});

// ============== Repository Management ==============

export async function listRepositories(opts = {}) {
  const config = {};
  if (opts.classId && opts.studentUserId) {
    config.params = {
      class_id: opts.classId,
      student_user_id: opts.studentUserId,
    };
  }
  const response = await api.get('/repositories', config);
  return response.data;
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

export async function rediscoverFiles(repositoryId) {
  const response = await api.post(`/repository/${repositoryId}/rediscover`);
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

export function initiateGitHubAuth() {
  const userId = getCurrentUserId();
  const params = new URLSearchParams();
  if (userId) params.set('user_id', userId);
  // Pass existing session_id so the backend can reuse it (cookie may not
  // survive cross-origin redirect in browsers that block third-party cookies).
  const sid = getSessionId();
  if (sid) params.set('session_id', sid);
  const qs = params.toString();
  window.location.href = `${API_BASE}/github/auth${qs ? '?' + qs : ''}`;
}

export async function getGitHubAuthStatus() {
  const response = await api.get('/github/status');
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

export async function pollAnalysis(type, analysisId, onUpdate, intervalMs = 5000) {
  const getAnalysis = analysisGetters[type] || getIntegrityAnalysis;

  let errorCount = 0;
  const maxErrors = 5;

  const poll = async () => {
    try {
      const analysis = await getAnalysis(analysisId);
      errorCount = 0;
      onUpdate(analysis);

      if (analysis.status === 'pending' || analysis.status === 'processing') {
        setTimeout(poll, intervalMs);
      }
    } catch (err) {
      errorCount++;
      console.error(`Poll error for ${type}/${analysisId} (${errorCount}/${maxErrors}):`, err);
      if (errorCount < maxErrors) {
        setTimeout(poll, intervalMs * 2);
      } else {
        console.error(`Giving up polling ${type}/${analysisId} after ${maxErrors} errors`);
        onUpdate({ status: 'failed', error: 'Polling failed' });
      }
    }
  };

  poll();
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

export async function sendChatMessage(
  analysisType,
  analysisId,
  message,
  history,
  model,
  apiKey,
  onChunk,
  onDone,
  onError
) {
  const url = `${API_BASE}/chat/${analysisType}/${analysisId}`;
  const headers = {
    'Content-Type': 'application/json',
  };

  const userId = getCurrentUserId();
  if (userId) headers['X-User-Id'] = userId;
  const sessionId = getSessionId();
  if (sessionId) headers['X-Session-Id'] = sessionId;
  if (apiKey) headers['X-TAMU-API-Key'] = apiKey;

  try {
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
    });

    if (!response.ok) {
      let detail = `Request failed (${response.status})`;
      try {
        const data = await response.json();
        if (data?.detail) detail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
      } catch {
        const text = await response.text();
        if (text) detail = text;
      }
      throw new Error(detail);
    }

    const reader = response.body.getReader();
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

          onChunk(decodeSseDataChunk(data));
        }
      }
    }

    onDone();
  } catch (err) {
    console.error('Chat error:', err);
    onError(err);
  }
}
