import React from 'react'
import { Link } from 'react-router-dom'

const ADVANTAGES = [
  { icon: '⚡', title: 'Instant Compliance Scan', desc: 'Upload a photo and get a full compliance assessment in under 10 seconds — replacing hours of manual inspection.' },
  { icon: '🎯', title: 'Zero Missed Violations', desc: 'Automated OCR extraction and deterministic rule engine ensure every mandatory declaration is checked against Legal Metrology Rules.' },
  { icon: '📊', title: 'Objective Scoring', desc: 'Weighted scoring with letter grades removes subjective judgment. Every product gets a fair, reproducible compliance score.' },
  { icon: '📄', title: 'Instant PDF Reports', desc: 'Professional compliance reports generated on-the-spot — ready for audits, court proceedings, or management review.' },
  { icon: '🔄', title: 'Batch Processing', desc: 'Scan up to 6 products simultaneously. Front and back images are merged for maximum extraction accuracy.' },
  { icon: '🛡️', title: 'Role-Based Access', desc: 'LMOs, Manufacturers, Retailers, and Admins each get tailored dashboards with appropriate permissions.' },
]

const WORKFLOW_STEPS = [
  { num: '01', title: 'Upload', desc: 'Photograph the product packaging — front, back, or side labels.', icon: '📷' },
  { num: '02', title: 'Extract', desc: 'Our OCR engine reads MRP, net quantity, manufacturer details, dates, and more.', icon: '🔍' },
  { num: '03', title: 'Validate', desc: '9 automated rules check compliance against Legal Metrology Rules, 2011.', icon: '⚖️' },
  { num: '04', title: 'Report', desc: 'Receive a scored compliance report with pass/fail status and detailed findings.', icon: '📋' },
]

const OUTCOMES = [
  { value: '<10s', label: 'Analysis Time', sub: 'per product' },
  { value: '9', label: 'Rules Checked', sub: 'automated validation' },
  { value: '92%', label: 'OCR Accuracy', sub: 'on clear images' },
  { value: '100%', label: 'Deterministic', sub: 'no LLM guessing' },
]

const RULES_COVERED = [
  { rule: 'Rule 3', title: 'Prescribed Information', desc: 'All mandatory declarations on package' },
  { rule: 'Rule 4', title: 'Manufacturer Details', desc: 'Name and complete address' },
  { rule: 'Rule 5', title: 'Commodity Name', desc: 'Clear and intelligible naming' },
  { rule: 'Rule 6', title: 'Principal Display Panel', desc: 'Required info on display panel' },
  { rule: 'Rule 11', title: 'Consumer Care', desc: 'Contact details (phone/email/web)' },
  { rule: 'Rule 12', title: 'Net Quantity', desc: 'SI units verification' },
  { rule: 'Rule 13', title: 'Standard Quantities', desc: 'First Schedule compliance' },
  { rule: 'Rule 14', title: 'Unit Sale Price', desc: 'Price per unit declaration' },
  { rule: 'Rule 15', title: 'Date of Manufacture', desc: 'Manufacturing/best-before dates' },
]

export default function Landing() {
  return (
    <div className="landing">
      {/* Navigation */}
      <nav className="landing-nav">
        <div className="landing-nav-inner">
          <Link to="/" className="landing-brand">
            <span className="landing-brand-mark">LM</span>
            <span className="landing-brand-text">LegalMetriX</span>
          </Link>
          <div className="landing-nav-links">
            <a href="#features" className="landing-nav-link">Features</a>
            <a href="#workflow" className="landing-nav-link">How It Works</a>
            <a href="#rules" className="landing-nav-link">Rules</a>
            <Link to="/login" className="landing-nav-link">Sign In</Link>
            <Link to="/register" className="primary landing-cta-sm">Get Started</Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="landing-hero">
        <div className="landing-hero-bg" />
        <div className="landing-hero-content">
          <div className="landing-hero-badge">Legal Metrology Compliance Automation</div>
          <h1 className="landing-hero-title">
            Transform Manual Inspections into
            <span className="landing-hero-accent"> Instant Digital Compliance</span>
          </h1>
          <p className="landing-hero-sub">
            LegalMetriX automates packaged commodities compliance checking under the
            Legal Metrology (Packaged Commodities) Rules, 2011. Upload a product photo,
            get a scored compliance report in seconds.
          </p>
          <div className="landing-hero-actions">
            <Link to="/register" className="primary landing-cta-lg">Start Free Analysis</Link>
            <a href="#workflow" className="secondary landing-cta-lg">See How It Works</a>
          </div>
          <div className="landing-hero-trust">
            <span>Trusted by Legal Metrology Officers across India</span>
            <span className="landing-dot" />
            <span>Deterministic, not LLM-based</span>
            <span className="landing-dot" />
            <span>9 rules automated</span>
          </div>
        </div>
      </section>

      {/* Transformation: Manual → Digital */}
      <section className="landing-section landing-transform" id="transform">
        <div className="landing-container">
          <div className="landing-section-label">The Problem</div>
          <h2 className="landing-section-title">Manual Inspections Are Slow, Error-Prone, and Unscalable</h2>
          <div className="landing-comparison">
            <div className="landing-compare-card landing-compare-before">
              <div className="landing-compare-badge before">Before: Manual</div>
              <ul className="landing-compare-list">
                <li>⏱️ 30-60 minutes per product inspection</li>
                <li>📝 Handwritten notes and paper reports</li>
                <li>🔍 Inconsistent rule interpretation</li>
                <li>📊 No standardized scoring or grading</li>
                <li>📁 Reports scattered across files and folders</li>
                <li>❌ Human fatigue leads to missed violations</li>
              </ul>
            </div>
            <div className="landing-compare-arrow">
              <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                <circle cx="24" cy="24" r="23" stroke="#2563eb" strokeWidth="2"/>
                <path d="M16 24H32M32 24L26 18M32 24L26 30" stroke="#2563eb" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <div className="landing-compare-card landing-compare-after">
              <div className="landing-compare-badge after">After: LegalMetriX</div>
              <ul className="landing-compare-list">
                <li>⚡ Under 10 seconds per product scan</li>
                <li>📄 Auto-generated professional PDF reports</li>
                <li>🎯 Deterministic, reproducible rule checks</li>
                <li>📊 Standardized A+ to F grading system</li>
                <li>🗂️ Centralized dashboard and inspection history</li>
                <li>✅ 100% rule coverage, zero fatigue</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Advantages */}
      <section className="landing-section" id="features">
        <div className="landing-container">
          <div className="landing-section-label">Why LegalMetriX</div>
          <h2 className="landing-section-title">Purpose-Built for Legal Metrology Compliance</h2>
          <div className="landing-advantages-grid">
            {ADVANTAGES.map((a, i) => (
              <div className="landing-advantage-card" key={i}>
                <span className="landing-advantage-icon">{a.icon}</span>
                <h3 className="landing-advantage-title">{a.title}</h3>
                <p className="landing-advantage-desc">{a.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Workflow */}
      <section className="landing-section landing-workflow" id="workflow">
        <div className="landing-container">
          <div className="landing-section-label">How It Works</div>
          <h2 className="landing-section-title">Four Simple Steps to Compliance</h2>
          <div className="landing-steps">
            {WORKFLOW_STEPS.map((s, i) => (
              <div className="landing-step" key={i}>
                <div className="landing-step-num">{s.num}</div>
                <div className="landing-step-icon">{s.icon}</div>
                <h3 className="landing-step-title">{s.title}</h3>
                <p className="landing-step-desc">{s.desc}</p>
                {i < WORKFLOW_STEPS.length - 1 && <div className="landing-step-connector" />}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Outcomes */}
      <section className="landing-section landing-outcomes" id="outcomes">
        <div className="landing-container">
          <div className="landing-section-label light">Results</div>
          <h2 className="landing-section-title light">Measurable Impact</h2>
          <div className="landing-outcomes-grid">
            {OUTCOMES.map((o, i) => (
              <div className="landing-outcome-card" key={i}>
                <div className="landing-outcome-value">{o.value}</div>
                <div className="landing-outcome-label">{o.label}</div>
                <div className="landing-outcome-sub">{o.sub}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Rules Covered */}
      <section className="landing-section" id="rules">
        <div className="landing-container">
          <div className="landing-section-label">Legal Framework</div>
          <h2 className="landing-section-title">9 Rules Automated from Legal Metrology Rules, 2011</h2>
          <div className="landing-rules-grid">
            {RULES_COVERED.map((r, i) => (
              <div className="landing-rule-card" key={i}>
                <div className="landing-rule-num">{r.rule}</div>
                <div className="landing-rule-title">{r.title}</div>
                <div className="landing-rule-desc">{r.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="landing-section landing-final-cta">
        <div className="landing-container landing-cta-content">
          <h2 className="landing-cta-title">Ready to Modernize Your Compliance Workflow?</h2>
          <p className="landing-cta-sub">
            Join Legal Metrology Officers who are already using LegalMetriX to automate their
            packaged commodities compliance assessments.
          </p>
          <div className="landing-cta-actions">
            <Link to="/register" className="primary landing-cta-lg">Create Free Account</Link>
            <Link to="/login" className="secondary landing-cta-lg">Sign In</Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <div className="landing-container landing-footer-inner">
          <div className="landing-footer-brand">
            <span className="landing-brand-mark sm">LM</span>
            <span>LegalMetriX</span>
          </div>
          <div className="landing-footer-text">
            Legal Metrology (Packaged Commodities) Compliance Scanner
          </div>
          <div className="landing-footer-legal">
            Reference: Legal Metrology Act, 2009 · Legal Metrology (Packaged Commodities) Rules, 2011
          </div>
        </div>
      </footer>
    </div>
  )
}
