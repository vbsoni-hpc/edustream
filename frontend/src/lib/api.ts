// Centralized API client for EduStream
const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

interface FetchOptions extends RequestInit {
  token?: string;
}

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = 'ApiError';
  }
}

async function request<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const { token, headers: extraHeaders, ...rest } = options;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(extraHeaders as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    headers,
    ...rest,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(body.detail || res.statusText, res.status);
  }

  return res.json();
}

// ── Auth ──────────────────────────────────────────────────
export const authApi = {
  login: (username: string, password: string) =>
    request<{ token: string; user_id: number; username: string; display_name: string; is_admin: boolean }>(
      '/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      }
    ),

  register: (username: string, password: string, display_name: string) =>
    request<{ token: string; user_id: number; username: string }>(
      '/api/auth/register', {
        method: 'POST',
        body: JSON.stringify({ username, password, display_name }),
      }
    ),
};

// ── Dashboard ─────────────────────────────────────────────
export const dashboardApi = {
  getStats: (token: string) =>
    request<{ total_videos: number; completed_videos: number; completion_pct: number; total_watch_hours: number; total_watch_seconds: number }>(
      '/api/dashboard/stats', { token }
    ),

  getLastSegment: (token: string) =>
    request<{ segment: any }>('/api/dashboard/last-segment', { token }),

  getSegmentStats: (token: string) =>
    request<{ segments: any[] }>('/api/segments/stats', { token }),

  getLeaderboard: (token: string, days = 1) =>
    request<{ leaderboard: any[] }>(`/api/leaderboard?days=${days}`, { token }),

  getNotices: () =>
    request<{ notices: any[] }>('/api/notices'),
};

// ── Courses ───────────────────────────────────────────────
export const coursesApi = {
  getSegments: (token: string) =>
    request<{ segments: any[] }>('/api/segments', { token }),

  getSegmentVideos: (token: string, segmentId: number) =>
    request<{ videos: any[] }>(`/api/segments/${segmentId}/videos`, { token }),

  getSegmentModules: (token: string, segmentId: number) =>
    request<{ modules: any[] }>(`/api/segments/${segmentId}/modules`, { token }),

  getSegmentLeaderboard: (segmentId: number, days = 7) =>
    request<{ leaderboard: any[] }>(`/api/segments/${segmentId}/leaderboard?days=${days}`),

  getModuleVideos: (token: string, moduleId: number) =>
    request<{ videos: any[] }>(`/api/modules/${moduleId}/videos`, { token }),

  getVideo: (token: string, videoId: number) =>
    request<any>(`/api/videos/${videoId}`, { token }),
};

// ── Subscriptions ─────────────────────────────────────────
export const subscriptionsApi = {
  get: (token: string) =>
    request<{ subscribed_ids: number[] }>('/api/subscriptions', { token }),

  subscribe: (token: string, segmentId: number) =>
    request('/api/subscriptions/' + segmentId, { method: 'POST', token }),

  unsubscribe: (token: string, segmentId: number) =>
    request('/api/subscriptions/' + segmentId, { method: 'DELETE', token }),
};

// ── Progress ──────────────────────────────────────────────
export const progressApi = {
  getAll: (token: string) =>
    request<{ progress: any[] }>('/api/progress', { token }),

  get: (token: string, videoId: number) =>
    request<{ progress: any }>(`/api/progress/${videoId}`, { token }),

  update: (token: string, videoId: number, watchSeconds: number, lastPosition: number) =>
    request(`/api/progress/${videoId}`, {
      method: 'POST',
      token,
      body: JSON.stringify({ watch_seconds: watchSeconds, last_position: lastPosition }),
    }),

  complete: (token: string, videoId: number) =>
    request(`/api/complete/${videoId}`, { method: 'POST', token }),
};

// ── Messaging ─────────────────────────────────────────────
export const messagingApi = {
  getGroupMessages: (limit = 50) =>
    request<{ messages: any[] }>(`/api/messages/group?limit=${limit}`),

  sendGroupMessage: (token: string, content: string) =>
    request('/api/messages/group', {
      method: 'POST',
      token,
      body: JSON.stringify({ content }),
    }),

  getInbox: (token: string) =>
    request<{ messages: any[] }>('/api/messages/inbox', { token }),

  getUnread: (token: string) =>
    request<{ messages: any[] }>('/api/messages/unread', { token }),

  sendDM: (token: string, recipientId: number, content: string) =>
    request('/api/messages/dm', {
      method: 'POST',
      token,
      body: JSON.stringify({ content, recipient_id: recipientId }),
    }),

  markRead: (token: string, messageIds: number[]) =>
    request('/api/messages/read', {
      method: 'POST',
      token,
      body: JSON.stringify({ message_ids: messageIds }),
    }),

  broadcast: (token: string, content: string) =>
    request('/api/messages/broadcast', {
      method: 'POST',
      token,
      body: JSON.stringify({ content }),
    }),
};

// ── Users ─────────────────────────────────────────────────
export const usersApi = {
  ping: (token: string, videoId?: number) =>
    request('/api/users/ping', { 
      method: 'POST', 
      token, 
      body: videoId ? JSON.stringify({ video_id: videoId }) : undefined 
    }),

  getOnline: () =>
    request<{ users: any[] }>('/api/users/online'),

  getWatching: (videoId: number) =>
    request<{ users: any[] }>(`/api/videos/${videoId}/watching`),

  getAll: (token: string) =>
    request<{ users: any[] }>('/api/users', { token }),

  getMe: (token: string) =>
    request<{ id: number; username: string; display_name: string; is_admin: boolean }>(
      '/api/users/me', { token }
    ),
};

// ── Analytics ─────────────────────────────────────────────
export const analyticsApi = {
  getDaily: (token: string, days = 30) =>
    request<{ activity: any[] }>(`/api/analytics/daily?days=${days}`, { token }),

  getSegments: (token: string) =>
    request<{ segments: any[] }>('/api/analytics/segments', { token }),

  getModules: (token: string) =>
    request<{ modules: any[] }>('/api/analytics/modules', { token }),
};

// ── AI Chat ───────────────────────────────────────────────
export const aiApi = {
  chat: (token: string, messages: Array<{role: string; content: string}>, videoTitle: string) =>
    request<{ response: string }>('/api/ai/chat', {
      method: 'POST',
      token,
      body: JSON.stringify({ messages, video_title: videoTitle }),
    }),
};

// ── YouTube Import ────────────────────────────────────────
export const importApi = {
  youtube: (token: string, url: string, icon = '▶️', description = '') =>
    request<{ status: string; segment_id: number }>('/api/import/youtube', {
      method: 'POST',
      token,
      body: JSON.stringify({ url, icon, description }),
    }),
};

// ── Admin ─────────────────────────────────────────────────
export const adminApi = {
  getUsers: (token: string) =>
    request<{ users: any[] }>('/api/admin/users', { token }),

  updateUser: (token: string, userId: number, data: { username: string; display_name: string; is_admin: boolean }) =>
    request(`/api/admin/users/${userId}`, { method: 'PUT', token, body: JSON.stringify(data) }),

  deleteUser: (token: string, userId: number) =>
    request(`/api/admin/users/${userId}`, { method: 'DELETE', token }),

  updateSegment: (token: string, segmentId: number, data: any) =>
    request(`/api/admin/segments/${segmentId}`, { method: 'PUT', token, body: JSON.stringify(data) }),

  createSegment: (token: string, data: { name: string; icon?: string; description?: string }) =>
    request(`/api/admin/segments`, { method: 'POST', token, body: JSON.stringify(data) }),

  updateModule: (token: string, moduleId: number, data: any) =>
    request(`/api/admin/modules/${moduleId}`, { method: 'PUT', token, body: JSON.stringify(data) }),

  createModule: (token: string, data: { name: string; segment_id: number; icon?: string }) =>
    request('/api/admin/modules', { method: 'POST', token, body: JSON.stringify(data) }),

  deleteModule: (token: string, moduleId: number) =>
    request(`/api/admin/modules/${moduleId}`, { method: 'DELETE', token }),

  assignVideos: (token: string, videoIds: number[], moduleId: number) =>
    request('/api/admin/videos/assign', { method: 'POST', token, body: JSON.stringify({ video_ids: videoIds, module_id: moduleId }) }),

  unassignVideos: (token: string, videoIds: number[]) =>
    request('/api/admin/videos/unassign', { method: 'POST', token, body: JSON.stringify({ video_ids: videoIds }) }),

  setVideoRestricted: (token: string, videoId: number, isRestricted: boolean) =>
    request(`/api/admin/videos/${videoId}/restricted`, { method: 'PUT', token, body: JSON.stringify({ is_restricted: isRestricted }) }),

  createNotice: (token: string, content: string) =>
    request('/api/admin/notices', { method: 'POST', token, body: JSON.stringify({ content }) }),

  getNotices: (token: string) =>
    request<{ notices: any[] }>('/api/admin/notices', { token }),

  deleteNotice: (token: string, noticeId: number) =>
    request(`/api/admin/notices/${noticeId}`, { method: 'DELETE', token }),

  getSegmentAccess: (token: string, segmentId: number) =>
    request<{ user_ids: number[] }>(`/api/admin/access/segments/${segmentId}`, { token }),

  setSegmentAccess: (token: string, segmentId: number, userIds: number[]) =>
    request(`/api/admin/access/segments/${segmentId}`, { method: 'PUT', token, body: JSON.stringify({ user_ids: userIds }) }),

  getModuleAccess: (token: string, moduleId: number) =>
    request<{ user_ids: number[] }>(`/api/admin/access/modules/${moduleId}`, { token }),

  setModuleAccess: (token: string, moduleId: number, userIds: number[]) =>
    request(`/api/admin/access/modules/${moduleId}`, { method: 'PUT', token, body: JSON.stringify({ user_ids: userIds }) }),

  getVideoAccess: (token: string, videoId: number) =>
    request<{ user_ids: number[] }>(`/api/admin/access/videos/${videoId}`, { token }),

  setVideoAccess: (token: string, videoId: number, userIds: number[]) =>
    request(`/api/admin/access/videos/${videoId}`, { method: 'PUT', token, body: JSON.stringify({ user_ids: userIds }) }),

  backup: (token: string) =>
    request('/api/admin/backup', { method: 'POST', token }),

  fixYoutube: (token: string) =>
    request<{ status: string; recovered: number }>('/api/admin/fix-youtube', { method: 'POST', token }),

  sync: (token: string) =>
    request<{ status: string; synced: number }>('/api/sync', { method: 'POST', token }),
};
