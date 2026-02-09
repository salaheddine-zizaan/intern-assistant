import type { Message } from "../App";

type Props = {
  message: Message;
};

export default function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";
  return (
    <div className={`bubble ${isUser ? "user" : "assistant"}`}>
      <div className="bubble-text">{message.text}</div>
      {!isUser && message.notice && (
        <div className="bubble-notice">{message.notice}</div>
      )}
      {!isUser && message.actions && message.actions.length > 0 && (
        <div className="bubble-meta">
          <div className="meta-title">Actions</div>
          <ul>
            {message.actions.map((action) => (
              <li key={action}>{action}</li>
            ))}
          </ul>
        </div>
      )}
      {!isUser && message.files && message.files.length > 0 && (
        <div className="bubble-meta">
          <div className="meta-title">Files</div>
          <ul>
            {message.files.map((file) => (
              <li key={file}>{file}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
