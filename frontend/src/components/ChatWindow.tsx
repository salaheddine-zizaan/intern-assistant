import { useEffect, useRef, useState } from "react";
import MessageBubble from "./MessageBubble";
import type { Message } from "../App";

type Props = {
  messages: Message[];
};

export default function ChatWindow({ messages }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [showScrollDown, setShowScrollDown] = useState(false);

  const checkScroll = () => {
    const el = containerRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 20;
    setShowScrollDown(!atBottom);
  };

  useEffect(() => {
    checkScroll();
  }, [messages.length]);

  return (
    <div className="chat-window" ref={containerRef} onScroll={checkScroll}>
      {messages.length === 0 && (
        <div className="empty-state">
          <div className="empty-title">Start with a command</div>
          <div className="empty-body">
            Try: “Summarize today’s meeting and extract tasks.”
          </div>
        </div>
      )}
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}
      {showScrollDown && (
        <button
          type="button"
          className="scroll-down"
          onClick={() => {
            const el = containerRef.current;
            if (el) {
              el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
            }
          }}
        >
          Scroll to latest
        </button>
      )}
    </div>
  );
}
