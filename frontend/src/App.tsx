import { useEffect, useState } from "react";
import ChatWindow from "./components/ChatWindow";
import InputBox from "./components/InputBox";
import StatusBar from "./components/StatusBar";
import {
  fetchHistory,
  fetchProfiles,
  sendMessage,
  switchProfile,
  updateProfile
} from "./services/api";
import OnboardingPage from "./components/OnboardingPage";
import ProfileSelector from "./components/ProfileSelector";

export type Message = {
  id: string;
  role: "user" | "assistant";
  text: string;
  actions?: string[];
  files?: string[];
  notice?: string;
};

type Status = "idle" | "loading" | "success" | "error";

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [status, setStatus] = useState<Status>("idle");
  const [statusMessage, setStatusMessage] = useState<string>("");
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [inputValue, setInputValue] = useState<string>("");
  const [profiles, setProfiles] = useState<
    { profile_id: string; internship_name: string; active: number; name?: string; start_date?: string }[]
  >([]);
  const [activeProfileId, setActiveProfileId] = useState<string | undefined>();
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [showSelector, setShowSelector] = useState(false);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [showEditProfile, setShowEditProfile] = useState(false);
  const [model, setModel] = useState<string>(() => {
    return localStorage.getItem("llm-model") || "gemini-2-flash";
  });
  const lastAssistant = [...messages].reverse().find((msg) => msg.role === "assistant");

  const templates = [
    "Summarize what I did today in my internship",
    "Extract tasks from this text",
    "What should I focus on next week?",
    "Prepare a weekly internship report",
    "Rewrite this note professionally",
    "Here are my raw notes. Rewrite them and save to Notes. Extract tasks, progress, and meeting summary, then organize files accordingly:\n\n[PASTE NOTES HERE]"
  ];

  const loadHistory = () => {
    fetchHistory()
      .then((history) => {
        setSessionId(history.session_id);
        if (history.messages.length > 0) {
          const restored = history.messages.map((msg) => ({
            id: crypto.randomUUID(),
            role: msg.role === "user" ? "user" : "assistant",
            text: msg.content
          }));
          setMessages(restored);
        } else {
          setMessages([]);
        }
      })
      .catch(() => {
        setStatusMessage("Unable to load history");
      });
  };

  useEffect(() => {
    fetchProfiles()
      .then((data) => {
        setProfiles(data.profiles);
        setActiveProfileId(data.active_profile_id);
        setShowOnboarding(data.profiles.length === 0);
        setShowSelector(data.profiles.length > 0 && !data.active_profile_id);
      })
      .catch(() => {
        setStatusMessage("Unable to load profiles");
      });
    loadHistory();
  }, []);

  const handleSend = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      text: trimmed
    };

    setMessages((prev) => [...prev, userMessage]);
    setStatus("loading");
    setStatusMessage("Processing...");
    setInputValue("");

    try {
      const response = await sendMessage(trimmed, sessionId, model);
      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        text: response.message,
        actions: response.actions,
        files: response.files,
        notice: response.notice
      };
      setMessages((prev) => [...prev, assistantMessage]);
      setStatus("success");
      setStatusMessage("Done");
    } catch (error) {
      setStatus("error");
      setStatusMessage("Request failed");
      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        text: "There was an error processing the request."
      };
      setMessages((prev) => [...prev, assistantMessage]);
    }
  };

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
            loadHistory();
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
            loadHistory();
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
          <p>Capture notes, turn them into actions, and ship reports in minutes.</p>
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
              }}
            >
              <option value="gemini-2-flash">gemini-2-flash</option>
              <option value="gemini-2.5-flash">gemini-2.5-flash</option>
              <option value="gemini-1.5-flash-001">gemini-1.5-flash-001</option>
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
            <div className="sidebar-title">Focus checklist</div>
            <ul className="sidebar-list">
              <li>Summaries stay read-only unless you say “save”.</li>
              <li>Progress logs create weekly rollups automatically.</li>
              <li>Notes, tasks, meetings stay organized by week.</li>
            </ul>
          </div>
        </aside>
        <main className="chat-panel">
          <StatusBar status={status} message={statusMessage} />
          <ChatWindow messages={messages} loading={status === "loading"} />
          <InputBox
            value={inputValue}
            onChange={setInputValue}
            onSend={handleSend}
            disabled={status === "loading"}
          />
        </main>
        <aside className="inspector">
          <div className="inspector-card">
            <div className="inspector-title">Latest response</div>
            <div className="inspector-body">
              {lastAssistant ? lastAssistant.text : "No assistant response yet."}
            </div>
          </div>
          <div className="inspector-card">
            <div className="inspector-title">Actions</div>
            <div className="inspector-body">
              {lastAssistant?.actions && lastAssistant.actions.length > 0
                ? lastAssistant.actions.join(", ")
                : "No actions performed."}
            </div>
          </div>
          <div className="inspector-card">
            <div className="inspector-title">Files</div>
            <div className="inspector-body">
              {lastAssistant?.files && lastAssistant.files.length > 0
                ? lastAssistant.files.join("\n")
                : "No files written."}
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
