interface ErrorMessageProps { message: string; onRetry?: () => void; }

export default function ErrorMessage({ message, onRetry }: ErrorMessageProps) {
  return (
    <div className="status-shell" role="alert">
      <div className="status-badge">Error</div>
      <p className="status-copy">{message}</p>
      {onRetry ? <button type="button" className="button button-secondary" onClick={onRetry}>Retry</button> : null}
    </div>
  );
}
