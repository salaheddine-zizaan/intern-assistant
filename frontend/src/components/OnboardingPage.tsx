import { useState } from "react";
import { createProfile } from "../services/api";

type Props = {
  onCreated: (profile: {
    profile_id: string;
    internship_name: string;
    start_date: string;
  }) => void;
};

export default function OnboardingPage({ onCreated }: Props) {
  const [name, setName] = useState("");
  const [internshipName, setInternshipName] = useState("");
  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");
  const [startDate, setStartDate] = useState("");
  const [vaultRoot, setVaultRoot] = useState("");
  const [vaultLabel, setVaultLabel] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!name.trim() || !internshipName.trim() || !startDate.trim()) {
      setError("Name, internship name, and start date are required.");
      return;
    }
    setError("");
    setIsSubmitting(true);
    try {
      const profile = await createProfile(internshipName, {
        name,
        start_date: startDate,
        vault_root: vaultRoot || undefined
      });
      localStorage.setItem(
        `profile:${profile.profile_id}:details`,
        JSON.stringify({ company, role })
      );
      onCreated(profile);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to create profile.";
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="onboarding-card">
      <div className="onboarding-section">
        <h2>About you</h2>
        <label className="field">
          <span>Your name</span>
          <input
            placeholder="e.g. Salah"
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </label>
      </div>
      {error && <div className="form-error">{error}</div>}
      <div className="onboarding-section">
        <h2>Internship</h2>
        <div className="form-grid">
          <label className="field">
            <span>Internship name</span>
            <input
              placeholder="e.g. AI Operations"
              value={internshipName}
              onChange={(event) => setInternshipName(event.target.value)}
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
          <label className="field">
            <span>Company (optional)</span>
            <input
              placeholder="e.g. ENSI"
              value={company}
              onChange={(event) => setCompany(event.target.value)}
            />
          </label>
          <label className="field">
            <span>Role (optional)</span>
            <input
              placeholder="e.g. AI Intern"
              value={role}
              onChange={(event) => setRole(event.target.value)}
            />
          </label>
        </div>
      </div>
      <div className="onboarding-section">
        <h2>Vault location</h2>
        <div className="vault-picker">
          <label className="vault-button">
            Browse folder
            <input
              type="file"
              webkitdirectory="true"
              onChange={(event) => {
                const files = event.target.files;
                if (!files || files.length === 0) return;
                const first = files[0];
                const relPath = (first as File & { webkitRelativePath?: string })
                  .webkitRelativePath;
                if (relPath) {
                  const folderName = relPath.split("/")[0];
                  setVaultLabel(folderName);
                  setVaultRoot(folderName);
                }
              }}
            />
          </label>
          <span className="vault-label">
            {vaultLabel || "No folder selected"}
          </span>
        </div>
        <label className="field">
          <span>Optional absolute path</span>
          <input
            placeholder="C:\\Users\\You\\Documents\\Internship Vault"
            value={vaultRoot}
            onChange={(event) => setVaultRoot(event.target.value)}
          />
        </label>
        <p>
          We will create the vault structure inside this folder. Browsers cannot
          read absolute paths; you can paste it manually if needed.
        </p>
      </div>
      <button type="button" className="primary" onClick={handleSubmit}>
        {isSubmitting ? "Creating..." : "Create profile"}
      </button>
    </div>
  );
}
