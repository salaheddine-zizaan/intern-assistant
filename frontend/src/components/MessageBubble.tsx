import type { Message } from "../App";

type Props = {
  message: Message;
};

type Block =
  | { type: "p"; text: string }
  | { type: "ul"; items: string[] }
  | { type: "ol"; items: string[] }
  | { type: "h"; level: number; text: string };

function renderInline(text: string) {
  const parts: Array<string | { bold: string }> = [];
  const regex = /\*\*(.+?)\*\*/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    parts.push({ bold: match[1] });
    lastIndex = regex.lastIndex;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts.map((part, index) => {
    if (typeof part === "string") {
      return <span key={index}>{part}</span>;
    }
    return <strong key={index}>{part.bold}</strong>;
  });
}

function parseBlocks(text: string): Block[] {
  const lines = text.split(/\r?\n/);
  const blocks: Block[] = [];
  let para: string[] = [];
  let listType: "ul" | "ol" | null = null;
  let listItems: string[] = [];

  const flushPara = () => {
    if (para.length > 0) {
      blocks.push({ type: "p", text: para.join(" ") });
      para = [];
    }
  };

  const flushList = () => {
    if (listType && listItems.length > 0) {
      blocks.push({ type: listType, items: listItems });
    }
    listType = null;
    listItems = [];
  };

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) {
      flushPara();
      flushList();
      continue;
    }

    const headingMatch = trimmed.match(/^(#{1,3})\s+(.+)/);
    if (headingMatch) {
      flushPara();
      flushList();
      blocks.push({
        type: "h",
        level: headingMatch[1].length,
        text: headingMatch[2],
      });
      continue;
    }

    const ulMatch = trimmed.match(/^[-*]\s+(.+)/);
    if (ulMatch) {
      flushPara();
      if (listType && listType !== "ul") {
        flushList();
      }
      listType = "ul";
      listItems.push(ulMatch[1]);
      continue;
    }

    const olMatch = trimmed.match(/^\d+[.)]\s+(.+)/);
    if (olMatch) {
      flushPara();
      if (listType && listType !== "ol") {
        flushList();
      }
      listType = "ol";
      listItems.push(olMatch[1]);
      continue;
    }

    if (listType) {
      flushList();
    }
    para.push(trimmed);
  }

  flushPara();
  flushList();

  return blocks;
}

function renderBlocks(text: string) {
  const blocks = parseBlocks(text);
  return blocks.map((block, index) => {
    if (block.type === "p") {
      return (
        <p key={index} className="bubble-paragraph">
          {renderInline(block.text)}
        </p>
      );
    }
    if (block.type === "ul") {
      return (
        <ul key={index} className="bubble-list">
          {block.items.map((item, itemIndex) => (
            <li key={itemIndex}>{renderInline(item)}</li>
          ))}
        </ul>
      );
    }
    if (block.type === "ol") {
      return (
        <ol key={index} className="bubble-list ordered">
          {block.items.map((item, itemIndex) => (
            <li key={itemIndex}>{renderInline(item)}</li>
          ))}
        </ol>
      );
    }

    const HeadingTag =
      block.level === 1 ? "h3" : block.level === 2 ? "h4" : "h5";
    return (
      <HeadingTag key={index} className="bubble-heading">
        {renderInline(block.text)}
      </HeadingTag>
    );
  });
}

export default function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";
  return (
    <div className={`bubble ${isUser ? "user" : "assistant"}`}>
      <div className="bubble-text">{renderBlocks(message.text)}</div>
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
