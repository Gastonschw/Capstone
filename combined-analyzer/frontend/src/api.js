import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
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
  window.location.href = '/api/github/auth';
}

export async function getGitHubAuthStatus() {
  const response = await api.get('/github/status');
  return response.data;
}

export async function getGitHubRepos() {
  const response = await api.get('/github/repos');
  return response.data;
}

export async function importGitHubRepo(repoFullName) {
  const response = await api.post('/github/import', {
    repo_full_name: repoFullName,
  });
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

export async function startIntegrityAnalysis(repositoryId) {
  const response = await api.post(`/integrity/repository/${repositoryId}/analyze`);
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
