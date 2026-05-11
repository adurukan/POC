import { useState } from 'react'
import LoginPage from './components/LoginPage'
import MainLayout from './components/MainLayout'
import TeacherLoginPage from './components/TeacherLoginPage'
import TeacherStudio from './components/TeacherStudio'
import TeacherTopicChooser from './components/TeacherTopicChooser'

type Lang = 'tr' | 'en'
type Screen =
  | 'student-login'
  | 'teacher-login'
  | 'student-app'
  | 'teacher-topic'
  | 'teacher-studio'

function initialScreen(): Screen {
  if (localStorage.getItem('loggedIn') !== 'true') return 'student-login'
  return localStorage.getItem('role') === 'teacher' ? 'teacher-topic' : 'student-app'
}

export default function App() {
  const [screen, setScreen] = useState<Screen>(initialScreen)
  const [username, setUsername] = useState(localStorage.getItem('username') ?? '')
  const [lang, setLang] = useState<Lang>(
    (localStorage.getItem('lang') as Lang) ?? 'tr',
  )

  function handleLangChange(next: Lang) {
    setLang(next)
    localStorage.setItem('lang', next)
  }

  function handleStudentLogin(name: string) {
    setUsername(name)
    localStorage.setItem('role', 'student')
    setScreen('student-app')
  }

  function handleTeacherLogin(name: string) {
    setUsername(name)
    setScreen('teacher-topic')
  }

  function handleLogout() {
    localStorage.removeItem('loggedIn')
    localStorage.removeItem('username')
    localStorage.removeItem('role')
    setUsername('')
    setScreen('student-login')
  }

  switch (screen) {
    case 'student-login':
      return (
        <LoginPage
          onLogin={handleStudentLogin}
          onGoToTeacherLogin={() => setScreen('teacher-login')}
        />
      )
    case 'teacher-login':
      return (
        <TeacherLoginPage
          onLogin={handleTeacherLogin}
          onBackToStudent={() => setScreen('student-login')}
        />
      )
    case 'student-app':
      return (
        <MainLayout
          username={username}
          onLogout={handleLogout}
          lang={lang}
          onLangChange={handleLangChange}
        />
      )
    case 'teacher-topic':
      return (
        <TeacherTopicChooser
          username={username}
          onLogout={handleLogout}
          lang={lang}
          onLangChange={handleLangChange}
          onPickMatematik={() => setScreen('teacher-studio')}
        />
      )
    case 'teacher-studio':
      return (
        <TeacherStudio
          username={username}
          onLogout={handleLogout}
          lang={lang}
          onLangChange={handleLangChange}
        />
      )
  }
}
