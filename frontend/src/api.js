import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
});

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
    const analysis = await getAnalysis(analysisId);
    onUpdate(analysis);

    if (analysis.status === 'pending' || analysis.status === 'processing') {
      setTimeout(poll, intervalMs);
    }
  };

  poll();
}
