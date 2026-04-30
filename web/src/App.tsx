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

  return <MainLayout username={username} onLogout={handleLogout} />
}
