interface LoadingSpinnerProps {
  message?: string;
}

export default function LoadingSpinner({
  message = "Loading data",
}: LoadingSpinnerProps) {
  return (
    <div className="status-shell" role="status" aria-live="polite">
      <div className="spinner" />
      <p className="status-copy">{message}</p>
    </div>
  );
}
