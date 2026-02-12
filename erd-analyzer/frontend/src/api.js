import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  withCredentials: true, // Enable cookies for session management
});

// ============== Legacy Single-File Analysis ==============

export async function submitAnalysis(imageFile, userStories) {
  const formData = new FormData();
  formData.append('image', imageFile);
  formData.append('user_stories', userStories);

  const response = await api.post('/analyze', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
}

// ============== Analysis ==============

export async function getAnalysis(analysisId) {
  const response = await api.get(`/analysis/${analysisId}`);
  return response.data;
}

export async function listAnalyses() {
  const response = await api.get('/analyses');
  return response.data;
}

export async function pollAnalysis(analysisId, onUpdate, intervalMs = 2000) {
  const poll = async () => {
    try {
      const analysis = await getAnalysis(analysisId);
      onUpdate(analysis);

      if (analysis.status === 'pending' || analysis.status === 'processing') {
        setTimeout(poll, intervalMs);
      }
    } catch (err) {
      console.error('Poll error:', err);
      // Retry on error
      setTimeout(poll, intervalMs * 2);
    }
  };

  poll();
}

// ============== GitHub OAuth ==============

export function initiateGitHubAuth() {
  // Redirect to backend OAuth endpoint
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

// ============== Repository Management ==============

export async function listRepositories() {
  const response = await api.get('/repositories');
  return response.data;
}

export async function getRepository(repositoryId) {
  const response = await api.get(`/repository/${repositoryId}`);
  return response.data;
}

export async function getRepositoryFiles(repositoryId) {
  const response = await api.get(`/repository/${repositoryId}/files`);
  return response.data;
}

export async function updateFileSelection(repositoryId, fileIds, isSelected) {
  const response = await api.put(`/repository/${repositoryId}/files/selection`, {
    file_ids: fileIds,
    is_selected: isSelected,
  });
  return response.data;
}

export async function rediscoverFiles(repositoryId) {
  const response = await api.post(`/repository/${repositoryId}/rediscover`);
  return response.data;
}

export async function deleteRepository(repositoryId) {
  const response = await api.delete(`/repository/${repositoryId}`);
  return response.data;
}

// ============== Repository Analysis ==============

export async function startRepositoryAnalysis(repositoryId) {
  const response = await api.post(`/repository/${repositoryId}/analyze`);
  return response.data;
}

export async function listRepositoryAnalyses(repositoryId) {
  const response = await api.get(`/repository/${repositoryId}/analyses`);
  return response.data;
}
