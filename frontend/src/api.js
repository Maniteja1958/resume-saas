export const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function createAnalysis({ file, jobDescription, targetMissingCount = 3 }) {
  const form = new FormData();
  form.append('resume_file', file);
  if (jobDescription) form.append('job_description', jobDescription);
  form.append('target_missing_count', String(targetMissingCount));
  return request('/analyses', { method: 'POST', body: form });
}

export async function getAnalysis(analysisId) {
  return request(`/analyses/${analysisId}`);
}

export async function getHistory() {
  return request('/history?limit=50');
}

export async function compareResumes({ fileA, fileB, jobDescription, analysisIdA, analysisIdB }) {
  const form = new FormData();
  if (fileA) form.append('resume_a', fileA);
  if (fileB) form.append('resume_b', fileB);
  if (analysisIdA) form.append('analysis_id_a', analysisIdA);
  if (analysisIdB) form.append('analysis_id_b', analysisIdB);
  if (jobDescription) form.append('job_description', jobDescription);
  return request('/compare', { method: 'POST', body: form });
}

export async function analyzeBatch({ file, jobs }) {
  const form = new FormData();
  form.append('resume_file', file);
  form.append('job_descriptions_json', JSON.stringify(jobs));
  return request('/analyze-batch', { method: 'POST', body: form });
}

export async function rescore({ analysisId, resumeData, jobDescription }) {
  return request('/rescore', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ analysis_id: analysisId, resume_data: resumeData, job_description: jobDescription || null })
  });
}

export async function fetchJobDescription(url) {
  return request('/job-description/fetch', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url })
  });
}

export async function healthCheck() {
  return request('/health');
}

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`;
  let res;
  try {
    res = await fetch(url, options);
  } catch (err) {
    throw new Error(
      `Cannot connect to backend at ${API_BASE}. ` +
      `Make sure FastAPI is running with: cd backend && python -m uvicorn app.main:app --reload --port 8000. ` +
      `Also open ${API_BASE}/health in your browser to confirm it works. Original error: ${err.message}`
    );
  }
  return handle(res);
}

async function handle(res) {
  if (!res.ok) {
    let message = `${res.status} ${res.statusText}`;
    try {
      const data = await res.json();
      message = data.detail || data.error || message;
    } catch (_) {}
    throw new Error(message);
  }
  return res.json();
}
