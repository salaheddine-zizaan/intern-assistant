import { useEffect, useRef, useState } from "react";
import MessageBubble from "./MessageBubble";
import type { Message } from "../App";

type Props = {
  messages: Message[];
  loading?: boolean;
};

export default function ChatWindow({ messages, loading = false }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [showScrollDown, setShowScrollDown] = useState(false);
  const isAutoScrolling = useRef(false);

  const checkScroll = () => {
    const el = containerRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 20;
    setShowScrollDown(!atBottom);
  };

  useEffect(() => {
    checkScroll();
  }, [messages.length]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    isAutoScrolling.current = true;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    const id = window.setTimeout(() => {
      isAutoScrolling.current = false;
    }, 300);
    return () => window.clearTimeout(id);
  }, [messages.length, loading]);

  return (
    <div
      className="chat-window"
      ref={containerRef}
      onScroll={() => {
        if (!isAutoScrolling.current) {
          checkScroll();
        }
      }}
    >
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
      {loading && (
        <div className="bubble assistant typing-bubble" aria-live="polite">
          <div className="typing-indicator">
            <span className="dot" />
            <span className="dot" />
            <span className="dot" />
          </div>
        </div>
      )}
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
