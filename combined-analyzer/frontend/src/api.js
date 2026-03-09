import axios from 'axios';

const USER_ID_STORAGE_KEY = 'supabase_user_id';

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

const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
});

api.interceptors.request.use((config) => {
  const userId = getCurrentUserId();
  if (userId) {
    config.headers['X-User-Id'] = userId;
  }
  return config;
});

// ============== Repository Management ==============

export async function listRepositories() {
  const response = await api.get('/repositories');
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

export async function uploadFolder(zipFile, name = null) {
  const formData = new FormData();
  formData.append('file', zipFile);
  if (name) {
    formData.append('name', name);
  }

  const response = await api.post('/upload-folder', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
}

// ============== GitHub OAuth ==============

export function initiateGitHubAuth() {
  const userId = getCurrentUserId();
  const url = userId
    ? `/api/github/auth?user_id=${encodeURIComponent(userId)}`
    : '/api/github/auth';
  window.location.href = url;
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

export async function startERDAnalysis(repositoryId) {
  const response = await api.post(`/erd/repository/${repositoryId}/analyze`);
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

// ============== Polling ==============

export async function pollAnalysis(type, analysisId, onUpdate, intervalMs = 2000) {
  const getAnalysis = type === 'erd' ? getERDAnalysis : getIntegrityAnalysis;

  const poll = async () => {
    try {
      const analysis = await getAnalysis(analysisId);
      onUpdate(analysis);

      if (analysis.status === 'pending' || analysis.status === 'processing') {
        setTimeout(poll, intervalMs);
      }
    } catch (err) {
      console.error('Poll error:', err);
      setTimeout(poll, intervalMs * 2);
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
  const url = `/api/chat/${analysisType}/${analysisId}`;
  const headers = {
    'Content-Type': 'application/json',
  };

  if (apiKey) {
    headers['X-TAMU-API-Key'] = apiKey;
  }

  try {
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
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
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

          onChunk(data);
        }
      }
    }

    onDone();
  } catch (err) {
    console.error('Chat error:', err);
    onError(err);
  }
}
