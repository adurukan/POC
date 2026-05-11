import { useState } from 'react'
import faviconUrl from '../assets/favicon.svg'
import { teacherLogin } from '../api/client'

interface Props {
  onLogin: (username: string) => void
  onBackToStudent: () => void
}

export default function TeacherLoginPage({ onLogin, onBackToStudent }: Props) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e: { preventDefault(): void }) {
    e.preventDefault()
    if (!username || !password) {
      setError('Kullanıcı adı ve parola gerekli.')
      return
    }
    setError('')
    setSubmitting(true)
    try {
      const res = await teacherLogin(username, password)
      localStorage.setItem('loggedIn', 'true')
      localStorage.setItem('role', 'teacher')
      localStorage.setItem('username', res.username)
      onLogin(res.username)
    } catch (err) {
      setError((err as Error).message || 'Giriş başarısız.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="login-bg">
      <form className="login-card" onSubmit={handleSubmit}>
        <div className="login-brand">
          <img src={faviconUrl} alt="" />
          <div className="word">Öğretmen Stüdyo<span className="accent">su</span></div>
        </div>
        <p className="login-tagline">Soru üret, geri bildirim ver, yayınla.</p>

        <div>
          <div className="field-label">Kullanıcı Adı</div>
          <input
            className="input"
            type="text"
            placeholder="ezgi"
            value={username}
            autoFocus
            onChange={(e) => setUsername(e.target.value)}
          />
        </div>

        <div>
          <div className="field-label">Parola</div>
          <input
            className="input"
            type="password"
            placeholder="••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>

        {error && <p className="error-text">{error}</p>}

        <button
          type="submit"
          className="btn btn-primary btn-lg"
          style={{ marginTop: 4 }}
          disabled={submitting}
        >
          {submitting ? 'Giriş yapılıyor…' : 'Giriş Yap'}
        </button>

        <button
          type="button"
          className="btn btn-ghost"
          onClick={onBackToStudent}
          style={{ fontSize: 12 }}
        >
          ← Öğrenci girişine dön
        </button>
      </form>
    </div>
  )
}
