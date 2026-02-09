type Props = {
  profiles: { profile_id: string; internship_name: string; start_date?: string }[];
  onSelect: (profileId: string) => void;
  onCreate: () => void;
};

export default function ProfileSelector({ profiles, onSelect, onCreate }: Props) {
  return (
    <div className="onboarding-card">
      <div className="onboarding-section">
        <h2>Choose a profile</h2>
        <div className="profile-list">
          {profiles.map((profile) => (
            <div key={profile.profile_id} className="profile-item">
              <div>
                <div className="profile-title">{profile.internship_name}</div>
                <div className="profile-subtitle">
                  Start date: {profile.start_date || "Not set"}
                </div>
              </div>
              <button type="button" onClick={() => onSelect(profile.profile_id)}>
                Select
              </button>
            </div>
          ))}
        </div>
      </div>
      <button type="button" className="primary" onClick={onCreate}>
        Add new profile
      </button>
    </div>
  );
}
