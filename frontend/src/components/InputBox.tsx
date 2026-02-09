type Props = {
  value: string;
  onChange: (value: string) => void;
  onSend: (text: string) => void;
  disabled?: boolean;
};

export default function InputBox({ value, onChange, onSend, disabled }: Props) {

  const handleSend = () => {
    if (!value.trim()) return;
    onSend(value);
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!disabled) {
        handleSend();
      }
    }
  };

  return (
    <div className="input-box">
      <textarea
        placeholder="Type a command. Press Enter to send."
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
      />
      <button onClick={handleSend} disabled={disabled || !value.trim()}>
        Send
      </button>
    </div>
  );
}
