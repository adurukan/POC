import { useState } from 'react'
import faviconUrl from '../assets/favicon.svg'

interface Props {
  onLogin: (username: string) => void
  onGoToTeacherLogin?: () => void
}

export default function LoginPage({ onLogin, onGoToTeacherLogin }: Props) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  function handleSubmit(e: { preventDefault(): void }) {
    e.preventDefault()
    if (!username || !password) {
      setError('Please enter a username and password.')
      return
    }
    if (username === 'alpbek' && password === '1234') {
      localStorage.setItem('loggedIn', 'true')
      localStorage.setItem('username', username)
      onLogin(username)
    } else {
      setError('Invalid username or password.')
    }
  }

  return (
    <div className="login-bg">
      <form className="login-card" onSubmit={handleSubmit}>
        <div className="login-brand">
          <img src={faviconUrl} alt="" />
          <div className="word">Matemant<span className="accent">ı</span>k</div>
        </div>
        <p className="login-tagline">Adım adım birlikte çözelim.</p>

        <div>
          <div className="field-label">Username</div>
          <input
            className="input"
            type="text"
            placeholder="alpbek"
            value={username}
            autoFocus
            onChange={(e) => setUsername(e.target.value)}
          />
        </div>

        <div>
          <div className="field-label">Password</div>
          <input
            className="input"
            type="password"
            placeholder="••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>

        {error && <p className="error-text">{error}</p>}

        <button type="submit" className="btn btn-primary btn-lg" style={{ marginTop: 4 }}>
          Sign in
        </button>

        <p style={{ fontSize: 12, color: 'var(--fg-3)', textAlign: 'center', margin: 0 }}>
          Hint: <code style={{ fontFamily: 'var(--font-mono)' }}>alpbek</code> / <code style={{ fontFamily: 'var(--font-mono)' }}>1234</code>
        </p>

        {onGoToTeacherLogin && (
          <button
            type="button"
            className="btn btn-ghost"
            onClick={onGoToTeacherLogin}
            style={{ fontSize: 12 }}
          >
            Öğretmen girişi →
          </button>
        )}
      </form>
    </div>
  )
}
