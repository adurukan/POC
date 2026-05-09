import { useState } from 'react'
import LoginPage from './components/LoginPage'
import MainLayout from './components/MainLayout'

export default function App() {
  const [loggedIn, setLoggedIn] = useState(
    localStorage.getItem('loggedIn') === 'true'
  )
  const [username, setUsername] = useState(
    localStorage.getItem('username') ?? ''
  )

  const [lang, setLang] = useState<'tr' | 'en'>(
  (localStorage.getItem('lang') as 'tr' | 'en') ?? 'tr'
)

  function handleLangChange(next: 'tr' | 'en') {
    setLang(next)
    localStorage.setItem('lang', next)
  }

  function handleLogin(name: string) {
    setUsername(name)
    setLoggedIn(true)
  }

  function handleLogout() {
    localStorage.removeItem('loggedIn')
    localStorage.removeItem('username')
    setLoggedIn(false)
    setUsername('')
  }

  if (!loggedIn) {
    return <LoginPage onLogin={handleLogin} />
  }

  return <MainLayout
  username={username}
  onLogout={handleLogout}
  lang={lang}
  onLangChange={handleLangChange}
/>
}
