interface DataSourceBannerProps {
  isMock: boolean;
  onRetry?: () => void;
}

export default function DataSourceBanner({
  isMock,
  onRetry,
}: DataSourceBannerProps) {
  if (!isMock) {
    return null;
  }

  return (
    <section className="data-source-banner" aria-live="polite">
      <div className="data-source-banner-inner">
        <span className="data-source-indicator" aria-hidden="true" />
        <span className="data-source-text">
          Live backend data is unavailable right now. Showing mock fallback data.
        </span>
        {onRetry ? (
          <button
            type="button"
            className="button button-secondary data-source-retry"
            onClick={onRetry}
          >
            Retry live data
          </button>
        ) : null}
      </div>
    </section>
  );
}
