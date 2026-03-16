const BASE = '/api'

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export const api = {
  listProjects: () => request<any[]>('/projects'),
  createProject: (data: any) => request<any>('/projects', { method: 'POST', body: JSON.stringify(data) }),
  getProject: (id: number) => request<any>(`/projects/${id}`),
  getProjectStats: (id: number) => request<any>(`/projects/${id}/stats`),
  getProjectLogs: (id: number, limit = 50) => request<any[]>(`/projects/${id}/logs?limit=${limit}`),
  startBatch: (projectId: number, batchId: number) =>
    request<any>(`/projects/${projectId}/batches/${batchId}/start`, { method: 'POST' }),
  getBatchEpisodes: (projectId: number, batchId: number) =>
    request<any[]>(`/projects/${projectId}/batches/${batchId}/episodes`),
  getEpisode: (id: number) => request<any>(`/episodes/${id}`),
  getPipelineStages: () => request<any>('/pipeline/stages'),
}

export function createEventSource(projectId: number): EventSource {
  return new EventSource(`${BASE}/projects/${projectId}/stream`)
}
