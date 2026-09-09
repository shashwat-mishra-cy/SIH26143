interface TopNavbarProps {
  onOpenUpload?: () => void
}

/**
 * Top navigation bar — brand, mode badge, system status, and satellite ingestion trigger.
 */
export default function TopNavbar({ onOpenUpload }: TopNavbarProps) {
  return (
    <header className="top-navbar">
      <div className="navbar-brand">
        <span className="brand-mark">SIH26143</span>
        <span className="brand-divider" aria-hidden="true" />
        <span className="brand-title">Marine Intelligence System</span>
      </div>
      <div className="navbar-status">
        {onOpenUpload && (
          <button
            type="button"
            className="navbar-upload-btn"
            onClick={onOpenUpload}
            title="Ingest Satellite Image to P1 ML Engine"
          >
            <span aria-hidden="true">🛰️</span>
            <span>Ingest Satellite Image</span>
          </button>
        )}
        <span className="badge badge-demo">Demo Mode</span>
        <span className="badge badge-online">
          <span className="status-dot" aria-hidden="true" />
          System Online
        </span>
      </div>
    </header>
  )
}