const API_BASE = '';

async function request<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || 'Request failed');
  }

  return response.json();
}

export interface Task {
  id: number;
  file_path: string;
  file_name: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled' | 'paused';
  progress: number;
  source_language: string | null;
  target_language: string;
  llm_provider: string;
  subtitle_track: number | null;
  force_override: boolean;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface TaskStats {
  pending: number;
  processing: number;
  completed: number;
  failed: number;
  cancelled: number;
  paused: number;
  total: number;
}

export interface TaskListResponse {
  tasks: Task[];
  total: number;
  limit: number;
  offset: number;
}

export interface FileInfo {
  name: string;
  path: string;
  is_dir: boolean;
  size: number | null;
}

export interface BrowseResponse {
  current_path: string;
  parent_path: string | null;
  items: FileInfo[];
}

export interface Watcher {
  id: number;
  path: string;
  enabled: boolean;
  target_language: string;
  llm_provider: string;
  created_at: string;
}

export interface Settings {
  openai_api_key: string | null;
  openai_model: string;
  openai_base_url: string | null;
  claude_api_key: string | null;
  claude_model: string;
  deepseek_api_key: string | null;
  deepseek_model: string;
  deepseek_base_url: string | null;
  glm_api_key: string | null;
  glm_model: string;
  glm_base_url: string | null;
  default_llm: string;
  target_language: string;
  source_language: string;
  bilingual_output: boolean;
  subtitle_output_format: 'mkv' | 'srt' | 'ass';
  overwrite_mkv: boolean;
  max_concurrent_tasks: number;
}

export interface SubtitleTrack {
  index: number;
  codec: string;
  language: string | null;
  title: string | null;
}

// Tasks API
export const tasksApi = {
  list: (params?: { status?: string; limit?: number; offset?: number }) => {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.set('status', params.status);
    if (params?.limit !== undefined) searchParams.set('limit', params.limit.toString());
    if (params?.offset !== undefined) searchParams.set('offset', params.offset.toString());
    const query = searchParams.toString();
    return request<TaskListResponse>(`/api/tasks${query ? `?${query}` : ''}`);
  },

  get: (id: number) => request<Task>(`/api/tasks/${id}`),

  create: (data: {
    file_path: string;
    target_language?: string;
    llm_provider?: string;
    subtitle_track?: number;
    force_override?: boolean;
  }) =>
    request<Task>('/api/tasks', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  createFromDirectory: (data: {
    directory_path: string;
    target_language?: string;
    llm_provider?: string;
    recursive?: boolean;
    force_override?: boolean;
  }) =>
    request<{ created_count: number; task_ids: number[] }>('/api/tasks/directory', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  delete: (id: number) =>
    request<{ status: string }>(`/api/tasks/${id}`, { method: 'DELETE' }),

  retry: (id: number) =>
    request<{ status: string }>(`/api/tasks/${id}/retry`, { method: 'POST' }),

  stats: () => request<TaskStats>('/api/tasks/stats'),

  pauseAll: () => request<{ paused_count: number }>('/api/tasks/pause-all', { method: 'POST' }),

  pauseSelected: (task_ids: number[]) =>
    request<{ paused_count: number }>('/api/tasks/pause-selected', {
      method: 'POST',
      body: JSON.stringify({ task_ids }),
    }),

  deleteAll: () => request<{ cancelled_count: number; deleted_count: number }>('/api/tasks/delete-all', { method: 'DELETE' }),

  deleteSelected: (task_ids: number[]) =>
    request<{ cancelled_count: number; deleted_count: number }>('/api/tasks/delete-selected', {
      method: 'POST',
      body: JSON.stringify({ task_ids }),
    }),
};

// Files API
export const filesApi = {
  browse: (path?: string) =>
    request<BrowseResponse>(`/api/files/browse${path ? `?path=${encodeURIComponent(path)}` : ''}`),

  getSubtitleTracks: (filePath: string) =>
    request<{ file_path: string; tracks: SubtitleTrack[] }>(
      `/api/files/subtitle-tracks?file_path=${encodeURIComponent(filePath)}`
    ),
};

// Watchers API
export const watchersApi = {
  list: () => request<Watcher[]>('/api/watchers'),

  create: (data: { path: string; target_language?: string; llm_provider?: string }) =>
    request<Watcher>('/api/watchers', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  delete: (id: number) =>
    request<{ status: string }>(`/api/watchers/${id}`, { method: 'DELETE' }),

  toggle: (id: number) =>
    request<{ enabled: boolean }>(`/api/watchers/${id}/toggle`, { method: 'POST' }),
};

// Settings API
export const settingsApi = {
  get: () => request<Settings>('/api/settings'),

  update: (data: Partial<Settings>) =>
    request<Settings>('/api/settings', {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  getLlmProviders: () =>
    request<{
      providers: { id: string; name: string; models: string[] }[];
    }>('/api/settings/llm-providers'),

  getLanguages: () =>
    request<{
      languages: { code: string; name: string }[];
    }>('/api/settings/languages'),

  testLlm: (data: {
    provider: string;
    api_key?: string | null;
    model?: string | null;
    base_url?: string | null;
  }) =>
    request<{ status: string }>('/api/settings/test-llm', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};

// WebSocket
export function createProgressWebSocket(
  onMessage: (data: { type: string; task_id: number; progress?: number; status?: string }) => void
) {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws/progress`);

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    onMessage(data);
  };

  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
  };

  // Keep connection alive with ping
  const pingInterval = setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send('ping');
    }
  }, 30000);

  ws.onclose = () => {
    clearInterval(pingInterval);
  };

  return ws;
}
