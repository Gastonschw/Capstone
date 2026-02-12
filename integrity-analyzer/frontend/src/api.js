import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
});

// Repository functions
export const listRepositories = () => api.get('/repositories');
export const getRepository = (id) => api.get(`/repository/${id}`);
export const deleteRepository = (id) => api.delete(`/repository/${id}`);
export const updateFileSelection = (repoId, fileIds, isSelected) =>
  api.put(`/repository/${repoId}/files/selection`, { file_ids: fileIds, is_selected: isSelected });
export const rediscoverFiles = (repoId) => api.post(`/repository/${repoId}/rediscover`);

// Upload functions
export const uploadFolder = (file) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post('/upload-folder', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

// GitHub functions
export const getGitHubStatus = () => api.get('/github/status');
export const listGitHubRepos = () => api.get('/github/repos');
export const importGitHubRepo = (repoFullName) =>
  api.post('/github/import', { repo_full_name: repoFullName });
export const logoutGitHub = () => api.post('/github/logout');

// Analysis functions
export const startAnalysis = (repoId) => api.post(`/repository/${repoId}/analyze`);
export const listAnalyses = (repoId) => api.get(`/repository/${repoId}/analyses`);
export const getAnalysis = (analysisId) => api.get(`/analysis/${analysisId}`);

// Polling helper
export const pollAnalysis = async (analysisId, onUpdate, intervalMs = 2000) => {
  const poll = async () => {
    const response = await getAnalysis(analysisId);
    onUpdate(response.data);
    if (response.data.status === 'pending' || response.data.status === 'processing') {
      setTimeout(poll, intervalMs);
    }
  };
  poll();
};

export default api;
