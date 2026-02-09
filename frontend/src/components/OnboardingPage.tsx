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

  const handleSubmit = async () => {
    if (!name.trim() || !internshipName.trim() || !startDate.trim()) {
      return;
    }
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
  };

  return (
    <div className="onboarding-card">
      <div className="onboarding-section">
        <h2>About you</h2>
        <input
          placeholder="Your name"
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
      </div>
      <div className="onboarding-section">
        <h2>Internship</h2>
        <input
          placeholder="Internship name"
          value={internshipName}
          onChange={(event) => setInternshipName(event.target.value)}
        />
        <input
          placeholder="Company (optional)"
          value={company}
          onChange={(event) => setCompany(event.target.value)}
        />
        <input
          placeholder="Role (optional)"
          value={role}
          onChange={(event) => setRole(event.target.value)}
        />
        <input
          type="date"
          value={startDate}
          onChange={(event) => setStartDate(event.target.value)}
        />
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
        <input
          placeholder="Optional absolute path (if known)"
          value={vaultRoot}
          onChange={(event) => setVaultRoot(event.target.value)}
        />
        <p>
          We will create the vault structure inside this folder. Browsers cannot
          read absolute paths; you can paste it manually if needed.
        </p>
      </div>
      <button type="button" className="primary" onClick={handleSubmit}>
        Create profile
      </button>
    </div>
  );
}
