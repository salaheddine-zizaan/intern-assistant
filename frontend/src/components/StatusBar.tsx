type Props = {
  status: "idle" | "loading" | "success" | "error";
  message: string;
};

export default function StatusBar({ status, message }: Props) {
  return (
    <div className={`status-bar ${status}`}>
      <span className="status-label">{status.toUpperCase()}</span>
      <span className="status-message">{message}</span>
    </div>
  );
}
