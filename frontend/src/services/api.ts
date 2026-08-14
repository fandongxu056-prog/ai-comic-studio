/** API client — fetch wrapper with JWT token injection and error handling. */

import { useAuthStore } from "@/stores/auth-store";

const API_BASE = "/api/v1";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

/** Get the current access token from the auth store. */
function getToken(): string | null {
  return useAuthStore.getState().accessToken;
}

/** Core request wrapper. */
async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const resp = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (resp.status === 401) {
    // Try refreshing the token once
    const refreshed = await useAuthStore.getState().refreshAccessToken();
    if (refreshed) {
      return request<T>(path, options);
    }
  }

  if (!resp.ok) {
    let detail = `请求失败 (${resp.status})`;
    try {
      const data = await resp.json();
      if (typeof data.detail === "string") detail = data.detail;
      else if (Array.isArray(data.detail)) detail = data.detail.map((d: any) => d.msg).join("; ");
    } catch {}
    throw new ApiError(detail, resp.status);
  }

  if (resp.status === 204) {
    return undefined as T;
  }
  return resp.json();
}

// ── Generic HTTP helpers ──

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PUT", body: body ? JSON.stringify(body) : undefined }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};

// ── Type definitions matching backend responses ──

export interface ProjectStageSummary {
  status: string;
  id: string | null;
  version: number;
}

export interface ProjectResponse {
  id: string;
  title: string;
  source_type: string;
  genre: Record<string, unknown> | null;
  format: string;
  aspect_ratio: string;
  target_resolution: string;
  total_duration_seconds: number | null;
  episode_count: number;
  art_style: string | null;
  style_preference: Record<string, unknown> | null;
  current_stage: string;
  stages: {
    script: ProjectStageSummary;
    assets: ProjectStageSummary;
    storyboard: ProjectStageSummary;
    production: ProjectStageSummary;
  };
  global_style_seed: number | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface ProjectListResponse {
  data: ProjectResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface ProjectCreateInput {
  title: string;
  source_type: string;
  source_content?: string;
  genre?: { primary: string; sub_tags: string[] };
  target_spec?: {
    format: string;
    aspect_ratio: string;
    total_duration_seconds: number;
    episode_count: number;
    duration_per_episode_seconds: number;
  };
  style_preference?: { art_style: string; style_notes?: string };
}

export interface ScriptStatusResponse {
  project_id: string;
  script_status: string;
  script_id: string | null;
  version: number;
  latest_score: number | null;
  latest_verdict: string | null;
}

export interface ScriptLatestResponse {
  project_id: string;
  script_id: string;
  version: number;
  status: string;
  episode_count: number;
  scene_count: number;
  character_count: number;
  latest_score: number | null;
  content: Record<string, any>;
  created_at: string | null;
}
