import { useEffect, useState, type InputHTMLAttributes } from "react";

type DirectoryInputProps = InputHTMLAttributes<HTMLInputElement> & {
  webkitdirectory?: string;
  directory?: string;
};

type ProfileShape = {
  profile_id: string;
  name?: string;
  internship_name: string;
  start_date?: string;
  vault_root?: string;
};

type Props = {
  profile: ProfileShape | undefined;
  modelSettings: {
    selected_model: string;
    available_models: string[];
    google_api_key_configured: boolean;
    openrouter_api_key_configured: boolean;
    openrouter_base_url: string;
  };
  onBack: () => void;
  onSave: (payload: {
    profile_id: string;
    name?: string;
    internship_name?: string;
    start_date?: string;
    vault_root?: string;
    selected_model?: string;
    google_api_key?: string;
    openrouter_api_key?: string;
    openrouter_base_url?: string;
  }) => Promise<void>;
};

export default function SettingsPage({ profile, modelSettings, onBack, onSave }: Props) {
  const [name, setName] = useState("");
  const [internshipName, setInternshipName] = useState("");
  const [startDate, setStartDate] = useState("");
  const [vaultRoot, setVaultRoot] = useState("");
  const [selectedModel, setSelectedModel] = useState(modelSettings.selected_model);
  const [googleApiKey, setGoogleApiKey] = useState("");
  const [openRouterApiKey, setOpenRouterApiKey] = useState("");
  const [openRouterBaseUrl, setOpenRouterBaseUrl] = useState(modelSettings.openrouter_base_url);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (!profile) return;
    setName(profile.name || "");
    setInternshipName(profile.internship_name || "");
    setStartDate(profile.start_date || "");
    setVaultRoot(profile.vault_root || "");
  }, [profile]);

  useEffect(() => {
    setSelectedModel(modelSettings.selected_model);
    setOpenRouterBaseUrl(modelSettings.openrouter_base_url);
  }, [modelSettings]);

  if (!profile) {
    return (
      <div className="settings-shell">
        <div className="settings-card">
          <h2>No active profile</h2>
          <p>Select or create a profile before opening settings.</p>
          <div className="settings-actions">
            <button type="button" className="primary" onClick={onBack}>
              Back
            </button>
          </div>
        </div>
      </div>
    );
  }

  const handleSave = async () => {
    if (!internshipName.trim()) {
      setError("Internship name is required.");
      return;
    }
    setError("");
    setSaved("");
    setIsSaving(true);
    try {
      await onSave({
        profile_id: profile.profile_id,
        name,
        internship_name: internshipName,
        start_date: startDate,
        vault_root: vaultRoot,
        selected_model: selectedModel,
        google_api_key: googleApiKey.trim() || undefined,
        openrouter_api_key: openRouterApiKey.trim() || undefined,
        openrouter_base_url: openRouterBaseUrl.trim() || undefined
      });
      setSaved("Settings saved.");
      setGoogleApiKey("");
      setOpenRouterApiKey("");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to save settings.";
      setError(message);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="settings-shell">
      <div className="settings-card">
        <div className="settings-header">
          <span className="brand-kicker">Settings</span>
          <h2>Profile and vault management</h2>
          <p>Update your internship profile, model defaults, and API credentials.</p>
        </div>

        <div className="settings-grid">
          <label className="field">
            <span>Name</span>
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Your name"
            />
          </label>
          <label className="field">
            <span>Internship name</span>
            <input
              value={internshipName}
              onChange={(event) => setInternshipName(event.target.value)}
              placeholder="Internship name"
            />
          </label>
          <label className="field">
            <span>Start date</span>
            <input
              type="date"
              value={startDate}
              onChange={(event) => setStartDate(event.target.value)}
            />
          </label>
          <label className="field field-full">
            <span>Vault location</span>
            <input
              value={vaultRoot}
              onChange={(event) => setVaultRoot(event.target.value)}
              placeholder="C:\\Users\\You\\Documents\\Internship Vault"
            />
          </label>
          <div className="field field-full">
            <span>Browse vault folder</span>
            <label className="vault-button settings-vault-button">
              Select folder
              <input
                {...({ type: "file", webkitdirectory: "true" } as DirectoryInputProps)}
                onChange={(event) => {
                  const files = event.target.files;
                  if (!files || files.length === 0) return;
                  const first = files[0];
                  const relPath = (first as File & { webkitRelativePath?: string })
                    .webkitRelativePath;
                  if (!relPath) return;
                  const folderName = relPath.split("/")[0];
                  setVaultRoot(folderName);
                }}
              />
            </label>
          </div>

          <div className="field field-full">
            <h3>Model management</h3>
          </div>
          <label className="field field-full">
            <span>Default model</span>
            <select
              value={selectedModel}
              onChange={(event) => setSelectedModel(event.target.value)}
            >
              {modelSettings.available_models.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <label className="field field-full">
            <span>Gemini API key</span>
            <input
              type="password"
              value={googleApiKey}
              onChange={(event) => setGoogleApiKey(event.target.value)}
              placeholder={
                modelSettings.google_api_key_configured
                  ? "Already configured (enter new key to replace)"
                  : "Paste GOOGLE_API_KEY"
              }
            />
          </label>
          <label className="field field-full">
            <span>OpenRouter API key</span>
            <input
              type="password"
              value={openRouterApiKey}
              onChange={(event) => setOpenRouterApiKey(event.target.value)}
              placeholder={
                modelSettings.openrouter_api_key_configured
                  ? "Already configured (enter new key to replace)"
                  : "Paste OPENROUTER_API_KEY"
              }
            />
          </label>
          <label className="field field-full">
            <span>OpenRouter base URL</span>
            <input
              value={openRouterBaseUrl}
              onChange={(event) => setOpenRouterBaseUrl(event.target.value)}
              placeholder="https://openrouter.ai/api/v1"
            />
          </label>
        </div>

        {error && <div className="form-error">{error}</div>}
        {saved && <div className="form-success">{saved}</div>}

        <div className="settings-actions">
          <button type="button" className="ghost" onClick={onBack}>
            Back
          </button>
          <button
            type="button"
            className="primary"
            disabled={isSaving}
            onClick={handleSave}
          >
            {isSaving ? "Saving..." : "Save settings"}
          </button>
        </div>
      </div>
    </div>
  );
}
