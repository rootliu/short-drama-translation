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
  getSystemStatus: () => request<any>('/system/status'),
  exportMarkdown: (projectId: number) => `${BASE}/projects/${projectId}/export`,

  // File upload
  uploadEpisodeFile: async (projectId: number, episodeId: number, file: File) => {
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(`${BASE}/projects/${projectId}/episodes/${episodeId}/upload`, {
      method: 'POST',
      body: form,
    })
    if (!res.ok) throw new Error(`Upload error: ${res.status}`)
    return res.json()
  },

  batchUploadSubtitles: async (projectId: number, files: File[]) => {
    const form = new FormData()
    files.forEach(f => form.append('files', f))
    const res = await fetch(`${BASE}/projects/${projectId}/batch-upload`, {
      method: 'POST',
      body: form,
    })
    if (!res.ok) throw new Error(`Upload error: ${res.status}`)
    return res.json()
  },
}

export function createEventSource(projectId: number): EventSource {
  return new EventSource(`${BASE}/projects/${projectId}/stream`)
}
