import { useState } from 'react'
import { Link } from 'react-router-dom'
import './Feedback.css'

function Feedback() {
  const [form, setForm] = useState({ name: '', type: 'Feedback', message: '' })
  const [submitted, setSubmitted] = useState(false)
  const [errors, setErrors] = useState({})

  const validate = () => {
    const e = {}
    if (!form.name.trim()) e.name = 'Name is required'
    if (!form.message.trim()) e.message = 'Message is required'
    return e
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    const errs = validate()
    if (Object.keys(errs).length > 0) {
      setErrors(errs)
      return
    }
    setSubmitted(true)
  }

  const handleChange = (field) => (e) => {
    setForm(prev => ({ ...prev, [field]: e.target.value }))
    if (errors[field]) setErrors(prev => ({ ...prev, [field]: null }))
  }

  const Navbar = () => (
    <div className="Navbar">
      <Link to="/">
        <img className="logo" src="/new-transparent-logo.png" alt="StockInsight" />
      </Link>
      <nav>
        <ul className="nav_links">
          <li><Link to="/guide">How to Use</Link></li>
          <li><Link to="/model-performance">Model Performance</Link></li>
          <li><Link to="/feedback">Feedback</Link></li>
        </ul>
      </nav>
    </div>
  )

  if (submitted) {
    return (
      <div className="fb-page">
        <Navbar />
        <div className="navbar-placeholder"></div>
        <div className="fb-container">
          <div className="fb-success">
            <div className="fb-success-icon">[ OK ]</div>
            <h2 className="fb-success-title">Submission received</h2>
            <p className="fb-success-text">
              Thank you for your {form.type.toLowerCase()}. It has been recorded.
            </p>
            <Link to="/" className="fb-home-link">← return home</Link>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="fb-page">
      <Navbar />
      <div className="navbar-placeholder"></div>
      <div className="fb-container">
        <div className="fb-hero">
          <h1 className="fb-title">// feedback</h1>
          <p className="fb-subtitle">
            Found a bug? Have a feature idea? Just want to share your thoughts?
            Fill out the form below.
          </p>
        </div>

        <form className="fb-form" onSubmit={handleSubmit} noValidate>
          <div className="fb-field">
            <label className="fb-label" htmlFor="fb-name">// NAME</label>
            <input
              id="fb-name"
              type="text"
              className="fb-input"
              placeholder="your name"
              value={form.name}
              onChange={handleChange('name')}
              autoComplete="off"
            />
            {errors.name && <span className="fb-error">{errors.name}</span>}
          </div>

          <div className="fb-field">
            <label className="fb-label" htmlFor="fb-type">// TYPE</label>
            <select
              id="fb-type"
              className="fb-select"
              value={form.type}
              onChange={handleChange('type')}
            >
              <option>Feedback</option>
              <option>Bug Report</option>
              <option>Feature Request</option>
            </select>
          </div>

          <div className="fb-field">
            <label className="fb-label" htmlFor="fb-message">// MESSAGE</label>
            <textarea
              id="fb-message"
              className="fb-textarea"
              placeholder="describe your feedback, bug, or idea..."
              rows={8}
              value={form.message}
              onChange={handleChange('message')}
            />
            {errors.message && <span className="fb-error">{errors.message}</span>}
          </div>

          <button type="submit" className="fb-submit">Submit</button>
        </form>

        <p className="fb-footer">
          This form is for feedback and feature requests only and is not monitored for support.
        </p>
      </div>
    </div>
  )
}

export default Feedback
