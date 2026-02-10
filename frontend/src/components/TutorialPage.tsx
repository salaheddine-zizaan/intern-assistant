import { useMemo, useState } from "react";

type Props = {
  onClose: () => void;
};

type Step = {
  title: string;
  subtitle: string;
  points: string[];
  example: string;
  tree?: string;
};

export default function TutorialPage({ onClose }: Props) {
  const steps = useMemo<Step[]>(
    () => [
      {
        title: "Welcome to your getting-started guide",
        subtitle:
          "This short tutorial shows how the internship assistant works, what it can do, and how to get the best results.",
        points: [
          "Local-first, professional workflow designed for interns.",
          "Intent-aware responses: chat vs. write actions are separated.",
          "You stay in control of what gets saved."
        ],
        example: "“What did I achieve today?”"
      },
      {
        title: "Notes management",
        subtitle:
          "Notes are organized by week and category so your vault stays clean.",
        points: [
          "Learning and Ideas are separated automatically.",
          "Messy notes get cleaned into structured Markdown.",
          "Files are named clearly and stored by week."
        ],
        example: "“Organize these notes into Learning.”"
      },
      {
        title: "Tasks management",
        subtitle: "Tasks are extracted with blockers and tracked by day.",
        points: [
          "Extract tasks from notes or meetings.",
          "Ask for open tasks without writing files.",
          "Blockers are highlighted for follow‑up."
        ],
        example: "“Extract tasks from this text.”"
      },
      {
        title: "Meetings & decisions",
        subtitle:
          "Meeting summaries are concise and include action items automatically.",
        points: [
          "Summaries capture decisions and follow‑ups.",
          "Tasks get created from meeting notes.",
          "Stored in the correct weekly folder."
        ],
        example: "“Summarize this meeting and extract tasks.”"
      },
      {
        title: "Progress & reporting",
        subtitle:
          "Daily logs and weekly summaries are generated from your context.",
        points: [
          "Daily progress uses notes, tasks, and meetings.",
          "Weekly summary is created automatically.",
          "Reports pull from weekly progress data."
        ],
        example: "“Log today’s progress: done, blockers, next.”"
      },
      {
        title: "Vault structure overview",
        subtitle:
          "Your Obsidian vault stays structured by year, month, week, and content type.",
        points: [
          "Notes, Tasks, Meetings, and Progress are separated per week.",
          "Reports live under Reports by year and month.",
          "Templates stay at the root for easy reuse."
        ],
        example:
          "vault/2026/02/Week-2/Meetings/2026-02-10-kickoff-meeting.md",
        tree:
          "vault/\n" +
          "  2026/\n" +
          "    02/\n" +
          "      Week-2/\n" +
          "        Meetings/\n" +
          "        Tasks/\n" +
          "        Progress/\n" +
          "        Notes/\n" +
          "  Reports/\n" +
          "    2026/\n" +
          "      02/\n" +
          "  Templates/"
      },
      {
        title: "You’re ready",
        subtitle:
          "Start with a small command, then let the assistant keep you on track.",
        points: [
          "Use the templates to move fast.",
          "Review history by day in the right sidebar.",
          "Keep it conversational — it remembers context."
        ],
        example: "“Generate my weekly internship report.”"
      }
    ],
    []
  );

  const [index, setIndex] = useState(0);
  const step = steps[index];
  const isLast = index === steps.length - 1;

  return (
    <div className="tutorial-shell">
      <div className={`tutorial-card ${isLast ? "last" : ""}`}>
        <div className="tutorial-progress">
          {steps.map((_, stepIndex) => (
            <span
              key={`dot-${stepIndex}`}
              className={`tutorial-dot ${stepIndex <= index ? "active" : ""}`}
            />
          ))}
        </div>
        <div className="tutorial-header">
          <span className="tutorial-kicker">Internship guide</span>
          <h2>{step.title}</h2>
          <p>{step.subtitle}</p>
        </div>
        <div className="tutorial-body">
          <ul>
            {step.points.map((point) => (
              <li key={point}>{point}</li>
            ))}
          </ul>
          {step.tree && <pre className="tutorial-tree">{step.tree}</pre>}
          <div className="tutorial-example">
            <span>Example</span>
            <code>{step.example}</code>
          </div>
        </div>
        <div className={`tutorial-actions ${isLast ? "center" : ""}`}>
          {index > 0 && (
            <button
              type="button"
              className="ghost"
              onClick={() => setIndex((prev) => Math.max(prev - 1, 0))}
            >
              Back
            </button>
          )}
          <button
            type="button"
            className={`primary ${isLast ? "primary-highlight" : ""}`}
            onClick={() => {
              if (isLast) {
                onClose();
              } else {
                setIndex((prev) => Math.min(prev + 1, steps.length - 1));
              }
            }}
          >
            {isLast ? "Start now" : "Next"}
          </button>
        </div>
      </div>
    </div>
  );
}
