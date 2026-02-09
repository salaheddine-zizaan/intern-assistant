export type CommandResponse = {
  status: string;
  actions: string[];
  files: string[];
  message: string;
  intent?: string;
  action?: string;
  reason?: string;
};

const API_BASE_URL = "http://127.0.0.1:8000";

export type ChatHistoryResponse = {
  session_id: string;
  messages: { role: string; timestamp: string; content: string }[];
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
    throw new Error("Profile create failed");
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
