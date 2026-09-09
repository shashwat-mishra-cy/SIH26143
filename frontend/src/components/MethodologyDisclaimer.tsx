import { useState } from 'react'

/**
 * Methodology and legal disclaimer information for the investigation dashboard.
 * Designed with a sleek collapsible disclosure to maximize data readability.
 */
export default function MethodologyDisclaimer() {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <div className="methodology-card">
      <button
        type="button"
        className="methodology-toggle"
        onClick={() => setIsOpen((prev) => !prev)}
        aria-expanded={isOpen}
      >
        <span className="toggle-left">
          <span className="toggle-icon">⚖️</span>
          <span className="toggle-title">Analysis Methodology &amp; Legal Notice</span>
        </span>
        <span className="toggle-arrow">{isOpen ? '▲' : '▼'}</span>
      </button>

      {isOpen && (
        <div className="methodology-content">
          <div className="methodology-steps-card">
            <span className="steps-title">Pipeline Attribution Logic:</span>
            <ul className="methodology-step-list">
              <li>
                <span className="step-bullet">1</span>
                <span><strong>P1 Satellite:</strong> Identifies dark-slick SAR features and computes centroid/shape.</span>
              </li>
              <li>
                <span className="step-bullet">2</span>
                <span><strong>P2 OpenDrift:</strong> Hindcasts ocean current &amp; wind drift to estimate source region.</span>
              </li>
              <li>
                <span className="step-bullet">3</span>
                <span><strong>P3 AIS Correlation:</strong> Ranks top 3 candidate vessels by spatio-temporal proximity.</span>
              </li>
              <li>
                <span className="step-bullet">4</span>
                <span><strong>P4 Evidence Map:</strong> Provides interactive time reconstruction and legal auditing.</span>
              </li>
            </ul>
          </div>

          <div className="disclaimer-alert-box">
            <span className="disclaimer-alert-icon">⚠️</span>
            <p className="disclaimer-alert-text">
              <strong>Non-Causation Advisory:</strong> Association ranking reflects mathematical spatio-temporal
              proximity to the inferred source and is <strong>not legal proof of spill discharge or culpability</strong>.
            </p>
          </div>

          <div className="demo-provenance-tag">
            <span>🛡️ Demo Mode: Synthetic AIS demonstration dataset.</span>
          </div>
        </div>
      )}
    </div>
  )
}
