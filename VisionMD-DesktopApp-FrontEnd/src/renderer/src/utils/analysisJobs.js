const API_URL = import.meta.env.VITE_API_BASE_URL;

const delay = ms => new Promise(resolve => window.setTimeout(resolve, ms));

export async function runAnalysisJob({ taskName, videoId, jsonData, force = false, onUpdate }) {
  const form = new FormData();
  form.append('json_data', typeof jsonData === 'string' ? jsonData : JSON.stringify(jsonData));
  const query = `id=${encodeURIComponent(videoId)}${force ? '&force=1' : ''}`;
  const createdResponse = await fetch(
    `${API_URL}/analysis_jobs/${taskName}/?${query}`,
    { method: 'POST', body: form },
  );
  if (!createdResponse.ok) throw new Error(await createdResponse.text());
  let job = await createdResponse.json();
  onUpdate?.(job);
  while (!['completed', 'failed', 'cancelled'].includes(job.status)) {
    await delay(750);
    const response = await fetch(`${API_URL}/analysis_jobs/status/${job.id}/`);
    if (!response.ok) throw new Error(await response.text());
    job = await response.json();
    onUpdate?.(job);
  }
  if (job.status !== 'completed') {
    throw new Error(job.error || `Analysis ${job.status}`);
  }
  return job.result;
}

export async function cancelAnalysisJob(jobId) {
  if (!jobId) return null;
  const response = await fetch(`${API_URL}/analysis_jobs/status/${jobId}/`, { method: 'DELETE' });
  return response.ok ? response.json() : null;
}
