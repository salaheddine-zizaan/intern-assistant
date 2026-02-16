import { useEffect, useState } from "react";
import ChatWindow from "./components/ChatWindow";
import InputBox from "./components/InputBox";
import StatusBar from "./components/StatusBar";
import {
  fetchChatSessions,
  fetchHistory,
  fetchHistoryForSession,
  fetchLatestProgressCache,
  fetchModelSettings,
  fetchProfiles,
  sendMessage,
  switchProfile,
  updateModelSettings,
  updateProfile
} from "./services/api";
import OnboardingPage from "./components/OnboardingPage";
import ProfileSelector from "./components/ProfileSelector";
import TutorialPage from "./components/TutorialPage";
import SettingsPage from "./components/SettingsPage";
import ApiSetupPage from "./components/ApiSetupPage";

export type Message = {
  id: string;
  role: "user" | "assistant";
  text: string;
  actions?: string[];
  files?: string[];
  notice?: string;
  intent?: string;
  action?: string;
  reason?: string;
};

type Status = "idle" | "loading" | "success" | "error";

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [status, setStatus] = useState<Status>("idle");
  const [statusMessage, setStatusMessage] = useState<string>("");
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [inputValue, setInputValue] = useState<string>("");
  const [chatSessions, setChatSessions] = useState<
    { session_id: string; day: string; updated_at: string }[]
  >([]);
  const [latestCache, setLatestCache] = useState<{
    cache_path: string;
    last_entry: string;
    updated_at: string;
  } | null>(null);
  const [profiles, setProfiles] = useState<
    { profile_id: string; internship_name: string; active: number; name?: string; start_date?: string }[]
  >([]);
  const [activeProfileId, setActiveProfileId] = useState<string | undefined>();
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [showSelector, setShowSelector] = useState(false);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [showEditProfile, setShowEditProfile] = useState(false);
  const [showTutorial, setShowTutorial] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [pendingWriteConfirmation, setPendingWriteConfirmation] = useState(false);
  const [pendingEditMode, setPendingEditMode] = useState(false);
  const [lastSubmittedMessage, setLastSubmittedMessage] = useState("");
  const [model, setModel] = useState<string>(() => {
    return localStorage.getItem("llm-model") || "gemini-2.5-flash";
  });
  const [availableModels, setAvailableModels] = useState<string[]>([
    "gemini-2-flash",
    "gemini-2.5-flash",
    "gemini-1.5-flash-001",
    "openrouter:nvidia/nemotron-3-nano-30b-a3b:free",
    "openrouter:openrouter/free",
    "openrouter:upstage/solar-pro-3:free",
    "openrouter:arcee-ai/trinity-large-preview:free"
  ]);
  const [googleApiConfigured, setGoogleApiConfigured] = useState(false);
  const [openrouterApiConfigured, setOpenrouterApiConfigured] = useState(false);
  const [openrouterBaseUrl, setOpenrouterBaseUrl] = useState("https://openrouter.ai/api/v1");
  const [showApiSetup, setShowApiSetup] = useState(false);
  const formatDay = (value: string) => {
    if (!value) return "";
    try {
      return new Date(value).toLocaleDateString();
    } catch {
      return value;
    }
  };
  const formatTimestamp = (value: string) => {
    if (!value) return "";
    try {
      return new Date(value).toLocaleString();
    } catch {
      return value;
    }
  };

  const templates = [
    "Summarize what I did today in my internship",
    "Extract tasks from this text",
    "What should I focus on next week?",
    "Prepare a weekly internship report",
    "Rewrite this note professionally",
    "Here are my raw notes. Rewrite them and save to Notes. Extract tasks, progress, and meeting summary, then organize files accordingly:\n\n[PASTE NOTES HERE]"
  ];

  const loadHistory = (sessionOverride?: string) => {
    const loader = sessionOverride
      ? fetchHistoryForSession(sessionOverride)
      : fetchHistory();
    loader
      .then((history) => {
        setSessionId(history.session_id);
        if (history.messages.length > 0) {
          const restored = history.messages.map((msg) => ({
            id: crypto.randomUUID(),
            role: (msg.role === "user" ? "user" : "assistant") as "user" | "assistant",
            text: msg.content
          }));
          setMessages(restored);
        } else {
          setMessages([]);
        }
        setPendingWriteConfirmation(false);
        setPendingEditMode(false);
      })
      .catch(() => {
        setStatusMessage("Unable to load history");
      });
  };

  const loadSessions = () => {
    fetchChatSessions()
      .then((data) => {
        setChatSessions(data.sessions);
        if (data.active_session_id) {
          setSessionId(data.active_session_id);
        }
      })
      .catch(() => {
        setStatusMessage("Unable to load chat sessions");
      });
  };

  const loadLatestCache = () => {
    fetchLatestProgressCache()
      .then((data) => {
        setLatestCache(data);
      })
      .catch(() => {
        setLatestCache(null);
      });
  };

  useEffect(() => {
    fetchProfiles()
      .then((data) => {
        setProfiles(data.profiles);
        setActiveProfileId(data.active_profile_id);
        setShowOnboarding(data.profiles.length === 0);
        setShowSelector(data.profiles.length > 0 && !data.active_profile_id);
        if (data.active_profile_id) {
          const seen = localStorage.getItem(`tutorial:${data.active_profile_id}`);
          if (!seen) {
            setShowTutorial(true);
          }
        }
      })
      .catch(() => {
        setStatusMessage("Unable to load profiles");
      });
    loadHistory();
    loadSessions();
    loadLatestCache();
    fetchModelSettings()
      .then((settings) => {
        setModel(settings.selected_model);
        setAvailableModels(settings.available_models);
        setGoogleApiConfigured(settings.google_api_key_configured);
        setOpenrouterApiConfigured(settings.openrouter_api_key_configured);
        setOpenrouterBaseUrl(settings.openrouter_base_url);
        setShowApiSetup(
          !settings.google_api_key_configured && !settings.openrouter_api_key_configured
        );
        localStorage.setItem("llm-model", settings.selected_model);
      })
      .catch(() => {
        setStatusMessage("Unable to load model settings");
      });
  }, []);

  const handleSend = async (text: string, displayText?: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;
    const shownText = (displayText || text).trim();
    if (!shownText) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      text: shownText
    };

    setMessages((prev) => [...prev, userMessage]);
    setStatus("loading");
    setStatusMessage("Processing...");
    setInputValue("");
    setPendingEditMode(false);
    if (!trimmed.toLowerCase().startsWith("edit:")) {
      setLastSubmittedMessage(shownText);
    }

    try {
      const response = await sendMessage(trimmed, sessionId, model);
      const isWritePermissionAsk =
        response.action === "ask" &&
        (response.reason === "Explicit write permission required" ||
          response.reason === "Awaiting confirmation" ||
          response.reason === "Draft cache created");
      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        text: response.message,
        actions: response.actions,
        files: response.files,
        notice: response.notice,
        intent: response.intent,
        action: response.action,
        reason: response.reason
      };
      setMessages((prev) => [...prev, assistantMessage]);
      setStatus("success");
      setStatusMessage("Done");
      setPendingWriteConfirmation(isWritePermissionAsk);
      loadSessions();
      loadLatestCache();
      if (response.message.toLowerCase().includes("no active profile")) {
        setShowOnboarding(true);
      }
    } catch (error) {
      setStatus("error");
      setStatusMessage("Request failed");
      setPendingWriteConfirmation(false);
      setPendingEditMode(false);
      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        text: "There was an error processing the request."
      };
      setMessages((prev) => [...prev, assistantMessage]);
    }
  };

  if (showApiSetup) {
    return (
      <div className="shell">
        <div className="background-glow" />
        <ApiSetupPage
          availableModels={availableModels}
          selectedModel={model}
          openrouterBaseUrl={openrouterBaseUrl}
          googleConfigured={googleApiConfigured}
          openrouterConfigured={openrouterApiConfigured}
          onSave={async (payload) => {
            const settings = await updateModelSettings(payload);
            setModel(settings.selected_model);
            setAvailableModels(settings.available_models);
            setGoogleApiConfigured(settings.google_api_key_configured);
            setOpenrouterApiConfigured(settings.openrouter_api_key_configured);
            setOpenrouterBaseUrl(settings.openrouter_base_url);
            localStorage.setItem("llm-model", settings.selected_model);
            if (settings.google_api_key_configured || settings.openrouter_api_key_configured) {
              setShowApiSetup(false);
            }
          }}
        />
      </div>
    );
  }

  if (showOnboarding) {
    return (
      <div className="shell">
        <div className="background-glow" />
        <header className="topbar">
          <div className="brand">
            <span className="brand-kicker">Intern Assistant</span>
            <h1>Profile setup</h1>
            <p>Scope your vault and restore your workspace anytime.</p>
          </div>
        </header>
        <OnboardingPage
          onCreated={(profile) => {
            setProfiles([profile]);
            setActiveProfileId(profile.profile_id);
            setShowOnboarding(false);
            setShowSelector(false);
            setShowTutorial(true);
            loadHistory();
            loadSessions();
            loadLatestCache();
          }}
        />
      </div>
    );
  }

  if (showTutorial) {
    return (
      <div className="shell">
        <div className="background-glow" />
        <TutorialPage
          onClose={() => {
            if (activeProfileId) {
              localStorage.setItem(`tutorial:${activeProfileId}`, "seen");
            }
            setShowTutorial(false);
          }}
        />
      </div>
    );
  }

  const activeProfile = profiles.find((p) => p.profile_id === activeProfileId);

  if (showSettings) {
    return (
      <div className="shell">
        <div className="background-glow" />
        <SettingsPage
          profile={activeProfile}
          modelSettings={{
            selected_model: model,
            available_models: availableModels,
            google_api_key_configured: googleApiConfigured,
            openrouter_api_key_configured: openrouterApiConfigured,
            openrouter_base_url: openrouterBaseUrl
          }}
          onBack={() => setShowSettings(false)}
          onSave={async (payload) => {
            const updated = await updateProfile({
              profile_id: payload.profile_id,
              name: payload.name,
              internship_name: payload.internship_name,
              start_date: payload.start_date,
              vault_root: payload.vault_root
            });
            setProfiles((prev) =>
              prev.map((p) => (p.profile_id === updated.profile_id ? updated : p))
            );
            const modelSettings = await updateModelSettings({
              selected_model: payload.selected_model,
              google_api_key: payload.google_api_key,
              openrouter_api_key: payload.openrouter_api_key,
              openrouter_base_url: payload.openrouter_base_url
            });
            setModel(modelSettings.selected_model);
            setAvailableModels(modelSettings.available_models);
            setGoogleApiConfigured(modelSettings.google_api_key_configured);
            setOpenrouterApiConfigured(modelSettings.openrouter_api_key_configured);
            setOpenrouterBaseUrl(modelSettings.openrouter_base_url);
            localStorage.setItem("llm-model", modelSettings.selected_model);
          }}
        />
      </div>
    );
  }

  if (showSelector) {
    return (
      <div className="shell">
        <div className="background-glow" />
        <header className="topbar">
          <div className="brand">
            <span className="brand-kicker">Intern Assistant</span>
            <h1>Select a profile</h1>
            <p>Switch contexts without mixing notes or history.</p>
          </div>
        </header>
        <ProfileSelector
          profiles={profiles}
          onSelect={async (profileId) => {
            await switchProfile(profileId);
            setActiveProfileId(profileId);
            setShowSelector(false);
            const seen = localStorage.getItem(`tutorial:${profileId}`);
            if (!seen) {
              setShowTutorial(true);
            }
            loadHistory();
            loadSessions();
            loadLatestCache();
          }}
          onCreate={async () => {
            setShowOnboarding(true);
            setShowSelector(false);
          }}
        />
      </div>
    );
  }

  return (
    <div className="shell">
      <div className="background-glow" />
      <header className="topbar">
        <div className="brand">
          <span className="brand-kicker">Astra Internship Copilot</span>
          <h1>Progress command desk</h1>
          <div className="brand-stats">
            <div className="stat-card">
              <span>Session focus</span>
              <strong>Internship ops</strong>
            </div>
            <div className="stat-card">
              <span>Mode</span>
              <strong>Intent-aware</strong>
            </div>
          </div>
        </div>
        <div className="topbar-controls">
          <div className="control-group">
            <label>Model</label>
            <select
              value={model}
              onChange={(event) => {
                const next = event.target.value;
                setModel(next);
                localStorage.setItem("llm-model", next);
                updateModelSettings({ selected_model: next }).catch(() => {
                  setStatusMessage("Failed to update selected model");
                });
              }}
            >
              {availableModels.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </div>
          <div className="profile-menu">
            <button
              type="button"
              className="profile-cta"
              onClick={() => setShowProfileMenu((prev) => !prev)}
            >
              <span className="profile-cta-label">
                {profiles.find((p) => p.profile_id === activeProfileId)?.internship_name ||
                  "Profile"}
              </span>
              <span className="profile-cta-sub">Manage profile</span>
            </button>
            {showProfileMenu && (
              <div className="profile-dropdown">
                <div className="profile-dropdown-title">
                  {profiles.find((p) => p.profile_id === activeProfileId)?.internship_name ||
                    "Profile"}
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setShowSelector(true);
                    setShowProfileMenu(false);
                  }}
                >
                  Switch profile
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowOnboarding(true);
                    setShowProfileMenu(false);
                  }}
                >
                  New profile
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowEditProfile(true);
                    setShowProfileMenu(false);
                  }}
                >
                  Edit profile
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowSettings(true);
                    setShowProfileMenu(false);
                  }}
                >
                  Settings
                </button>
                <button
                  type="button"
                  onClick={() => {
                    sendMessage("reset this conversation", sessionId).finally(() => {
                      setMessages([]);
                      loadHistory();
                      setShowProfileMenu(false);
                    });
                  }}
                >
                  Clear working context
                </button>
              </div>
            )}
          </div>
        </div>
      </header>
      <div className="workspace">
        <aside className="sidebar">
          <div className="sidebar-card">
            <div className="sidebar-title">Quick templates</div>
            <div className="template-list">
              {templates.map((template) => (
                <button
                  key={template}
                  className="template-item"
                  onClick={() => setInputValue(template)}
                  type="button"
                >
                  {template}
                </button>
              ))}
            </div>
          </div>
          <div className="sidebar-card">
            <div className="sidebar-title">Session pulse</div>
            <div className="sidebar-metrics">
              <div>
                <span>Messages</span>
                <strong>{messages.length}</strong>
              </div>
              <div>
                <span>Status</span>
                <strong>{status === "loading" ? "Working" : "Ready"}</strong>
              </div>
            </div>
          </div>
          <div className="sidebar-card">
            <div className="sidebar-title">Latest daily cache</div>
            <div className="sidebar-cache">
              {latestCache?.last_entry ? (
                <>
                  <div className="cache-entry">{latestCache.last_entry}</div>
                  <div className="cache-meta">
                    Updated {formatTimestamp(latestCache.updated_at)}
                  </div>
                  <div className="cache-meta">{latestCache.cache_path}</div>
                </>
              ) : (
                <div className="cache-entry empty">
                  No cache entries yet for today. Send a daily update to start.
                </div>
              )}
            </div>
          </div>
        </aside>
        <main className="chat-panel">
          <StatusBar status={status} message={statusMessage} />
          <ChatWindow messages={messages} loading={status === "loading"} />
          {pendingWriteConfirmation && (
            <div className="confirm-bar">
              <div className="confirm-bar-text">
                This request needs permission before saving to your vault.
              </div>
              <div className="confirm-bar-actions">
                <button
                  type="button"
                  className="primary"
                  disabled={status === "loading"}
                  onClick={() => {
                    setPendingWriteConfirmation(false);
                    handleSend("confirm", "Confirm save");
                  }}
                >
                  Confirm save
                </button>
                <button
                  type="button"
                  className="ghost"
                  disabled={status === "loading"}
                  onClick={() => {
                    setPendingEditMode(true);
                    setPendingWriteConfirmation(false);
                    setInputValue(lastSubmittedMessage);
                    setStatusMessage(
                      "Edit mode enabled. Update your message and submit."
                    );
                  }}
                >
                  Edit previous message
                </button>
              </div>
            </div>
          )}
          <InputBox
            value={inputValue}
            onChange={setInputValue}
            onSend={(text) => {
              if (pendingEditMode) {
                handleSend(`edit: ${text}`, text);
                return;
              }
              handleSend(text);
            }}
            disabled={status === "loading"}
          />
        </main>
        <aside className="inspector">
          <div className="inspector-card">
            <div className="inspector-title">Daily chat history</div>
            <div className="inspector-body">
              {chatSessions.length === 0 && "No chat sessions yet."}
              {chatSessions.length > 0 && (
                <div className="chat-history-list">
                  {chatSessions.map((session) => (
                    <button
                      key={session.session_id}
                      type="button"
                      className={`chat-history-item ${
                        session.session_id === sessionId ? "active" : ""
                      }`}
                      onClick={() => {
                        loadHistory(session.session_id);
                        setSessionId(session.session_id);
                      }}
                    >
                      <div className="chat-history-day">{formatDay(session.day)}</div>
                      <div className="chat-history-meta">
                        Updated {formatTimestamp(session.updated_at)}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </aside>
      </div>
      {showEditProfile && (
        <div className="modal">
          <div className="modal-card">
            <h2>Edit profile</h2>
            <div className="modal-grid">
              <input
                placeholder="Name"
                defaultValue={
                  profiles.find((p) => p.profile_id === activeProfileId)?.name || ""
                }
                id="profile-name"
              />
              <input
                placeholder="Internship name"
                defaultValue={
                  profiles.find((p) => p.profile_id === activeProfileId)?.internship_name || ""
                }
                id="profile-internship"
              />
              <input
                placeholder="Start date (YYYY-MM-DD)"
                defaultValue={
                  profiles.find((p) => p.profile_id === activeProfileId)?.start_date || ""
                }
                id="profile-start-date"
              />
              <input placeholder="Vault root" id="profile-vault" />
            </div>
            <div className="modal-actions">
              <button
                type="button"
                className="ghost"
                onClick={() => setShowEditProfile(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="primary"
                onClick={async () => {
                  const payload = {
                    profile_id: activeProfileId || "",
                    name: (document.getElementById("profile-name") as HTMLInputElement)
                      ?.value,
                    internship_name: (
                      document.getElementById("profile-internship") as HTMLInputElement
                    )?.value,
                    start_date: (
                      document.getElementById("profile-start-date") as HTMLInputElement
                    )?.value,
                    vault_root: (
                      document.getElementById("profile-vault") as HTMLInputElement
                    )?.value
                  };
                  const updated = await updateProfile(payload);
                  setProfiles((prev) =>
                    prev.map((p) => (p.profile_id === updated.profile_id ? updated : p))
                  );
                  setShowEditProfile(false);
                }}
              >
                Save changes
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
