export type CommandResponse = {
  status: string;
  actions: string[];
  files: string[];
  message: string;
  intent?: string;
  action?: string;
  reason?: string;
  notice?: string;
};

const API_BASE_URL = "http://127.0.0.1:8000";

export type ChatHistoryResponse = {
  session_id: string;
  messages: { role: string; timestamp: string; content: string }[];
};

export type ChatSession = {
  session_id: string;
  day: string;
  created_at: string;
  updated_at: string;
};

export type ProgressCacheResponse = {
  cache_path: string;
  last_entry: string;
  updated_at: string;
};

export type ChatSessionsResponse = {
  active_session_id?: string;
  sessions: ChatSession[];
};

export type Profile = {
  profile_id: string;
  name: string;
  internship_name: string;
  start_date: string;
  vault_root: string;
  active: number;
};

export type ProfilesListResponse = {
  active_profile_id?: string;
  profiles: Profile[];
};

export type ModelSettingsResponse = {
  selected_model: string;
  available_models: string[];
  google_api_key_configured: boolean;
  openrouter_api_key_configured: boolean;
  openrouter_base_url: string;
};

export async function sendMessage(
  text: string,
  sessionId?: string,
  model?: string
): Promise<CommandResponse> {
  const response = await fetch(`${API_BASE_URL}/chat/message`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ text, session_id: sessionId, model })
  });

  if (!response.ok) {
    throw new Error("Command failed");
  }

  return response.json() as Promise<CommandResponse>;
}

export async function fetchHistory(): Promise<ChatHistoryResponse> {
  const response = await fetch(`${API_BASE_URL}/chat/history`);
  if (!response.ok) {
    throw new Error("History fetch failed");
  }
  return response.json() as Promise<ChatHistoryResponse>;
}

export async function fetchHistoryForSession(
  sessionId: string
): Promise<ChatHistoryResponse> {
  const response = await fetch(`${API_BASE_URL}/chat/history?session_id=${sessionId}`);
  if (!response.ok) {
    throw new Error("History fetch failed");
  }
  return response.json() as Promise<ChatHistoryResponse>;
}

export async function fetchChatSessions(): Promise<ChatSessionsResponse> {
  const response = await fetch(`${API_BASE_URL}/chat/sessions`);
  if (!response.ok) {
    throw new Error("Chat sessions fetch failed");
  }
  return response.json() as Promise<ChatSessionsResponse>;
}

export async function fetchLatestProgressCache(): Promise<ProgressCacheResponse> {
  const response = await fetch(`${API_BASE_URL}/progress/cache/latest`);
  if (!response.ok) {
    throw new Error("Progress cache fetch failed");
  }
  return response.json() as Promise<ProgressCacheResponse>;
}

export async function fetchProfiles(): Promise<ProfilesListResponse> {
  const response = await fetch(`${API_BASE_URL}/profiles`);
  if (!response.ok) {
    throw new Error("Profiles fetch failed");
  }
  return response.json() as Promise<ProfilesListResponse>;
}

export async function createProfile(
  internship_name: string,
  options?: {
    name?: string;
    start_date?: string;
    vault_root?: string;
  }
): Promise<Profile> {
  const response = await fetch(`${API_BASE_URL}/profiles`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ internship_name, ...options })
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const detail = payload?.detail || "Profile create failed";
    throw new Error(detail);
  }
  return response.json() as Promise<Profile>;
}

export async function switchProfile(profile_id: string): Promise<Profile> {
  const response = await fetch(`${API_BASE_URL}/profiles/switch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ profile_id })
  });
  if (!response.ok) {
    throw new Error("Profile switch failed");
  }
  return response.json() as Promise<Profile>;
}

export async function updateProfile(payload: {
  profile_id: string;
  name?: string;
  internship_name?: string;
  start_date?: string;
  vault_root?: string;
}): Promise<Profile> {
  const response = await fetch(`${API_BASE_URL}/profiles/update`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    throw new Error("Profile update failed");
  }
  return response.json() as Promise<Profile>;
}

export async function fetchModelSettings(): Promise<ModelSettingsResponse> {
  const response = await fetch(`${API_BASE_URL}/settings/models`);
  if (!response.ok) {
    throw new Error("Model settings fetch failed");
  }
  return response.json() as Promise<ModelSettingsResponse>;
}

export async function updateModelSettings(payload: {
  selected_model?: string;
  google_api_key?: string;
  openrouter_api_key?: string;
  openrouter_base_url?: string;
}): Promise<ModelSettingsResponse> {
  const response = await fetch(`${API_BASE_URL}/settings/models`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    const detail = errorBody?.detail || "Model settings update failed";
    throw new Error(detail);
  }
  return response.json() as Promise<ModelSettingsResponse>;
}
