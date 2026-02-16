import { useState } from "react";

type Props = {
  availableModels: string[];
  selectedModel: string;
  openrouterBaseUrl: string;
  googleConfigured: boolean;
  openrouterConfigured: boolean;
  onSave: (payload: {
    selected_model?: string;
    google_api_key?: string;
    openrouter_api_key?: string;
    openrouter_base_url?: string;
  }) => Promise<void>;
};

export default function ApiSetupPage({
  availableModels,
  selectedModel,
  openrouterBaseUrl,
  googleConfigured,
  openrouterConfigured,
  onSave
}: Props) {
  const [model, setModel] = useState(selectedModel);
  const [googleApiKey, setGoogleApiKey] = useState("");
  const [openRouterApiKey, setOpenRouterApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState(openrouterBaseUrl);
  const [error, setError] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  const handleSubmit = async () => {
    const googleTrimmed = googleApiKey.trim();
    const openrouterTrimmed = openRouterApiKey.trim();

    if (!googleTrimmed && !openrouterTrimmed && !googleConfigured && !openrouterConfigured) {
      setError("Add at least one API key to continue.");
      return;
    }

    setError("");
    setIsSaving(true);
    try {
      await onSave({
        selected_model: model,
        google_api_key: googleTrimmed || undefined,
        openrouter_api_key: openrouterTrimmed || undefined,
        openrouter_base_url: baseUrl.trim() || undefined
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to save API settings.";
      setError(message);
      setIsSaving(false);
    }
  };

  return (
    <div className="api-setup-shell">
      <section className="api-setup-card">
        <div className="api-setup-header">
          <span className="brand-kicker">Intern Assistant</span>
          <h2>Connect your model provider</h2>
          <p>
            Configure Gemini or OpenRouter once. The app stores credentials locally and starts directly next time.
          </p>
        </div>

        <div className="api-setup-grid">
          <label className="field field-full">
            <span>Default model</span>
            <select value={model} onChange={(event) => setModel(event.target.value)}>
              {availableModels.map((option) => (
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
              placeholder={googleConfigured ? "Configured already (enter to replace)" : "Paste GOOGLE_API_KEY"}
            />
          </label>

          <label className="field field-full">
            <span>OpenRouter API key</span>
            <input
              type="password"
              value={openRouterApiKey}
              onChange={(event) => setOpenRouterApiKey(event.target.value)}
              placeholder={
                openrouterConfigured ? "Configured already (enter to replace)" : "Paste OPENROUTER_API_KEY"
              }
            />
          </label>

          <label className="field field-full">
            <span>OpenRouter base URL</span>
            <input
              value={baseUrl}
              onChange={(event) => setBaseUrl(event.target.value)}
              placeholder="https://openrouter.ai/api/v1"
            />
          </label>
        </div>

        {error && <div className="form-error">{error}</div>}

        <div className="api-setup-actions">
          <button type="button" className="primary" disabled={isSaving} onClick={handleSubmit}>
            {isSaving ? "Saving..." : "Save and continue"}
          </button>
        </div>
      </section>
    </div>
  );
}
