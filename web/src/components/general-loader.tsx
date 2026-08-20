export function GeneralLoader({
  label = 'Making a little space…',
  onRetry,
}: {
  label?: string
  onRetry?: () => void
}) {
  return (
    <div className="api-loader" role={onRetry ? 'alert' : 'status'} aria-live="polite">
      <div>
        <span className="api-loader__spark" aria-hidden="true">
          ✦
        </span>{' '}
        <span>{label}</span>
      </div>
      {onRetry && (
        <button className="button button--small button--primary" type="button" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  )
}
